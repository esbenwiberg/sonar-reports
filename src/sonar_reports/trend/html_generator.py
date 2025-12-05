"""HTML trend report generator with Chart.js integration."""

import logging
import json
from pathlib import Path
from datetime import datetime

from .models import TrendData


logger = logging.getLogger(__name__)


class HTMLTrendReportGenerator:
    """Generate interactive HTML trend reports with Chart.js."""
    
    def __init__(self):
        """Initialize the HTML generator."""
        self.chart_js_cdn = "https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js"
    
    def generate(self, trend_data: TrendData, output_path: str) -> str:
        """
        Generate HTML trend report.
        
        Args:
            trend_data: TrendData object with all metrics
            output_path: Path to save the HTML file
            
        Returns:
            Path to generated HTML file
        """
        logger.info(f"Generating HTML trend report for {trend_data.project_name}")
        
        html_content = self._build_html(trend_data)
        
        output_file = Path(output_path)
        output_file.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        logger.info(f"HTML trend report saved to {output_path}")
        return str(output_file)
    
    def _build_html(self, td: TrendData) -> str:
        """Build complete HTML document."""
        summary = td.calculate_summary_stats()
        current = td.get_current_report()
        
        dates = json.dumps(td.blocker_trend.get_dates())
        blocker_data = json.dumps(td.blocker_trend.get_values())
        critical_data = json.dumps(td.critical_trend.get_values())
        major_data = json.dumps(td.major_trend.get_values())
        vuln_data = json.dumps(td.vulnerabilities_trend.get_values())
        hotspot_data = json.dumps(td.hotspots_trend.get_values())
        security_data = json.dumps(td.security_trend.get_values())
        coverage_data = json.dumps(td.coverage_trend.get_values())
        qg_data = json.dumps([1 if r.quality_gate_passed else 0 for r in td.reports])
        
        trend_emoji = '📈' if summary['overall_trend'] == 'improving' else '📉' if summary['overall_trend'] == 'declining' else '➡️'
        
        with open(Path(__file__).parent.parent.parent.parent / 'docs' / 'sample-trend-report.html', 'r', encoding='utf-8') as f:
            template = f.read()
        
        html = template.replace('PM.PowerHub', td.project_name)
        html = html.replace('365projectum_PM.PowerHub', td.project_key)
        html = html.replace('2025-11-01 to 2025-12-04', td.get_date_range_str())
        html = html.replace('Reports Analyzed: 8', f'Reports Analyzed: {td.get_report_count()}')
        html = html.replace('📈 Executive Summary: Improving', f'{trend_emoji} Executive Summary: {summary["overall_trend"].capitalize()}')
        
        # Update executive summary cards
        blocker_current = int(td.blocker_trend.get_values()[-1])
        critical_current = int(td.critical_trend.get_values()[-1])
        security_current = int(td.security_trend.get_values()[-1])
        coverage_current = td.coverage_trend.get_values()[-1]
        
        blocker_change = td.blocker_trend.get_change()
        critical_change = td.critical_trend.get_change()
        security_change = td.security_trend.get_change()
        coverage_change = td.coverage_trend.get_change()
        
        # Replace summary card values
        html = html.replace('<div class="value">1</div>\n                    <div class="change">-50%',
                           f'<div class="value">{blocker_current}</div>\n                    <div class="change">{blocker_change.get("percent", 0):.0f}%')
        html = html.replace('<div class="value">66</div>\n                    <div class="change">-35%',
                           f'<div class="value">{critical_current}</div>\n                    <div class="change">{critical_change.get("percent", 0):.0f}%')
        html = html.replace('<div class="value">2</div>\n                    <div class="change">-60%',
                           f'<div class="value">{security_current}</div>\n                    <div class="change">{security_change.get("percent", 0):.0f}%')
        html = html.replace('<div class="value">3.4%</div>\n                    <div class="change">+62%',
                           f'<div class="value">{coverage_current:.1f}%</div>\n                    <div class="change">{coverage_change.get("percent", 0):+.0f}%')
        
        html = html.replace("const dates = ['2025-11-01', '2025-11-08', '2025-11-15', '2025-11-22', '2025-11-29', '2025-12-04'];",
                           f"const dates = {dates};")
        html = html.replace('data: [2, 2, 2, 1, 1, 1]', f'data: {blocker_data}')
        html = html.replace('data: [95, 102, 89, 78, 71, 66]', f'data: {critical_data}')
        html = html.replace('data: [342, 338, 345, 328, 332, 335]', f'data: {major_data}')
        html = html.replace('data: [12, 11, 10, 9, 8, 7]', f'data: {vuln_data}')
        html = html.replace('data: [7, 7, 7, 7, 7, 7]', f'data: {hotspot_data}')
        html = html.replace('data: [5, 5, 4, 3, 2, 2]', f'data: {security_data}')
        html = html.replace('data: [2.1, 2.3, 2.5, 2.8, 3.1, 3.4]', f'data: {coverage_data}')
        html = html.replace('const qgData = [0, 0, 0, 0, 0, 0];', f'const qgData = {qg_data};')
        
        return html