"""Data models for trend analysis."""

from dataclasses import dataclass, field
from typing import List, Dict, Optional
from datetime import datetime


@dataclass
class ReportMetadata:
    """Metadata extracted from a single report."""
    
    # Report info
    report_version: str
    generated_date: datetime
    analysis_date: datetime
    file_path: str
    
    # Project info
    project_key: str
    project_name: str
    organization: str
    
    # Quality gate
    quality_gate_status: str
    quality_gate_passed: bool
    
    # Issue metrics
    total_issues: int
    blocker_issues: int
    critical_issues: int
    major_issues: int
    minor_issues: int
    info_issues: int
    
    # Category metrics
    security_issues: int
    reliability_issues: int
    maintainability_issues: int
    
    # Type metrics
    vulnerabilities: int
    bugs: int
    code_smells: int
    security_hotspots: int
    
    # Quality metrics
    code_coverage: float
    reliability_rating: str
    security_rating: str
    maintainability_rating: str
    
    # Category breakdown
    security_by_severity: Dict[str, int] = field(default_factory=dict)
    reliability_by_severity: Dict[str, int] = field(default_factory=dict)
    maintainability_by_severity: Dict[str, int] = field(default_factory=dict)
    
    def get_rating_numeric(self, rating: str) -> int:
        """Convert letter rating to numeric (A=5, E=1)."""
        rating_map = {'A': 5, 'B': 4, 'C': 3, 'D': 2, 'E': 1}
        return rating_map.get(rating, 0)
    
    def get_date_str(self) -> str:
        """Get formatted date string for display."""
        return self.analysis_date.strftime('%Y-%m-%d')


@dataclass
class TrendDataPoint:
    """Single data point in a trend."""
    
    date: datetime
    value: float
    metadata: Optional[ReportMetadata] = None
    
    def get_date_str(self) -> str:
        """Get formatted date string."""
        return self.date.strftime('%Y-%m-%d')


@dataclass
class TrendSeries:
    """A series of trend data points."""
    
    name: str
    data_points: List[TrendDataPoint]
    color: Optional[str] = None
    
    def get_dates(self) -> List[str]:
        """Get list of date strings."""
        return [dp.get_date_str() for dp in self.data_points]
    
    def get_values(self) -> List[float]:
        """Get list of values."""
        return [dp.value for dp in self.data_points]
    
    def get_change(self) -> Dict[str, any]:
        """Calculate change from first to last data point."""
        if len(self.data_points) < 2:
            return {'absolute': 0, 'percent': 0, 'direction': 'stable'}
        
        first = self.data_points[0].value
        last = self.data_points[-1].value
        absolute_change = last - first
        
        if first == 0:
            percent_change = 0 if last == 0 else 100
        else:
            percent_change = (absolute_change / first) * 100
        
        direction = 'improving' if absolute_change < 0 else ('declining' if absolute_change > 0 else 'stable')
        
        return {
            'absolute': absolute_change,
            'percent': percent_change,
            'direction': direction,
            'first': first,
            'last': last
        }


@dataclass
class TrendData:
    """Aggregated trend data from multiple reports."""
    
    project_key: str
    project_name: str
    organization: str
    reports: List[ReportMetadata]
    start_date: datetime
    end_date: datetime
    
    # Trend series
    blocker_trend: TrendSeries
    critical_trend: TrendSeries
    major_trend: TrendSeries
    security_trend: TrendSeries
    vulnerabilities_trend: TrendSeries
    hotspots_trend: TrendSeries
    coverage_trend: TrendSeries
    quality_gate_trend: TrendSeries
    
    def get_date_range_str(self) -> str:
        """Get formatted date range string."""
        return f"{self.start_date.strftime('%Y-%m-%d')} to {self.end_date.strftime('%Y-%m-%d')}"
    
    def get_report_count(self) -> int:
        """Get number of reports analyzed."""
        return len(self.reports)
    
    def get_current_report(self) -> Optional[ReportMetadata]:
        """Get the most recent report."""
        return self.reports[-1] if self.reports else None
    
    def get_previous_report(self) -> Optional[ReportMetadata]:
        """Get the first report for comparison."""
        return self.reports[0] if self.reports else None
    
    def get_overall_trend(self) -> str:
        """Determine overall trend direction."""
        # Check critical metrics
        critical_change = self.critical_trend.get_change()
        security_change = self.security_trend.get_change()
        
        # If both critical and security are improving, overall is improving
        if critical_change['direction'] == 'improving' and security_change['direction'] == 'improving':
            return 'improving'
        
        # If either is declining significantly, overall is declining
        if critical_change['direction'] == 'declining' or security_change['direction'] == 'declining':
            return 'declining'
        
        return 'stable'
    
    def get_quality_gate_pass_rate(self) -> float:
        """Calculate quality gate pass rate."""
        if not self.reports:
            return 0.0
        
        passed = sum(1 for r in self.reports if r.quality_gate_passed)
        return (passed / len(self.reports)) * 100
    
    def calculate_summary_stats(self) -> Dict[str, any]:
        """Calculate summary statistics for the trend."""
        current = self.get_current_report()
        previous = self.get_previous_report()
        
        if not current or not previous:
            return {}
        
        return {
            'overall_trend': self.get_overall_trend(),
            'report_count': self.get_report_count(),
            'date_range': self.get_date_range_str(),
            'quality_gate_pass_rate': self.get_quality_gate_pass_rate(),
            'blocker_change': self.blocker_trend.get_change(),
            'critical_change': self.critical_trend.get_change(),
            'security_change': self.security_trend.get_change(),
            'coverage_change': self.coverage_trend.get_change(),
            'current_metrics': {
                'blocker': current.blocker_issues,
                'critical': current.critical_issues,
                'major': current.major_issues,
                'security': current.security_issues,
                'coverage': current.code_coverage,
                'quality_gate': current.quality_gate_status,
                'security_rating': current.security_rating,
                'reliability_rating': current.reliability_rating,
                'maintainability_rating': current.maintainability_rating,
            },
            'previous_metrics': {
                'blocker': previous.blocker_issues,
                'critical': previous.critical_issues,
                'major': previous.major_issues,
                'security': previous.security_issues,
                'coverage': previous.code_coverage,
            }
        }