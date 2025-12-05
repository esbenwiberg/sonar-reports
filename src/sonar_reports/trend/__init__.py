"""Trend analysis module for generating trend reports from multiple SAST reports."""

from .parser import ReportParser
from .aggregator import TrendDataAggregator
from .models import ReportMetadata, TrendData
from .html_generator import HTMLTrendReportGenerator

__all__ = [
    'ReportParser',
    'TrendDataAggregator',
    'ReportMetadata',
    'TrendData',
    'HTMLTrendReportGenerator',
]