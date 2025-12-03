"""Report data aggregation model."""

from dataclasses import dataclass
from typing import List, Dict
from collections import defaultdict

from .issue import Issue
from .metric import Metric
from .project import ProjectInfo


@dataclass
class ReportData:
    """Aggregated data for report generation."""
    
    project_info: ProjectInfo
    issues: List[Issue]
    metrics: List[Metric]
    quality_gate_status: dict
    security_hotspots: List[dict]
    
    def get_issues_by_severity(self) -> Dict[str, List[Issue]]:
        """
        Group issues by severity level.
        
        Returns:
            Dictionary mapping severity to list of issues
        """
        by_severity = defaultdict(list)
        for issue in self.issues:
            by_severity[issue.severity].append(issue)
        
        # Sort issues within each severity by priority
        for severity in by_severity:
            by_severity[severity].sort(
                key=lambda x: (x.get_severity_priority(), x.creation_date),
                reverse=True
            )
        
        return dict(by_severity)
    
    def get_issues_by_type(self) -> Dict[str, List[Issue]]:
        """
        Group issues by type.
        
        Returns:
            Dictionary mapping type to list of issues
        """
        by_type = defaultdict(list)
        for issue in self.issues:
            by_type[issue.type].append(issue)
        
        # Sort issues within each type by severity
        for issue_type in by_type:
            by_type[issue_type].sort(
                key=lambda x: x.get_severity_priority(),
                reverse=True
            )
        
        return dict(by_type)
    
    def get_security_issues(self) -> List[Issue]:
        """
        Get all security-related issues.
        
        Returns:
            List of security issues sorted by severity
        """
        security_issues = [issue for issue in self.issues if issue.is_security_issue()]
        security_issues.sort(key=lambda x: x.get_severity_priority(), reverse=True)
        return security_issues
    
    def get_security_summary(self) -> dict:
        """
        Get security-specific statistics.
        
        Returns:
            Dictionary with security metrics
        """
        security_issues = self.get_security_issues()
        by_severity = defaultdict(int)
        
        for issue in security_issues:
            by_severity[issue.severity] += 1
        
        return {
            'total': len(security_issues),
            'by_severity': dict(by_severity),
            'vulnerabilities': len([i for i in security_issues if i.type == 'VULNERABILITY']),
            'hotspots': len(self.security_hotspots),
        }
    
    def get_top_issues(self, limit: int = 10) -> List[Issue]:
        """
        Get top priority issues.
        
        Args:
            limit: Maximum number of issues to return
            
        Returns:
            List of top issues sorted by priority
        """
        sorted_issues = sorted(
            self.issues,
            key=lambda x: (x.get_severity_priority(), x.is_security_issue()),
            reverse=True
        )
        return sorted_issues[:limit]
    
    def get_category_statistics(self) -> dict:
        """
        Calculate statistics grouped by SonarQube categories (Security, Reliability, Maintainability).
        
        Returns:
            Dictionary with category-based statistics including severity counts
        """
        categories = {
            'security': {'total': 0, 'by_severity': defaultdict(int)},
            'reliability': {'total': 0, 'by_severity': defaultdict(int)},
            'maintainability': {'total': 0, 'by_severity': defaultdict(int)},
        }
        
        for issue in self.issues:
            if issue.type == 'VULNERABILITY':
                categories['security']['total'] += 1
                categories['security']['by_severity'][issue.severity] += 1
            elif issue.type == 'BUG':
                categories['reliability']['total'] += 1
                categories['reliability']['by_severity'][issue.severity] += 1
            elif issue.type == 'CODE_SMELL':
                categories['maintainability']['total'] += 1
                categories['maintainability']['by_severity'][issue.severity] += 1
        
        # Convert defaultdicts to regular dicts
        for category in categories.values():
            category['by_severity'] = dict(category['by_severity'])
        
        return categories
    
    def calculate_statistics(self) -> dict:
        """
        Calculate summary statistics.
        
        Returns:
            Dictionary with various statistics
        """
        by_severity = defaultdict(int)
        by_type = defaultdict(int)
        total_debt_minutes = 0
        
        for issue in self.issues:
            by_severity[issue.severity] += 1
            by_type[issue.type] += 1
            total_debt_minutes += issue.get_effort_minutes()
        
        # Convert total debt to readable format
        days = total_debt_minutes // (8 * 60)
        remaining = total_debt_minutes % (8 * 60)
        hours = remaining // 60
        
        debt_str = []
        if days > 0:
            debt_str.append(f"{days}d")
        if hours > 0:
            debt_str.append(f"{hours}h")
        
        return {
            'total_issues': len(self.issues),
            'by_severity': dict(by_severity),
            'by_type': dict(by_type),
            'security_issues': len(self.get_security_issues()),
            'technical_debt': " ".join(debt_str) if debt_str else "0h",
            'technical_debt_minutes': total_debt_minutes,
        }
    
    def get_metric_value(self, metric_key: str) -> str:
        """
        Get value for a specific metric.
        
        Args:
            metric_key: Metric key to look up
            
        Returns:
            Metric value or 'N/A' if not found
        """
        for metric in self.metrics:
            if metric.key == metric_key:
                return metric.get_formatted_value()
        return 'N/A'
    
    def get_owasp_coverage(self) -> Dict[str, int]:
        """
        Analyze OWASP Top 10 coverage based on issue tags.
        
        Returns:
            Dictionary mapping OWASP categories to issue counts
        """
        owasp_map = {
            'A01:2021': 'Broken Access Control',
            'A02:2021': 'Cryptographic Failures',
            'A03:2021': 'Injection',
            'A04:2021': 'Insecure Design',
            'A05:2021': 'Security Misconfiguration',
            'A06:2021': 'Vulnerable Components',
            'A07:2021': 'Authentication Failures',
            'A08:2021': 'Software and Data Integrity',
            'A09:2021': 'Security Logging Failures',
            'A10:2021': 'Server-Side Request Forgery',
        }
        
        owasp_counts = defaultdict(int)
        
        for issue in self.get_security_issues():
            for tag in issue.tags:
                tag_upper = tag.upper()
                # Check if tag matches OWASP pattern
                for owasp_key in owasp_map:
                    if owasp_key.replace(':', '').replace('-', '') in tag_upper.replace('-', ''):
                        owasp_counts[owasp_key] += 1
        
        return dict(owasp_counts)
    
    def __str__(self) -> str:
        """String representation of report data."""
        stats = self.calculate_statistics()
        return (
            f"ReportData(project={self.project_info.name}, "
            f"issues={stats['total_issues']}, "
            f"security={stats['security_issues']}, "
            f"debt={stats['technical_debt']})"
        )