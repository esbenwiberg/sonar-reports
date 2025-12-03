"""Report generator for creating Markdown reports."""

import os
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional
import jinja2
from tabulate import tabulate

from ..models import ReportData


logger = logging.getLogger(__name__)


class ReportGenerator:
    """Generate Markdown reports from report data."""
    
    def __init__(self, template_path: Optional[str] = None, max_issues_per_section: int = 10):
        """
        Initialize report generator.
        
        Args:
            template_path: Path to custom Jinja2 template (optional)
            max_issues_per_section: Maximum issues to show per section
        """
        self.max_issues_per_section = max_issues_per_section
        
        if template_path and os.path.exists(template_path):
            template_dir = os.path.dirname(template_path)
            template_name = os.path.basename(template_path)
        else:
            # Use default template
            template_dir = os.path.join(os.path.dirname(__file__), 'templates')
            template_name = 'report.md.j2'
        
        self.env = jinja2.Environment(
            loader=jinja2.FileSystemLoader(template_dir),
            trim_blocks=True,
            lstrip_blocks=True,
        )
        
        # Add custom filters
        self.env.filters['format_table'] = self._format_table
        
        self.template = self.env.get_template(template_name)
    
    def generate(self, report_data: ReportData, output_path: str) -> str:
        """
        Generate report and save to file.
        
        Args:
            report_data: Report data to generate from
            output_path: Path to save report
            
        Returns:
            Path to generated report
        """
        logger.info(f"Generating report for {report_data.project_info.name}")
        
        # Render template
        content = self._render_template(report_data)
        
        # Ensure output directory exists
        output_file = Path(output_path)
        output_file.parent.mkdir(parents=True, exist_ok=True)
        
        # Write to file
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(content)
        
        logger.info(f"Report saved to {output_path}")
        return str(output_file)
    
    def _render_template(self, report_data: ReportData) -> str:
        """
        Render Jinja2 template with data.
        
        Args:
            report_data: Report data
            
        Returns:
            Rendered template string
        """
        # Prepare data for template
        statistics = report_data.calculate_statistics()
        category_stats = report_data.get_category_statistics()
        issues_by_severity = report_data.get_issues_by_severity()
        issues_by_type = report_data.get_issues_by_type()
        security_issues = report_data.get_security_issues()
        security_summary = report_data.get_security_summary()
        
        # Group security issues by severity
        security_by_severity = {}
        for severity in ['BLOCKER', 'CRITICAL', 'MAJOR']:
            security_by_severity[severity] = [
                issue for issue in security_issues
                if issue.severity == severity
            ][:self.max_issues_per_section]
        
        context = {
            'project_info': report_data.project_info,
            'generation_date': datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC'),
            'statistics': statistics,
            'category_stats': category_stats,
            'issues_by_severity': issues_by_severity,
            'issues_by_type': issues_by_type,
            'security_issues': security_issues[:self.max_issues_per_section],
            'security_by_severity': security_by_severity,
            'security_summary': security_summary,
            'security_hotspots': report_data.security_hotspots[:self.max_issues_per_section],
            'metrics': report_data.metrics,
            'quality_gate_status': report_data.project_info.quality_gate_status,
            'quality_gate_emoji': report_data.project_info.get_quality_gate_emoji(),
            'top_issues': report_data.get_top_issues(self.max_issues_per_section),
            'max_issues': self.max_issues_per_section,
        }
        
        return self.template.render(**context)
    
    @staticmethod
    def _format_table(data: list, headers: list) -> str:
        """
        Format data as Markdown table.
        
        Args:
            data: List of rows
            headers: List of column headers
            
        Returns:
            Markdown table string
        """
        if not data:
            return "_No data available_"
        
        return tabulate(data, headers=headers, tablefmt='github')