"""Tests for the HTML renderer over the JSON payload."""

import json
from pathlib import Path

import pytest

from sonar_reports.report.html_report import (
    HtmlReportRenderer, PayloadError, build_view_model, _condition_row, find_chrome, html_to_pdf,
)


def _payload(**overrides):
    base = {
        'schema_version': 1,
        'generated_at': '2026-09-07T11:28:21Z',
        'data_source': {'name': 'SonarCloud', 'url': 'https://sonarcloud.io', 'role': 'SAST'},
        'scope': {'severity_filter': ['BLOCKER', 'CRITICAL', 'MAJOR', 'MINOR'], 'include_resolved': False,
                  'issues_exported': 3, 'issues_total': 3, 'issues_truncated': False},
        'project': {'key': 'org_proj', 'name': 'Proj <b>x</b>', 'organization': 'org',
                    'last_analysis_date': '2026-09-07T10:55:06+00:00', 'quality_gate_status': 'OK'},
        'statistics': {'total_issues': 3, 'by_severity': {'CRITICAL': 1, 'MAJOR': 1, 'MINOR': 1},
                       'by_type': {'CODE_SMELL': 2, 'BUG': 1}, 'security_issues': 0,
                       'technical_debt': '1h', 'technical_debt_minutes': 60},
        'category_statistics': {'security': {'total': 0, 'by_severity': {}},
                                'reliability': {'total': 1, 'by_severity': {'MINOR': 1}},
                                'maintainability': {'total': 2, 'by_severity': {'CRITICAL': 1, 'MAJOR': 1}}},
        'security_summary': {'total': 0, 'by_severity': {}, 'vulnerabilities': 0, 'hotspots': 2},
        'metrics': [{'key': 'coverage', 'name': 'Coverage', 'value': '13.5', 'formatted': '13.5%'},
                    {'key': 'security_rating', 'name': 'Security Rating', 'value': '1.0', 'formatted': 'A'},
                    {'key': 'reliability_rating', 'name': 'Reliability Rating', 'value': '2.0', 'formatted': 'B'},
                    {'key': 'sqale_rating', 'name': 'Maintainability Rating', 'value': '1.0', 'formatted': 'A'},
                    {'key': 'ncloc', 'name': 'Lines of Code', 'value': '1000', 'formatted': '1,000'},
                    {'key': 'duplicated_lines_density', 'name': 'Duplicated Lines', 'value': '5.5', 'formatted': '5.5%'}],
        'security_hotspots': {'total': 2, 'by_status': {'REVIEWED': 1, 'TO_REVIEW': 1}, 'items': [
            {'key': 'h1', 'component_name': 'a/Db.cs', 'line': 10, 'message': 'Use a parameterized query',
             'status': 'REVIEWED', 'resolution': 'SAFE', 'securityCategory': 'sql-injection', 'vulnerabilityProbability': 'HIGH'},
            {'key': 'h2', 'component_name': 'b/Http.ts', 'line': 3, 'message': 'Use https',
             'status': 'TO_REVIEW', 'resolution': None, 'securityCategory': 'encrypt-data', 'vulnerabilityProbability': 'LOW'},
        ]},
        'quality_gate': {'projectStatus': {'status': 'OK', 'conditions': [
            {'status': 'OK', 'metricKey': 'new_reliability_rating', 'comparator': 'GT', 'errorThreshold': '1', 'actualValue': '1'},
            {'status': 'OK', 'metricKey': 'new_coverage', 'comparator': 'LT', 'errorThreshold': '80', 'actualValue': '85.5'},
        ]}},
        'issues': [
            {'key': 'i1', 'type': 'CODE_SMELL', 'severity': 'CRITICAL', 'ui_severity': 'High', 'status': 'OPEN',
             'message': 'Reduce complexity', 'component_name': 'a/Svc.cs', 'line': 5, 'rule': 'csharpsquid:S3776'},
            {'key': 'i2', 'type': 'CODE_SMELL', 'severity': 'MAJOR', 'ui_severity': 'Medium', 'status': 'OPEN',
             'message': 'Rename class', 'component_name': 'a/Dto.cs', 'line': 1, 'rule': 'csharpsquid:S101'},
            {'key': 'i3', 'type': 'BUG', 'severity': 'MINOR', 'ui_severity': 'Low', 'status': 'OPEN',
             'message': 'Compare to default', 'component_name': 'a/Ext.cs', 'line': 21, 'rule': 'csharpsquid:S2955'},
        ],
    }
    base.update(overrides)
    return base


def test_view_model_counts_and_hotspot_split():
    vm = build_view_model(_payload())
    assert vm['hotspots_total'] == 2
    assert vm['hotspots_open'] == 1
    assert vm['bugs_total'] == 1
    assert vm['high_smells_total'] == 1
    assert vm['top_rules'][0]['rule'] in ('csharpsquid:S3776', 'csharpsquid:S101')
    # open hotspot sorts first regardless of probability
    assert len(vm['hotspots_open_rows']) == 1 and vm['hotspots_open_rows'][0]['open'] is True
    assert len(vm['hotspots_closed_rows']) == 1 and vm['hotspots_closed_rows'][0]['open'] is False
    # recommendations: open hotspot is P1, not P2
    assert any('hotspot' in r for r in vm['recommendations']['p1'])
    assert not any('have been reviewed' in r for r in vm['recommendations']['p2'])


def test_all_reviewed_hotspots_are_not_an_action_item():
    p = _payload()
    p['security_hotspots']['items'][1]['status'] = 'REVIEWED'
    p['security_hotspots']['items'][1]['resolution'] = 'SAFE'
    vm = build_view_model(p)
    assert vm['hotspots_open'] == 0
    assert vm['recommendations']['p1'] == []
    assert any('have been reviewed' in r for r in vm['recommendations']['p2'])


def test_condition_row_humanises_metric_and_comparator():
    rating = _condition_row({'status': 'OK', 'metricKey': 'new_reliability_rating', 'comparator': 'GT',
                             'errorThreshold': '1', 'actualValue': '2'})
    assert rating['name'] == 'Reliability rating on new code'
    assert rating['requirement'] == '≤ A'
    assert rating['actual'] == 'B'
    cov = _condition_row({'status': 'ERROR', 'metricKey': 'new_coverage', 'comparator': 'LT',
                          'errorThreshold': '80', 'actualValue': '12.5'})
    assert cov['requirement'] == '≥ 80%'
    assert cov['actual'] == '12.5%'
    assert cov['ok'] is False


def test_render_escapes_and_is_self_contained(tmp_path):
    out = tmp_path / 'r.html'
    HtmlReportRenderer().render_to_file(_payload(), str(out))
    html = out.read_text(encoding='utf-8')
    assert '&lt;b&gt;x&lt;/b&gt;' in html and '<b>x</b>' not in html
    assert 'Quality gate passed' in html
    assert 'sql-injection' in html
    assert 'Reliability rating on new code' in html
    assert 'src=' not in html and '<link' not in html  # no external assets


def test_rejects_wrong_schema():
    with pytest.raises(PayloadError):
        build_view_model(_payload(schema_version=99))
    with pytest.raises(PayloadError):
        build_view_model({'foo': 'bar'})


def test_html_to_pdf_errors_without_browser(tmp_path, monkeypatch):
    monkeypatch.setenv('SONAR_REPORT_CHROME', str(tmp_path / 'definitely-not-a-browser'))
    assert find_chrome() is None
    src = tmp_path / 'x.html'
    src.write_text('<p>hi</p>')
    with pytest.raises(RuntimeError, match='No Chrome'):
        html_to_pdf(str(src), str(tmp_path / 'x.pdf'))


def test_customer_audience_hides_maintainability_and_recommendations(tmp_path):
    vm = build_view_model(_payload(), audience='customer')
    assert [k['label'] for k in vm['kpis']] == ['Quality gate', 'Open vulnerabilities', 'Security hotspots', 'Bugs']
    assert vm['facts'] == []
    assert [r['name'] for r in vm['category_rows']] == ['Security', 'Reliability']
    # severity totals exclude code smells so they agree with the category table
    assert vm['total_issues'] == 1
    assert [s['label'] for s in vm['segments']] == ['Low']
    html = HtmlReportRenderer(audience='customer').render(_payload())
    for banned in ('Maintainability</h2>', 'Recommendations', 'Code smells', 'Technical debt',
                   'Lines of code', 'Test coverage', 'Duplicated lines', 'csharpsquid:S3776'):
        assert banned not in html, banned
    assert 'csharpsquid:S2955' in html  # the bug is still there


def test_internal_audience_keeps_everything():
    vm = build_view_model(_payload(), audience='internal')
    assert len(vm['kpis']) == 6 and len(vm['facts']) == 3
    assert vm['total_issues'] == 3
    html = HtmlReportRenderer(audience='internal').render(_payload())
    assert 'Recommendations' in html and 'csharpsquid:S3776' in html


def test_unknown_audience_rejected():
    with pytest.raises(ValueError):
        build_view_model(_payload(), audience='board')


def test_hotspots_grouped_by_rule_file_and_outcome():
    from sonar_reports.report.html_report import group_hotspots, hotspot_summary
    hs = [
        {'key': 'a', 'ruleKey': 'r1', 'ruleName': 'SQL queries should not be dynamically formatted', 'message': 'Use a parameterized query',
         'component_name': 'Db.cs', 'line': 239, 'status': 'REVIEWED', 'resolution': 'SAFE', 'securityCategory': 'sql-injection',
         'vulnerabilityProbability': 'HIGH', 'reviewComments': ['Identifiers are allow-listed.', 'Identifiers are allow-listed.']},
        {'key': 'b', 'ruleKey': 'r1', 'ruleName': 'SQL queries should not be dynamically formatted', 'message': 'Use a parameterized query',
         'component_name': 'Db.cs', 'line': 247, 'status': 'REVIEWED', 'resolution': 'SAFE', 'securityCategory': 'sql-injection',
         'vulnerabilityProbability': 'HIGH', 'reviewComments': ['Values are SqlParameters.']},
        {'key': 'c', 'ruleKey': 'r1', 'message': 'Use a parameterized query', 'component_name': 'Db.cs', 'line': 300,
         'status': 'TO_REVIEW', 'resolution': None, 'securityCategory': 'sql-injection', 'vulnerabilityProbability': 'HIGH', 'reviewComments': []},
        {'key': 'd', 'ruleKey': 'r2', 'ruleName': 'Regex timeout', 'message': 'Pass a timeout', 'component_name': 'Swagger.cs', 'line': 410,
         'status': 'REVIEWED', 'resolution': 'FIXED', 'securityCategory': 'dos', 'vulnerabilityProbability': 'MEDIUM', 'reviewComments': []},
    ]
    rows = group_hotspots(hs)
    assert len(rows) == 3
    assert rows[0]['open'] is True and rows[0]['tone'] == 'serious'          # open first, coloured
    safe = next(r for r in rows if r['resolution'] == 'SAFE')
    assert safe['lines'] == [239, 247] and safe['count'] == 2
    assert safe['tone'] == 'muted'                                            # reviewed -> not red
    assert safe['finding'] == 'SQL queries should not be dynamically formatted'  # rule title, not the imperative
    assert safe['justification'] == ['Identifiers are allow-listed.', 'Values are SqlParameters.']
    assert next(r for r in rows if r['resolution'] == 'FIXED')['status_label'] == 'Fixed'
    assert hotspot_summary(hs) == ('The scanner flagged 4 security-sensitive locations. 3 have been manually reviewed '
                                   '(2 confirmed safe, 1 fixed); 1 is still awaiting review.')
    hs_all_done = [h for h in hs if h['status'] == 'REVIEWED']
    assert hotspot_summary(hs_all_done).endswith('None remain open.')
    assert hotspot_summary([]) == 'The scanner raised no security hotspots for this project.'


def test_hotspot_section_renders_outcomes_not_alarm():
    p = _payload()
    p['security_hotspots']['items'][1]['status'] = 'REVIEWED'
    p['security_hotspots']['items'][1]['resolution'] = 'SAFE'
    p['security_hotspots']['items'][0]['reviewComments'] = ['Table names come from a fixed allow-list.']
    p['security_hotspots']['items'][0]['ruleName'] = 'SQL queries should not be dynamically formatted'
    html = HtmlReportRenderer().render(p)
    assert 'Security review outcomes' in html
    assert 'None remain open.' in html
    assert 'Awaiting review: none' in html
    assert 'Confirmed safe' in html
    assert 'Table names come from a fixed allow-list.' in html
    assert 'Use a parameterized query' not in html          # scanner imperative hidden for customers
    assert 'tone-serious' not in html.split('Reviewed and closed')[1]  # no red pills in the closed table
