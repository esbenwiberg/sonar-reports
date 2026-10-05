"""Regression tests for Issue.get_effort_minutes().

SonarCloud reports effort as compound strings ("1h58min", "3d2h15min").
The original parser stripped a single unit and fed the remainder to int(),
so any compound value raised ValueError and killed the whole report run.
"""

import pytest

from sonar_reports.models.issue import Issue


def issue_with(effort):
    return Issue(
        key='K',
        type='CODE_SMELL',
        severity='MAJOR',
        status='OPEN',
        message='m',
        component='c',
        line=1,
        creation_date=None,
        tags=[],
        rule='r',
        effort=effort,
    )


HOUR = 60
DAY = 8 * 60  # SonarCloud's working day


@pytest.mark.parametrize('effort,expected', [
    # single unit — the only cases that ever worked
    ('5min', 5),
    ('1h', HOUR),
    ('2d', 2 * DAY),
    # compound — every one of these used to raise
    ('1h58min', HOUR + 58),
    ('1h10min', HOUR + 10),
    ('4h30min', 4 * HOUR + 30),
    ('1d4h', DAY + 4 * HOUR),
    ('3d2h15min', 3 * DAY + 2 * HOUR + 15),
    # formatting variance
    ('1H58MIN', HOUR + 58),
    ('  2h ', 2 * HOUR),
    ('1d 4h 30min', DAY + 4 * HOUR + 30),
    # unitless value is read as minutes
    ('90', 90),
    ('90.0', 90),
])
def test_parses_effort(effort, expected):
    assert issue_with(effort).get_effort_minutes() == expected


@pytest.mark.parametrize('effort', [None, '', '   ', 'unknown', 'abc', '-'])
def test_unparseable_effort_is_zero_not_an_exception(effort):
    assert issue_with(effort).get_effort_minutes() == 0


def test_min_is_not_swallowed_by_the_shorter_units():
    """'min' contains no 'd'/'h', but the alternation order still matters:
    a naive pattern could match 'm' or split the token."""
    assert issue_with('45min').get_effort_minutes() == 45


def test_no_regression_on_the_three_projects_that_failed():
    """The exact values that broke CopyToolBundle, Power-Financials, PowerGantt."""
    for effort in ('158min', '1h58min', '110min', '1h10min', '430min', '4h30min'):
        assert issue_with(effort).get_effort_minutes() > 0


def test_effort_is_summed_across_a_realistic_issue_set():
    efforts = ['5min', '1h', '1h58min', '1d4h', '3d2h15min', None, 'garbage']
    total = sum(issue_with(e).get_effort_minutes() for e in efforts)
    assert total == 5 + HOUR + (HOUR + 58) + (DAY + 4 * HOUR) + (3 * DAY + 2 * HOUR + 15)


class TestMetricValueHardening:
    """A null metric value used to reach float() and raise TypeError, which the
    surrounding `except ValueError` did not catch."""

    def test_null_value_becomes_zero(self):
        from sonar_reports.models.metric import Metric
        assert Metric.from_api_response({'metric': 'ncloc', 'value': None}).value == '0'

    def test_missing_value_becomes_zero(self):
        from sonar_reports.models.metric import Metric
        assert Metric.from_api_response({'metric': 'ncloc'}).value == '0'

    def test_numeric_value_is_stringified(self):
        from sonar_reports.models.metric import Metric
        assert Metric.from_api_response({'metric': 'ncloc', 'value': 1234}).value == '1234'

    @pytest.mark.parametrize('key', ['ncloc', 'coverage', 'sqale_index', 'security_rating'])
    def test_formatting_never_raises_on_null(self, key):
        from sonar_reports.models.metric import Metric
        Metric.from_api_response({'metric': key, 'value': None}).get_formatted_value()

    def test_non_numeric_value_is_passed_through(self):
        from sonar_reports.models.metric import Metric
        m = Metric.from_api_response({'metric': 'ncloc', 'value': 'n/a'})
        assert m.get_formatted_value() == 'n/a'
