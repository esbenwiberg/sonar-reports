"""Tests for organization-token support in SonarCloudClient.

Regression cover for the failure where every api/issues/search call returned
HTTP 400 "The 'organization' parameter is required when using an organization
token" because Config.organization was never passed to the client.
"""

import pytest
import requests

from sonar_reports.api.client import SonarCloudClient, SonarCloudAPIError


class FakeResponse:
    def __init__(self, status=200, payload=None, text=""):
        self.status_code = status
        self._payload = payload
        self.text = text

    def json(self):
        if self._payload is None:
            raise ValueError("no json")
        return self._payload

    def raise_for_status(self):
        if self.status_code >= 400:
            raise requests.exceptions.HTTPError(response=self)


def client_with(responses, organization="365projectum"):
    """Client whose session returns the queued responses; records sent params."""
    c = SonarCloudClient("tok", organization=organization)
    calls = []

    def fake_get(url, params=None, timeout=None):
        calls.append(dict(params or {}))
        return responses.pop(0)

    c.session.get = fake_get
    return c, calls


ORG_REQUIRED = {"errors": [{"msg": "The 'organization' parameter is required when using an organization token"}]}
ORG_UNKNOWN = {"errors": [{"msg": "Unexpected value for parameter 'organization'"}]}


def test_organization_is_sent_on_every_request():
    c, calls = client_with([FakeResponse(200, {"issues": []})])
    c._make_request("/api/issues/search", {"componentKeys": "p"})
    assert calls[0]["organization"] == "365projectum"


def test_no_organization_sent_when_not_configured():
    c, calls = client_with([FakeResponse(200, {"issues": []})], organization=None)
    c._make_request("/api/issues/search", {"componentKeys": "p"})
    assert "organization" not in calls[0]


def test_explicit_organization_param_is_not_overwritten():
    c, calls = client_with([FakeResponse(200, {})])
    c._make_request("/api/issues/search", {"organization": "other"})
    assert calls[0]["organization"] == "other"


def test_org_required_error_is_actionable():
    """The real-world 400: message must name the cause and the fix."""
    c, _ = client_with([FakeResponse(400, ORG_REQUIRED)], organization=None)
    with pytest.raises(SonarCloudAPIError) as exc:
        c._make_request("/api/issues/search", {"componentKeys": "p"})
    msg = str(exc.value)
    assert "organization token" in msg
    assert "--organization" in msg


def test_endpoint_rejecting_organization_is_retried_without_it():
    c, calls = client_with([
        FakeResponse(400, ORG_UNKNOWN),
        FakeResponse(200, {"component": {}}),
    ])
    result = c._make_request("/api/measures/component", {"component": "p"})
    assert result == {"component": {}}
    assert "organization" in calls[0]
    assert "organization" not in calls[1]


def test_rejecting_endpoint_is_remembered_so_retry_happens_once():
    c, calls = client_with([
        FakeResponse(400, ORG_UNKNOWN),
        FakeResponse(200, {}),
        FakeResponse(200, {}),
    ])
    c._make_request("/api/measures/component", {"component": "p"})
    c._make_request("/api/measures/component", {"component": "p"})
    assert len(calls) == 3                       # not 4: no second retry
    assert "organization" not in calls[2]


def test_generic_http_error_includes_sonarcloud_detail():
    """Regression: the old client collapsed this to a bare status code."""
    c, _ = client_with([FakeResponse(400, {"errors": [{"msg": "Nope"}]})])
    with pytest.raises(SonarCloudAPIError) as exc:
        c._make_request("/api/issues/search", {})
    assert "Nope" in str(exc.value)
    assert "400" in str(exc.value)


def test_error_detail_survives_non_json_body():
    c, _ = client_with([FakeResponse(500, None, text="gateway exploded")])
    with pytest.raises(SonarCloudAPIError) as exc:
        c._make_request("/api/issues/search", {})
    assert "gateway exploded" in str(exc.value)


def test_auth_and_forbidden_still_classified():
    c, _ = client_with([FakeResponse(401, {"errors": [{"msg": "bad token"}]})])
    with pytest.raises(SonarCloudAPIError, match="Authentication failed"):
        c._make_request("/api/issues/search", {})

    c, _ = client_with([FakeResponse(403, {"errors": [{"msg": "no access"}]})])
    with pytest.raises(SonarCloudAPIError) as exc:
        c._make_request("/api/issues/search", {})
    assert "forbidden" in str(exc.value).lower() and "no access" in str(exc.value)


def test_caller_params_are_not_mutated():
    c, _ = client_with([FakeResponse(200, {})])
    original = {"componentKeys": "p"}
    c._make_request("/api/issues/search", original)
    assert original == {"componentKeys": "p"}


def test_get_issues_sends_organization_end_to_end():
    c, calls = client_with([FakeResponse(200, {"issues": [], "paging": {"total": 0}})])
    c.get_issues("365projectum_PowerGantt", severities=["BLOCKER"])
    assert calls[0]["organization"] == "365projectum"
    assert calls[0]["componentKeys"] == "365projectum_PowerGantt"


# ---------------------------------------------------------------------------
# api/hotspots/search accepts only ONE 'status' value; the comma-separated
# list it used to send was rejected with:
#   Value of parameter 'status' (TO_REVIEW,REVIEWED) must be one of:
#   [TO_REVIEW, REVIEWED]
# ---------------------------------------------------------------------------

def test_hotspots_fetched_one_status_per_request():
    c, calls = client_with([
        FakeResponse(200, {"hotspots": [{"key": "h1"}], "paging": {"total": 1}}),
        FakeResponse(200, {"hotspots": [{"key": "h2"}], "paging": {"total": 1}}),
    ])
    hotspots = c.get_security_hotspots("365projectum_PowerGantt")

    assert [h["key"] for h in hotspots] == ["h1", "h2"]
    assert [call["status"] for call in calls] == ["TO_REVIEW", "REVIEWED"]
    for call in calls:
        assert "," not in call["status"]


def test_hotspots_partial_failure_keeps_what_succeeded():
    """A failing status must not discard the other status's results."""
    c, _ = client_with([
        FakeResponse(200, {"hotspots": [{"key": "h1"}], "paging": {"total": 1}}),
        FakeResponse(400, {"errors": [{"msg": "boom"}]}),
    ])
    hotspots = c.get_security_hotspots("365projectum_PowerGantt")
    assert [h["key"] for h in hotspots] == ["h1"]


def test_hotspots_never_raises():
    """Hotspots are supplementary — they must not fail the whole report."""
    c, _ = client_with([
        FakeResponse(400, {"errors": [{"msg": "boom"}]}),
        FakeResponse(400, {"errors": [{"msg": "boom"}]}),
    ])
    assert c.get_security_hotspots("365projectum_PowerGantt") == []


# ---------------------------------------------------------------------------
# Organization tokens are refused by every component-addressed endpoint with
# 404 "Project doesn't exist" — api/components/show, api/measures/component,
# api/measures/component_tree — while api/issues/search, api/projects/search
# and api/qualitygates/project_status work fine. The report must survive that.
# ---------------------------------------------------------------------------

NOT_FOUND = {"errors": [{"msg": "Project doesn't exist"}]}


BRANCHES = {"branches": [
    {"name": "feature/x", "isMain": False, "status": {"bugs": 1}},
    {"name": "master", "isMain": True, "type": "LONG",
     "status": {"qualityGateStatus": "ERROR", "bugs": 152,
                "vulnerabilities": 4, "codeSmells": 998}},
]}


def test_metrics_failure_does_not_raise():
    """Regression: a 404 here used to abort the whole report."""
    c, _ = client_with([FakeResponse(404, NOT_FOUND), FakeResponse(404, NOT_FOUND)])
    assert c.get_metrics("365projectum_PowerGantt") == []


def test_metrics_derived_from_main_branch_when_measures_denied():
    c, calls = client_with([
        FakeResponse(404, NOT_FOUND),      # measures/component
        FakeResponse(200, BRANCHES),       # project_branches/list
    ])
    measures = c.get_metrics("365projectum_PowerGantt")

    assert {m["metric"]: m["value"] for m in measures} == {
        "bugs": "152", "vulnerabilities": "4", "code_smells": "998",
    }
    assert calls[1]["project"] == "365projectum_PowerGantt"


def test_branch_metrics_ignore_non_main_branches():
    """Counts must come from the main branch, not whichever came first."""
    c, _ = client_with([FakeResponse(404, NOT_FOUND), FakeResponse(200, BRANCHES)])
    measures = c.get_metrics("365projectum_PowerGantt")
    assert {"metric": "bugs", "value": "1"} not in measures


def test_branch_metrics_include_hotspots_when_present():
    c, _ = client_with([FakeResponse(404, NOT_FOUND), FakeResponse(200, {"branches": [
        {"name": "master", "isMain": True,
         "status": {"bugs": 2, "securityHotspots": 7}},
    ]})])
    measures = c.get_metrics("p")
    assert {"metric": "security_hotspots", "value": "7"} in measures


def test_branch_metrics_skip_absent_fields():
    """A missing count must be omitted, never reported as zero."""
    c, _ = client_with([FakeResponse(404, NOT_FOUND), FakeResponse(200, {"branches": [
        {"name": "master", "isMain": True, "status": {"bugs": 0}},
    ]})])
    measures = c.get_metrics("p")
    assert measures == [{"metric": "bugs", "value": "0"}]


def test_branch_metrics_handle_no_main_branch():
    c, _ = client_with([FakeResponse(404, NOT_FOUND), FakeResponse(200, {"branches": [
        {"name": "feature/x", "isMain": False, "status": {"bugs": 1}},
    ]})])
    assert c.get_metrics("p") == []


def test_branch_metrics_handle_missing_status():
    c, _ = client_with([FakeResponse(404, NOT_FOUND), FakeResponse(200, {"branches": [
        {"name": "master", "isMain": True},
    ]})])
    assert c.get_metrics("p") == []


def test_branch_fallback_not_used_when_measures_works():
    c, calls = client_with([
        FakeResponse(200, {"component": {"measures": [{"metric": "ncloc", "value": "9"}]}}),
    ])
    assert c.get_metrics("p") == [{"metric": "ncloc", "value": "9"}]
    assert len(calls) == 1


def test_metrics_still_returned_when_endpoint_works():
    c, _ = client_with([
        FakeResponse(200, {"component": {"measures": [{"metric": "ncloc", "value": "42"}]}}),
    ])
    assert c.get_metrics("365projectum_PowerGantt") == [{"metric": "ncloc", "value": "42"}]


def test_project_info_falls_back_to_projects_search():
    c, calls = client_with([
        FakeResponse(404, NOT_FOUND),                      # components/show
        FakeResponse(200, {"components": [                 # projects/search
            {"key": "365projectum_Other", "name": "Other"},
            {"key": "365projectum_PowerGantt", "name": "PowerGantt",
             "lastAnalysisDate": "2026-08-25T07:00:00+0000"},
        ]}),
    ])
    info = c.get_project_info("365projectum_PowerGantt")

    assert info["name"] == "PowerGantt"
    assert info["organization"] == "365projectum"
    # projects/search names the field differently; ProjectInfo needs analysisDate
    assert info["analysisDate"] == "2026-08-25T07:00:00+0000"
    assert calls[1]["q"] == "365projectum_PowerGantt"


def test_project_info_fallback_requires_exact_key_match():
    """A substring match must not be mistaken for the project."""
    c, _ = client_with([
        FakeResponse(404, NOT_FOUND),
        FakeResponse(200, {"components": [
            {"key": "365projectum_PowerGantt-legacy", "name": "Legacy"},
        ]}),
    ])
    assert c.get_project_info("365projectum_PowerGantt") == {}


def test_project_info_prefers_components_show_when_available():
    c, calls = client_with([
        FakeResponse(200, {"component": {"key": "k", "name": "Direct"}}),
    ])
    assert c.get_project_info("k")["name"] == "Direct"
    assert len(calls) == 1          # no needless fallback call


def test_project_info_fallback_without_organization_is_graceful():
    c, _ = client_with([FakeResponse(404, NOT_FOUND)], organization=None)
    assert c.get_project_info("365projectum_PowerGantt") == {}


def test_project_info_survives_fallback_also_failing():
    c, _ = client_with([
        FakeResponse(404, NOT_FOUND),
        FakeResponse(500, None, text="boom"),
    ])
    assert c.get_project_info("365projectum_PowerGantt") == {}


# api/hotspots/show adds the reviewer's side of the story. It must never turn a
# successful hotspot fetch into a failure.
def test_enrich_hotspots_adds_rule_name_and_deduped_comments():
    c, calls = client_with([
        FakeResponse(200, {"rule": {"key": "csharpsquid:S2077", "name": "SQL queries should not be dynamically formatted"},
                           "comment": [{"markdown": "Reviewed - Safe. Same text."},
                                       {"markdown": "Reviewed - Safe. Same text."},
                                       {"htmlText": "Second comment"}]}),
    ])
    out = c.enrich_hotspots([{"key": "h1", "status": "REVIEWED"}])
    assert out[0]["ruleName"] == "SQL queries should not be dynamically formatted"
    assert out[0]["reviewComments"] == ["Reviewed - Safe. Same text.", "Second comment"]
    assert calls[0]["hotspot"] == "h1"


def test_enrich_hotspots_survives_detail_failure():
    c, _ = client_with([FakeResponse(500, {"errors": [{"msg": "boom"}]})])
    out = c.enrich_hotspots([{"key": "h1"}, {"status": "TO_REVIEW"}])  # second has no key
    assert out[0]["ruleName"] is None and out[0]["reviewComments"] == []
    assert out[1]["reviewComments"] == []
