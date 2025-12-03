"""Data processor for transforming SonarCloud API data into report data."""

import logging
from typing import List

from ..api.client import SonarCloudClient
from ..models import Issue, Metric, ProjectInfo, ReportData


logger = logging.getLogger(__name__)


class DataProcessor:
    """Process raw API data into structured report data."""
    
    def __init__(self, api_client: SonarCloudClient):
        """
        Initialize data processor.
        
        Args:
            api_client: SonarCloud API client instance
        """
        self.api_client = api_client
    
    def fetch_all_data(self, project_key: str, include_resolved: bool = False) -> ReportData:
        """
        Fetch and process all data for a project.
        
        Args:
            project_key: SonarCloud project key
            include_resolved: Whether to include resolved issues
            
        Returns:
            ReportData instance with all processed data
        """
        logger.info(f"Fetching data for project: {project_key}")
        
        # Fetch raw data from API
        logger.info("Fetching issues...")
        statuses = ['OPEN', 'CONFIRMED', 'REOPENED']
        if include_resolved:
            statuses.extend(['RESOLVED', 'CLOSED'])
        raw_issues = self.api_client.get_issues(project_key, statuses)
        
        logger.info("Fetching security hotspots...")
        security_hotspots = self.api_client.get_security_hotspots(project_key)
        
        logger.info("Fetching metrics...")
        raw_metrics = self.api_client.get_metrics(project_key)
        
        logger.info("Fetching project info...")
        project_info_data = self.api_client.get_project_info(project_key)
        
        logger.info("Fetching quality gate status...")
        quality_gate_data = self.api_client.get_quality_gate_status(project_key)
        
        # Process data into models
        logger.info("Processing data...")
        issues = self.process_issues(raw_issues)
        metrics = self.process_metrics(raw_metrics)
        project_info = ProjectInfo.from_api_response(project_info_data, quality_gate_data)
        
        logger.info(f"Processed {len(issues)} issues and {len(metrics)} metrics")
        
        return ReportData(
            project_info=project_info,
            issues=issues,
            metrics=metrics,
            quality_gate_status=quality_gate_data,
            security_hotspots=security_hotspots,
        )
    
    def process_issues(self, raw_issues: List[dict]) -> List[Issue]:
        """
        Convert raw API issues to Issue objects.
        
        Args:
            raw_issues: List of issue dictionaries from API
            
        Returns:
            List of Issue objects
        """
        issues = []
        for raw_issue in raw_issues:
            try:
                issue = Issue.from_api_response(raw_issue)
                issues.append(issue)
            except Exception as e:
                logger.warning(f"Failed to process issue {raw_issue.get('key', 'unknown')}: {e}")
        
        return issues
    
    def process_metrics(self, raw_metrics: List[dict]) -> List[Metric]:
        """
        Convert raw API metrics to Metric objects.
        
        Args:
            raw_metrics: List of metric dictionaries from API
            
        Returns:
            List of Metric objects
        """
        metrics = []
        for raw_metric in raw_metrics:
            try:
                metric = Metric.from_api_response(raw_metric)
                metrics.append(metric)
            except Exception as e:
                logger.warning(f"Failed to process metric {raw_metric.get('metric', 'unknown')}: {e}")
        
        return metrics