"""Aggregator for building trend data from multiple reports."""

import logging
from typing import List
from datetime import datetime

from .models import ReportMetadata, TrendData, TrendSeries, TrendDataPoint


logger = logging.getLogger(__name__)


class TrendDataAggregator:
    """Aggregate metrics from multiple reports into trend data."""
    
    def aggregate_reports(self, reports: List[ReportMetadata]) -> TrendData:
        """
        Combine data from multiple reports into trend data.
        
        Args:
            reports: List of ReportMetadata objects (should be sorted by date)
            
        Returns:
            TrendData object with all trend series
        """
        if not reports:
            raise ValueError("No reports provided for aggregation")
        
        sorted_reports = sorted(reports, key=lambda x: x.analysis_date)
        
        first_report = sorted_reports[0]
        project_key = first_report.project_key
        project_name = first_report.project_name
        organization = first_report.organization
        
        for report in sorted_reports:
            if report.project_key != project_key:
                logger.warning(
                    f"Report {report.file_path} is for different project "
                    f"({report.project_key} vs {project_key})"
                )
        
        blocker_trend = self._build_series("Blocker Issues", sorted_reports, 
                                           lambda r: r.blocker_issues, "#d32f2f")
        critical_trend = self._build_series("Critical Issues", sorted_reports,
                                            lambda r: r.critical_issues, "#f57c00")
        major_trend = self._build_series("Major Issues", sorted_reports,
                                         lambda r: r.major_issues, "#fbc02d")
        security_trend = self._build_series("Security Issues", sorted_reports,
                                            lambda r: r.security_issues, "#c62828")
        vulnerabilities_trend = self._build_series("Vulnerabilities", sorted_reports,
                                                   lambda r: r.vulnerabilities, "#d32f2f")
        hotspots_trend = self._build_series("Security Hotspots", sorted_reports,
                                            lambda r: r.security_hotspots, "#f57c00")
        coverage_trend = self._build_series("Code Coverage", sorted_reports,
                                            lambda r: r.code_coverage, "#0288d1")
        quality_gate_trend = self._build_series("Quality Gate", sorted_reports,
                                                lambda r: 1 if r.quality_gate_passed else 0, "#4caf50")
        
        return TrendData(
            project_key=project_key,
            project_name=project_name,
            organization=organization,
            reports=sorted_reports,
            start_date=sorted_reports[0].analysis_date,
            end_date=sorted_reports[-1].analysis_date,
            blocker_trend=blocker_trend,
            critical_trend=critical_trend,
            major_trend=major_trend,
            security_trend=security_trend,
            vulnerabilities_trend=vulnerabilities_trend,
            hotspots_trend=hotspots_trend,
            coverage_trend=coverage_trend,
            quality_gate_trend=quality_gate_trend,
        )
    
    def _build_series(self, name: str, reports: List[ReportMetadata],
                     value_extractor, color: str = None) -> TrendSeries:
        """
        Build a trend series from reports.
        
        Args:
            name: Name of the series
            reports: List of reports
            value_extractor: Function to extract value from report
            color: Optional color for the series
            
        Returns:
            TrendSeries object
        """
        data_points = []
        
        for report in reports:
            value = value_extractor(report)
            data_point = TrendDataPoint(
                date=report.analysis_date,
                value=float(value),
                metadata=report
            )
            data_points.append(data_point)
        
        return TrendSeries(
            name=name,
            data_points=data_points,
            color=color
        )
    
    def calculate_velocity(self, trend_series: TrendSeries) -> dict:
        """
        Calculate velocity metrics for a trend series.
        
        Args:
            trend_series: TrendSeries to analyze
            
        Returns:
            Dictionary with velocity metrics
        """
        if len(trend_series.data_points) < 2:
            return {
                'rate_per_week': 0,
                'rate_per_day': 0,
                'total_change': 0,
                'days_elapsed': 0
            }
        
        first = trend_series.data_points[0]
        last = trend_series.data_points[-1]
        
        total_change = last.value - first.value
        days_elapsed = (last.date - first.date).days
        
        if days_elapsed == 0:
            return {
                'rate_per_week': 0,
                'rate_per_day': 0,
                'total_change': total_change,
                'days_elapsed': 0
            }
        
        rate_per_day = total_change / days_elapsed
        rate_per_week = rate_per_day * 7
        
        return {
            'rate_per_week': rate_per_week,
            'rate_per_day': rate_per_day,
            'total_change': total_change,
            'days_elapsed': days_elapsed
        }
    
    def identify_regressions(self, trend_data: TrendData, threshold: float = 10.0) -> List[dict]:
        """
        Identify significant regressions in the trend data.
        
        Args:
            trend_data: TrendData to analyze
            threshold: Percentage threshold for identifying regressions
            
        Returns:
            List of regression events
        """
        regressions = []
        
        blocker_change = trend_data.blocker_trend.get_change()
        if blocker_change['percent'] > threshold:
            regressions.append({
                'metric': 'Blocker Issues',
                'change': blocker_change,
                'severity': 'critical'
            })
        
        critical_change = trend_data.critical_trend.get_change()
        if critical_change['percent'] > threshold:
            regressions.append({
                'metric': 'Critical Issues',
                'change': critical_change,
                'severity': 'high'
            })
        
        security_change = trend_data.security_trend.get_change()
        if security_change['percent'] > threshold:
            regressions.append({
                'metric': 'Security Issues',
                'change': security_change,
                'severity': 'high'
            })
        
        coverage_change = trend_data.coverage_trend.get_change()
        if coverage_change['percent'] < -threshold:
            regressions.append({
                'metric': 'Code Coverage',
                'change': coverage_change,
                'severity': 'medium'
            })
        
        return regressions
    
    def identify_improvements(self, trend_data: TrendData, threshold: float = 10.0) -> List[dict]:
        """
        Identify significant improvements in the trend data.
        
        Args:
            trend_data: TrendData to analyze
            threshold: Percentage threshold for identifying improvements
            
        Returns:
            List of improvement events
        """
        improvements = []
        
        blocker_change = trend_data.blocker_trend.get_change()
        if blocker_change['percent'] < -threshold:
            improvements.append({
                'metric': 'Blocker Issues',
                'change': blocker_change,
                'impact': 'high'
            })
        
        critical_change = trend_data.critical_trend.get_change()
        if critical_change['percent'] < -threshold:
            improvements.append({
                'metric': 'Critical Issues',
                'change': critical_change,
                'impact': 'high'
            })
        
        security_change = trend_data.security_trend.get_change()
        if security_change['percent'] < -threshold:
            improvements.append({
                'metric': 'Security Issues',
                'change': security_change,
                'impact': 'high'
            })
        
        coverage_change = trend_data.coverage_trend.get_change()
        if coverage_change['percent'] > threshold:
            improvements.append({
                'metric': 'Code Coverage',
                'change': coverage_change,
                'impact': 'medium'
            })
        
        return improvements