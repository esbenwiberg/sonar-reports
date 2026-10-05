"""Machine-readable export of report data.

The markdown report is for humans; this payload is for tooling — notably the
portfolio HTML builder, which needs structured data for every project rather
than a document it would have to scrape.
"""

import json
import logging
from datetime import datetime
from typing import List, Optional

from ..models import ReportData


logger = logging.getLogger(__name__)

#: Bumped whenever the payload shape changes incompatibly, so consumers can
#: refuse data they don't understand instead of silently misreading it.
SCHEMA_VERSION = 1

#: Where the underlying analysis comes from. Carried in the payload so any
#: downstream document can state its provenance without hardcoding it.
DATA_SOURCE = {
    'name': 'SonarCloud',
    'url': 'https://sonarcloud.io',
    'vendor': 'Sonar',
    'role': 'Static Application Security Testing (SAST) and code quality analysis',
}


def _iso(value: Optional[datetime]) -> Optional[str]:
    return value.isoformat() if isinstance(value, datetime) else None


def _issue_dict(issue) -> dict:
    return {
        'key': issue.key,
        'type': issue.type,
        'severity': issue.severity,
        'ui_severity': issue.get_ui_severity(),
        'status': issue.status,
        'message': issue.message,
        'component': issue.component,
        'component_name': issue.get_component_name(),
        'line': issue.line,
        'rule': issue.rule,
        'tags': list(issue.tags or []),
        'effort': issue.effort,
        'effort_minutes': issue.get_effort_minutes(),
        'creation_date': _iso(issue.creation_date),
        'is_security': issue.is_security_issue(),
    }


#: api/hotspots/search fields worth keeping. Hotspots arrive as raw dicts
#: (unlike issues, which are modelled), so they are passed through explicitly:
#: a blanket copy would bake today's API response shape into the payload.
_HOTSPOT_FIELDS = (
    'key', 'component', 'project', 'line', 'message', 'status', 'resolution',
    'securityCategory', 'vulnerabilityProbability', 'ruleKey',
    'creationDate', 'updateDate', 'author',
    # Added by SonarCloudClient.enrich_hotspots (api/hotspots/show)
    'ruleName', 'reviewComments',
)


def _hotspot_dict(hotspot: dict) -> dict:
    """Flatten one raw hotspot into the payload shape.

    'component' is fully qualified ('projectKey:path/to/File.ts'); the path
    alone is what any consumer wanting to open the file actually needs, so it
    is split out rather than left for every consumer to re-derive.
    """
    out = {k: hotspot.get(k) for k in _HOTSPOT_FIELDS}
    component = hotspot.get('component') or ''
    out['component_name'] = component.split(':', 1)[1] if ':' in component else component
    # Hotspots have no severity; probability is the closest analogue and is what
    # the SonarCloud UI ranks them by.
    out['ui_severity'] = hotspot.get('vulnerabilityProbability')
    out['type'] = 'SECURITY_HOTSPOT'
    return out


def build_payload(
    data: ReportData,
    severity_filter: Optional[List[str]] = None,
    base_url: Optional[str] = None,
    include_resolved: bool = False,
    max_issues: Optional[int] = None,
) -> dict:
    """
    Build a JSON-serialisable payload describing one project's analysis.

    Args:
        data: Processed report data
        severity_filter: Severities the issue set was restricted to
        base_url: SonarCloud host the data came from
        include_resolved: Whether resolved issues were included
        max_issues: Cap on exported issues; None exports all

    Returns:
        Dictionary ready for json.dump
    """
    info = data.project_info
    issues = data.get_top_issues(len(data.issues))  # severity-ordered

    truncated = False
    if max_issues is not None and len(issues) > max_issues:
        issues = issues[:max_issues]
        truncated = True

    hotspot_statuses = {}
    for hotspot in data.security_hotspots or []:
        status = hotspot.get('status', 'UNKNOWN')
        hotspot_statuses[status] = hotspot_statuses.get(status, 0) + 1

    return {
        'schema_version': SCHEMA_VERSION,
        'generated_at': datetime.utcnow().isoformat() + 'Z',
        'data_source': dict(DATA_SOURCE, host=base_url or DATA_SOURCE['url']),
        'scope': {
            'severity_filter': list(severity_filter or []),
            'include_resolved': include_resolved,
            'issues_exported': len(issues),
            'issues_total': len(data.issues),
            'issues_truncated': truncated,
        },
        'project': {
            'key': info.key,
            'name': info.name or info.key,
            'organization': info.organization,
            'version': info.version,
            'last_analysis_date': _iso(info.last_analysis_date),
            'quality_gate_status': info.quality_gate_status,
        },
        'statistics': data.calculate_statistics(),
        'category_statistics': data.get_category_statistics(),
        'security_summary': data.get_security_summary(),
        'metrics': [
            {
                'key': m.key,
                'name': m.metric_name,
                'value': m.value,
                'formatted': m.get_formatted_value(),
            }
            for m in data.metrics
        ],
        'security_hotspots': {
            'total': len(data.security_hotspots or []),
            'by_status': hotspot_statuses,
            # The tally alone cannot be triaged: a downstream tool needs the
            # key, rule, file and line to act on an individual hotspot.
            'items': [_hotspot_dict(h) for h in (data.security_hotspots or [])],
        },
        'quality_gate': data.quality_gate_status or {},
        'issues': [_issue_dict(i) for i in issues],
    }


def write_json(path: str, payload: dict) -> str:
    """
    Write a payload to disk as UTF-8 JSON.

    Args:
        path: Destination file path
        payload: Payload from build_payload

    Returns:
        The path written
    """
    with open(path, 'w', encoding='utf-8') as fh:
        json.dump(payload, fh, indent=2, ensure_ascii=False, default=str)
    logger.info(f"JSON data written to: {path}")
    return path
