"""Render the JSON report payload as a self-contained HTML document, optionally as PDF.

The renderer consumes the machine-readable payload written by ``json_export``
rather than re-fetching from SonarCloud, so the HTML/PDF is always a faithful
re-presentation of a report that already exists and can be regenerated offline.

PDF conversion shells out to a locally installed Chrome/Chromium in headless
mode. There is deliberately no Python PDF dependency: the HTML is print-styled,
and a real browser engine renders it exactly as the user would see it.
"""

import html
import logging
import os
import shutil
import subprocess
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional

import jinja2

from .json_export import SCHEMA_VERSION

logger = logging.getLogger(__name__)

SEVERITY_ORDER = ['BLOCKER', 'CRITICAL', 'MAJOR', 'MINOR', 'INFO']
UI_SEVERITY = {'BLOCKER': 'Blocker', 'CRITICAL': 'High', 'MAJOR': 'Medium', 'MINOR': 'Low', 'INFO': 'Info'}
SEVERITY_TONE = {'BLOCKER': 'critical', 'CRITICAL': 'serious', 'MAJOR': 'warning', 'MINOR': 'neutral', 'INFO': 'muted'}
PROBABILITY_TONE = {'HIGH': 'serious', 'MEDIUM': 'warning', 'LOW': 'neutral'}
RATING_LETTERS = {'1': 'A', '2': 'B', '3': 'C', '4': 'D', '5': 'E'}

#: Human names for the quality-gate condition metrics SonarCloud commonly uses.
QG_METRIC_NAMES = {
    'reliability_rating': 'Reliability rating',
    'security_rating': 'Security rating',
    'maintainability_rating': 'Maintainability rating',
    'sqale_rating': 'Maintainability rating',
    'coverage': 'Coverage',
    'duplicated_lines_density': 'Duplicated lines',
    'security_hotspots_reviewed': 'Security hotspots reviewed',
    'bugs': 'Bugs',
    'vulnerabilities': 'Vulnerabilities',
    'code_smells': 'Code smells',
    'violations': 'Issues',
    'blocker_violations': 'Blocker issues',
    'critical_violations': 'Critical issues',
    'sqale_index': 'Technical debt',
}
PERCENT_METRICS = {'coverage', 'duplicated_lines_density', 'security_hotspots_reviewed'}
RATING_METRICS = {'reliability_rating', 'security_rating', 'maintainability_rating', 'sqale_rating'}


class PayloadError(ValueError):
    """The JSON payload is missing, malformed, or of an unsupported schema version."""


def _metric(payload: dict, key: str, field: str = 'formatted', default: str = '-') -> str:
    for m in payload.get('metrics') or []:
        if m.get('key') == key:
            return m.get(field) if m.get(field) is not None else default
    return default


def _rating_letter(value: Optional[str]) -> str:
    if value is None:
        return '-'
    return RATING_LETTERS.get(str(value).split('.')[0], str(value))


def _fmt_date(iso: Optional[str]) -> str:
    if not iso:
        return 'Unknown'
    try:
        return datetime.fromisoformat(iso.replace('Z', '+00:00')).strftime('%Y-%m-%d %H:%M UTC')
    except ValueError:
        return iso


def _debt(minutes: Optional[int]) -> str:
    if not minutes:
        return '0h'
    days, rem = divmod(int(minutes), 480)  # SonarCloud's 8h working day
    hours = rem // 60
    if days and hours:
        return f'{days}d {hours}h'
    return f'{days}d' if days else f'{hours}h'


def _condition_row(cond: dict) -> dict:
    key = cond.get('metricKey', '')
    on_new = key.startswith('new_')
    base = key[4:] if on_new else key
    name = QG_METRIC_NAMES.get(base, base.replace('_', ' ').capitalize())
    actual = cond.get('actualValue')
    threshold = cond.get('errorThreshold')
    if base in RATING_METRICS:
        actual_s, threshold_s = _rating_letter(actual), _rating_letter(threshold)
    elif base in PERCENT_METRICS:
        actual_s = f'{float(actual):g}%' if actual not in (None, '') else '-'
        threshold_s = f'{float(threshold):g}%' if threshold not in (None, '') else '-'
    else:
        actual_s, threshold_s = str(actual if actual is not None else '-'), str(threshold if threshold is not None else '-')
    # SonarCloud states the *failure* comparator: GT means "fails when actual > threshold".
    requirement = {'GT': f'≤ {threshold_s}', 'LT': f'≥ {threshold_s}'}.get(cond.get('comparator'), threshold_s)
    return {
        'name': name + (' on new code' if on_new else ''),
        'requirement': requirement,
        'actual': actual_s,
        'status': cond.get('status', 'UNKNOWN'),
        'ok': cond.get('status') == 'OK',
    }


RESOLUTION_LABEL = {'SAFE': 'Confirmed safe', 'FIXED': 'Fixed', 'ACKNOWLEDGED': 'Acknowledged'}
RESOLUTION_ORDER = ['SAFE', 'FIXED', 'ACKNOWLEDGED']
MAX_JUSTIFICATION_CHARS = 800


def _clean_comment(text: str) -> str:
    """Flatten a reviewer comment to one readable line for a table cell."""
    text = ' '.join((text or '').split())
    if len(text) > MAX_JUSTIFICATION_CHARS:
        text = text[:MAX_JUSTIFICATION_CHARS - 1].rstrip() + '…'
    return text


def group_hotspots(hotspots: List[dict]) -> List[dict]:
    """Collapse hotspots that share rule, file and review outcome into one row.

    Five identical SQL-formatting flags in one file are one finding in five
    places, not five findings; listing them separately makes a reviewed file
    look five times worse than it is. Every line number is kept, so nothing
    is hidden, only de-duplicated. Open hotspots sort first, then by the
    scanner's priority.
    """
    groups: Dict[tuple, dict] = {}
    for h in hotspots:
        rule = h.get('ruleKey') or h.get('securityCategory') or ''
        key = (rule, h.get('component_name') or h.get('component') or '', h.get('status'), h.get('resolution'))
        g = groups.get(key)
        if g is None:
            g = groups[key] = {
                'rule': rule,
                'finding': h.get('ruleName') or h.get('message') or rule,
                'message': h.get('message') or '',
                'category': h.get('securityCategory') or '-',
                'file': key[1],
                'lines': [],
                'probability': h.get('vulnerabilityProbability') or '-',
                'status': h.get('status') or '-',
                'resolution': h.get('resolution') or '',
                'open': h.get('status') == 'TO_REVIEW',
                'justification': [],
            }
        if h.get('line') is not None:
            g['lines'].append(h['line'])
        # Highest scanner probability wins for the group.
        order = {'HIGH': 0, 'MEDIUM': 1, 'LOW': 2}
        if order.get(h.get('vulnerabilityProbability'), 9) < order.get(g['probability'], 9):
            g['probability'] = h['vulnerabilityProbability']
        for c in h.get('reviewComments') or []:
            cleaned = _clean_comment(c)
            if cleaned and cleaned not in g['justification']:
                g['justification'].append(cleaned)

    rows = []
    for g in groups.values():
        g['lines'] = sorted(set(g['lines']))
        g['count'] = max(len(g['lines']), 1)
        g['tone'] = PROBABILITY_TONE.get(g['probability'], 'neutral') if g['open'] else 'muted'
        g['status_label'] = 'Awaiting review' if g['open'] else RESOLUTION_LABEL.get(g['resolution'], 'Reviewed')
        rows.append(g)
    prob_order = {'HIGH': 0, 'MEDIUM': 1, 'LOW': 2}
    rows.sort(key=lambda g: (not g['open'], prob_order.get(g['probability'], 9), g['file'], g['lines'][:1]))
    return rows


def hotspot_summary(hotspots: List[dict]) -> str:
    """One sentence that states the outcome before the reader sees any row."""
    total = len(hotspots)
    if not total:
        return 'The scanner raised no security hotspots for this project.'
    open_n = sum(1 for h in hotspots if h.get('status') == 'TO_REVIEW')
    reviewed = total - open_n
    by_res = Counter((h.get('resolution') or 'REVIEWED') for h in hotspots if h.get('status') != 'TO_REVIEW')
    parts = []
    for res in RESOLUTION_ORDER:
        if by_res.get(res):
            parts.append(f"{by_res[res]} {RESOLUTION_LABEL[res].lower()}")
    other = by_res.get('REVIEWED')
    if other:
        parts.append(f'{other} reviewed')
    where = 'location' if total == 1 else 'locations'
    text = f'The scanner flagged {total} security-sensitive {where}. '
    if reviewed == total and total == 1:
        only = parts[0].split(' ', 1)[1] if parts else 'reviewed'
        return f'The scanner flagged 1 security-sensitive location. It was manually reviewed and {only}. None remain open.'
    if reviewed == total:
        text += f"All {total} were manually reviewed"
        text += f" ({', '.join(parts)})." if parts else '.'
        text += ' None remain open.'
    elif reviewed:
        text += f"{reviewed} {'has' if reviewed == 1 else 'have'} been manually reviewed"
        text += f" ({', '.join(parts)})" if parts else ''
        text += f"; {open_n} {'is' if open_n == 1 else 'are'} still awaiting review."
    else:
        text += f"{'It is' if total == 1 else 'All are'} awaiting manual review."
    return text


AUDIENCES = ('customer', 'internal')


def build_view_model(payload: dict, max_rows: int = 25, audience: str = 'customer') -> dict:
    """Turn the JSON payload into the flat structure the HTML template needs.

    All counting and ranking happens here rather than in the template so the
    logic is testable and the template stays presentational.

    ``audience`` controls scope. ``customer`` (default) is a security and
    reliability report: maintainability content (code smells, technical debt,
    coverage, duplication, size) and the recommendations are left out.
    ``internal`` includes everything.
    """
    if audience not in AUDIENCES:
        raise ValueError(f"audience must be one of {AUDIENCES}, got {audience!r}")
    internal = audience == 'internal'
    if not isinstance(payload, dict) or 'schema_version' not in payload:
        raise PayloadError('Not a sonar-reports JSON payload (missing schema_version)')
    if payload['schema_version'] != SCHEMA_VERSION:
        raise PayloadError(
            f"Unsupported payload schema_version {payload['schema_version']} (expected {SCHEMA_VERSION})")

    project = payload.get('project') or {}
    stats = payload.get('statistics') or {}
    cats = payload.get('category_statistics') or {}
    sec = payload.get('security_summary') or {}
    issues: List[dict] = payload.get('issues') or []
    hs = payload.get('security_hotspots') or {}
    hotspots: List[dict] = hs.get('items') or []
    scope = payload.get('scope') or {}
    qg = ((payload.get('quality_gate') or {}).get('projectStatus')) or {}

    if internal:
        by_sev = stats.get('by_severity') or {}
        total_issues = stats.get('total_issues', len(issues))
    else:
        # Customer scope excludes code smells, so count severities over the
        # remaining issues instead of trusting the payload-wide totals.
        scoped = [i for i in issues if i.get('type') != 'CODE_SMELL']
        by_sev = dict(Counter(i.get('severity') for i in scoped))
        total_issues = len(scoped)
    open_hotspots = sum(1 for h in hotspots if h.get('status') == 'TO_REVIEW')
    total_hotspots = sec.get('hotspots', len(hotspots))
    vulnerabilities = [i for i in issues if i.get('type') == 'VULNERABILITY']
    bugs = [i for i in issues if i.get('type') == 'BUG']
    smells = [i for i in issues if i.get('type') == 'CODE_SMELL']
    blockers = by_sev.get('BLOCKER', 0)

    def sev_sort(i):
        return (SEVERITY_ORDER.index(i.get('severity')) if i.get('severity') in SEVERITY_ORDER else 99,
                i.get('component_name') or '', i.get('line') or 0)

    def issue_row(i: dict) -> dict:
        return {
            'severity': UI_SEVERITY.get(i.get('severity'), i.get('severity')),
            'tone': SEVERITY_TONE.get(i.get('severity'), 'neutral'),
            'rule': i.get('rule', ''),
            'message': i.get('message', ''),
            'file': i.get('component_name') or i.get('component', ''),
            'line': i.get('line') or '-',
        }

    qg_status = project.get('quality_gate_status') or qg.get('status') or 'UNKNOWN'
    qg_ok = qg_status == 'OK'

    # Severity distribution as a single stacked bar. Segments carry label+count,
    # so colour never has to carry the meaning alone.
    segments = []
    for s in SEVERITY_ORDER:
        n = by_sev.get(s, 0)
        if n:
            segments.append({'label': UI_SEVERITY[s], 'count': n, 'tone': SEVERITY_TONE[s],
                             'pct': round(100.0 * n / total_issues, 2) if total_issues else 0})

    rule_counts = Counter(i.get('rule') for i in smells)
    rule_example = {}
    for i in smells:
        rule_example.setdefault(i.get('rule'), i.get('message', ''))
    top_rules = [{'rule': r, 'count': c, 'example': rule_example.get(r, '')}
                 for r, c in rule_counts.most_common(10)]

    high_smells = sorted([i for i in smells if i.get('severity') in ('BLOCKER', 'CRITICAL')], key=sev_sort)

    # Recommendations mirror the markdown template's logic, but only recommend
    # reviewing hotspots that are actually still open.
    p1, p2, p3 = [], [], []
    if blockers:
        p1.append(f'Fix {blockers} blocker-level issue(s) before the next release.')
    if vulnerabilities:
        p1.append(f'Remediate {len(vulnerabilities)} open vulnerability(ies).')
    if open_hotspots:
        p1.append(f'Review {open_hotspots} security hotspot(s) awaiting a decision.')
    if not qg_ok:
        p1.append('Bring the failing quality gate back to passing.')
    if bugs:
        p2.append(f'Fix {len(bugs)} reliability issue(s) (bugs).')
    if high_smells:
        p2.append(f'Address {len(high_smells)} high-severity maintainability issue(s).')
    if total_hotspots and not open_hotspots:
        p2.append(f'All {total_hotspots} security hotspot(s) have been reviewed. Re-review if the affected code changes.')
    cov = _metric(payload, 'coverage', 'value', None)
    if cov is not None:
        try:
            covf = float(cov)
            if covf < 80:
                p3.append(f'Increase test coverage from {covf:g}% towards 80%.' if covf > 0
                          else 'No test coverage is reported. Either tests are missing or coverage is not wired into the analysis pipeline.')
        except ValueError:
            pass
    dup = _metric(payload, 'duplicated_lines_density', 'value', None)
    if dup is not None:
        try:
            if float(dup) > 3:
                p3.append(f'Reduce code duplication ({float(dup):g}% of lines).')
        except ValueError:
            pass
    if smells:
        p3.append(f'Work down the {len(smells)} maintainability issue(s), starting with the most frequent rules below.')

    grouped = group_hotspots(hotspots)

    return {
        'schema_version': payload['schema_version'],
        'generated_at': _fmt_date(payload.get('generated_at')),
        'rendered_at': datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC'),
        'data_source': payload.get('data_source') or {},
        'project': {
            'name': project.get('name') or project.get('key', 'Unknown'),
            'key': project.get('key', ''),
            'organization': project.get('organization', ''),
            'last_analysis': _fmt_date(project.get('last_analysis_date')),
        },
        'quality_gate': {'status': qg_status, 'ok': qg_ok,
                         'conditions': [_condition_row(c) for c in qg.get('conditions') or []]},
        'audience': audience,
        'internal': internal,
        'kpis': [
            {'label': 'Quality gate', 'value': 'Passed' if qg_ok else qg_status.title(),
             'tone': 'good' if qg_ok else 'critical', 'sub': 'SonarCloud gate'},
            {'label': 'Open vulnerabilities', 'value': len(vulnerabilities),
             'tone': 'good' if not vulnerabilities else 'critical', 'sub': 'security issues'},
            {'label': 'Security hotspots', 'value': f'{open_hotspots} / {total_hotspots}',
             'tone': 'good' if not open_hotspots else 'warning', 'sub': 'awaiting review / total'},
            {'label': 'Bugs', 'value': len(bugs),
             'tone': 'good' if not bugs else ('warning' if len(bugs) < 10 else 'serious'), 'sub': 'reliability issues'},
        ] + ([
            {'label': 'Code smells', 'value': f'{len(smells):,}', 'tone': 'neutral', 'sub': 'maintainability issues'},
            {'label': 'Technical debt', 'value': stats.get('technical_debt') or _debt(stats.get('technical_debt_minutes')),
             'tone': 'neutral', 'sub': 'estimated remediation'},
        ] if internal else []),
        'ratings': [
            {'label': 'Security', 'value': _metric(payload, 'security_rating')},
            {'label': 'Reliability', 'value': _metric(payload, 'reliability_rating')},
            {'label': 'Maintainability', 'value': _metric(payload, 'sqale_rating')},
        ],
        'facts': [
            {'label': 'Lines of code', 'value': _metric(payload, 'ncloc')},
            {'label': 'Test coverage', 'value': _metric(payload, 'coverage')},
            {'label': 'Duplicated lines', 'value': _metric(payload, 'duplicated_lines_density')},
        ] if internal else [],
        'total_issues': total_issues,
        'segments': segments,
        'category_rows': [
            {'name': name, 'total': (cats.get(k) or {}).get('total', 0),
             'by': [((cats.get(k) or {}).get('by_severity') or {}).get(s, 0) for s in SEVERITY_ORDER]}
            for k, name in (('security', 'Security'), ('reliability', 'Reliability'))
            + ((('maintainability', 'Maintainability'),) if internal else ())
        ],
        'severity_headers': [UI_SEVERITY[s] for s in SEVERITY_ORDER],
        'vulnerabilities': [issue_row(i) for i in sorted(vulnerabilities, key=sev_sort)[:max_rows]],
        'vulnerabilities_total': len(vulnerabilities),
        'hotspot_summary': hotspot_summary(hotspots),
        'hotspots_open_rows': [g for g in grouped if g['open']][:max_rows],
        'hotspots_closed_rows': [g for g in grouped if not g['open']][:max_rows],
        'hotspots_grouped_total': len(grouped),
        'hotspots_has_justification': any(g['justification'] for g in grouped),
        'hotspots_total': total_hotspots,
        'hotspots_open': open_hotspots,
        'bugs': [issue_row(i) for i in sorted(bugs, key=sev_sort)[:max_rows]],
        'bugs_total': len(bugs),
        'high_smells': [issue_row(i) for i in high_smells[:max_rows]],
        'high_smells_total': len(high_smells),
        'top_rules': top_rules,
        'recommendations': {'p1': p1, 'p2': p2, 'p3': p3},
        'scope': {
            'severity_filter': [UI_SEVERITY.get(s, s) for s in scope.get('severity_filter') or []],
            'include_resolved': scope.get('include_resolved', False),
            'truncated': scope.get('issues_truncated', False),
            'exported': scope.get('issues_exported'),
            'total': scope.get('issues_total'),
        },
        'max_rows': max_rows,
    }


class HtmlReportRenderer:
    """Render a JSON payload to a single self-contained HTML file."""

    def __init__(self, template_path: Optional[str] = None, max_rows: int = 25, audience: str = 'customer'):
        self.max_rows = max_rows
        self.audience = audience
        if template_path and os.path.exists(template_path):
            template_dir, template_name = os.path.split(template_path)
        else:
            template_dir = os.path.join(os.path.dirname(__file__), 'templates')
            template_name = 'report.html.j2'
        self.env = jinja2.Environment(
            loader=jinja2.FileSystemLoader(template_dir),
            autoescape=True,
            trim_blocks=True,
            lstrip_blocks=True,
        )
        self.template = self.env.get_template(template_name)

    def render(self, payload: dict) -> str:
        return self.template.render(**build_view_model(payload, self.max_rows, self.audience))

    def render_to_file(self, payload: dict, output_path: str) -> str:
        out = Path(output_path)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(self.render(payload), encoding='utf-8')
        logger.info(f'HTML report written to {out}')
        return str(out)


_CHROME_CANDIDATES = (
    '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',
    '/Applications/Chromium.app/Contents/MacOS/Chromium',
    '/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge',
    '/Applications/Brave Browser.app/Contents/MacOS/Brave Browser',
    'google-chrome', 'google-chrome-stable', 'chromium', 'chromium-browser', 'chrome', 'msedge',
    r'C:\Program Files\Google\Chrome\Application\chrome.exe',
    r'C:\Program Files (x86)\Google\Chrome\Application\chrome.exe',
    r'C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe',
)


def find_chrome() -> Optional[str]:
    """Locate a Chromium-based browser. ``SONAR_REPORT_CHROME`` overrides discovery."""
    override = os.environ.get('SONAR_REPORT_CHROME')
    if override:
        return override if os.path.exists(override) else shutil.which(override)
    for cand in _CHROME_CANDIDATES:
        if os.path.sep in cand or cand.endswith('.exe'):
            if os.path.exists(cand):
                return cand
        else:
            found = shutil.which(cand)
            if found:
                return found
    return None


def html_to_pdf(html_path: str, pdf_path: str, chrome: Optional[str] = None, timeout: int = 120) -> str:
    """Print an HTML file to PDF with headless Chrome.

    Raises RuntimeError when no browser is found or Chrome exits non-zero, so a
    caller never ends up with a silently missing or half-written PDF.
    """
    chrome = chrome or find_chrome()
    if not chrome:
        raise RuntimeError(
            'No Chrome/Chromium found for PDF export. Install Google Chrome or set SONAR_REPORT_CHROME.')
    html_abs = Path(html_path).resolve()
    pdf_abs = Path(pdf_path).resolve()
    pdf_abs.parent.mkdir(parents=True, exist_ok=True)
    cmd = [
        chrome, '--headless=new', '--disable-gpu', '--no-first-run', '--no-default-browser-check',
        '--hide-scrollbars', '--no-pdf-header-footer',
        f'--print-to-pdf={pdf_abs}', html_abs.as_uri(),
    ]
    logger.debug('Running: %s', ' '.join(cmd))
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    except subprocess.TimeoutExpired:
        raise RuntimeError(f'Chrome timed out after {timeout}s printing {html_abs.name}')
    if proc.returncode != 0 or not pdf_abs.exists() or pdf_abs.stat().st_size == 0:
        raise RuntimeError(f'Chrome failed to produce {pdf_abs.name} (exit {proc.returncode}): {proc.stderr.strip()[-500:]}')
    logger.info(f'PDF written to {pdf_abs}')
    return str(pdf_abs)
