# Implementation Plan - SonarCloud SAST Report Generator

## Phase 1: Project Setup

### 1.1 Directory Structure
Create the following structure:
```
sonar-reports/
├── src/
│   └── sonar_reports/
│       ├── __init__.py
│       ├── cli.py
│       ├── config.py
│       ├── api/
│       ├── models/
│       ├── processors/
│       └── report/
├── tests/
├── config/
├── reports/
├── requirements.txt
├── setup.py
├── README.md
└── .gitignore
```

### 1.2 Dependencies (requirements.txt)
```
requests>=2.31.0
python-dotenv>=1.0.0
pyyaml>=6.0.1
jinja2>=3.1.2
click>=8.1.7
tabulate>=0.9.0
```

### 1.3 Development Dependencies
```
pytest>=7.4.3
black>=23.12.0
mypy>=1.7.1
pylint>=3.0.3
```

## Phase 2: Core Components Implementation

### 2.1 Configuration Manager (config.py)

**Purpose**: Load and validate configuration from multiple sources

**Implementation Details**:
```python
class Config:
    def __init__(self):
        self.sonarcloud_token: str
        self.organization: str
        self.project_key: str
        self.base_url: str = "https://sonarcloud.io/api"
        self.output_path: str = "./reports"
        self.include_resolved: bool = False
        self.severity_filter: List[str] = ["BLOCKER", "CRITICAL", "MAJOR"]
    
    @classmethod
    def from_env(cls) -> Config
    
    @classmethod
    def from_file(cls, path: str) -> Config
    
    def validate(self) -> bool
```

**Configuration Priority**:
1. Command-line arguments (highest)
2. Environment variables
3. Config file
4. Defaults (lowest)

**Environment Variables**:
- `SONARCLOUD_TOKEN`
- `SONARCLOUD_ORGANIZATION`
- `SONARCLOUD_PROJECT_KEY`
- `SONARCLOUD_BASE_URL`

### 2.2 SonarCloud API Client (api/client.py)

**Purpose**: Handle all API communication with SonarCloud

**Key Methods**:
```python
class SonarCloudClient:
    def __init__(self, token: str, base_url: str):
        self.token = token
        self.base_url = base_url
        self.session = requests.Session()
    
    def _make_request(self, endpoint: str, params: dict) -> dict
    
    def get_issues(self, project_key: str, page: int = 1) -> dict
    
    def get_all_issues(self, project_key: str) -> List[dict]
    
    def get_metrics(self, project_key: str, metric_keys: List[str]) -> dict
    
    def get_project_info(self, project_key: str) -> dict
    
    def get_quality_gate_status(self, project_key: str) -> dict
    
    def get_security_hotspots(self, project_key: str) -> List[dict]
```

**Error Handling**:
- Retry logic with exponential backoff (max 3 retries)
- Handle HTTP errors: 401 (auth), 403 (forbidden), 404 (not found), 429 (rate limit)
- Timeout: 30 seconds per request
- Log all API calls for debugging

**Pagination Strategy**:
```python
def _paginate(self, endpoint: str, params: dict) -> List[dict]:
    """Fetch all pages of results"""
    all_results = []
    page = 1
    while True:
        params['p'] = page
        params['ps'] = 500  # max page size
        response = self._make_request(endpoint, params)
        items = response.get('issues', [])
        all_results.extend(items)
        
        if len(items) < 500:
            break
        page += 1
    
    return all_results
```

### 2.3 Data Models (models/)

#### Issue Model (models/issue.py)
```python
from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional

@dataclass
class Issue:
    key: str
    type: str  # BUG, VULNERABILITY, CODE_SMELL, SECURITY_HOTSPOT
    severity: str  # BLOCKER, CRITICAL, MAJOR, MINOR, INFO
    status: str
    message: str
    component: str
    line: Optional[int]
    creation_date: datetime
    tags: List[str]
    rule: str
    effort: Optional[str]  # Technical debt
    
    @classmethod
    def from_api_response(cls, data: dict) -> 'Issue'
    
    def get_severity_priority(self) -> int:
        """Return numeric priority for sorting"""
        priorities = {
            'BLOCKER': 5,
            'CRITICAL': 4,
            'MAJOR': 3,
            'MINOR': 2,
            'INFO': 1
        }
        return priorities.get(self.severity, 0)
    
    def is_security_issue(self) -> bool:
        return self.type in ['VULNERABILITY', 'SECURITY_HOTSPOT']
```

#### Metric Model (models/metric.py)
```python
@dataclass
class Metric:
    key: str
    value: str
    metric_name: str
    
    @classmethod
    def from_api_response(cls, data: dict) -> 'Metric'
    
    def get_formatted_value(self) -> str:
        """Format value for display (e.g., percentages, time)"""
```

#### Project Info Model (models/project.py)
```python
@dataclass
class ProjectInfo:
    key: str
    name: str
    organization: str
    last_analysis_date: datetime
    quality_gate_status: str
    version: Optional[str]
    
    @classmethod
    def from_api_response(cls, data: dict) -> 'ProjectInfo'
```

#### Report Data Model (models/report_data.py)
```python
@dataclass
class ReportData:
    project_info: ProjectInfo
    issues: List[Issue]
    metrics: List[Metric]
    quality_gate_status: dict
    security_hotspots: List[dict]
    
    def get_issues_by_severity(self) -> dict:
        """Group issues by severity level"""
    
    def get_issues_by_type(self) -> dict:
        """Group issues by type"""
    
    def get_security_summary(self) -> dict:
        """Get security-specific statistics"""
    
    def get_top_issues(self, limit: int = 10) -> List[Issue]:
        """Get top priority issues"""
```

### 2.4 Data Processor (processors/data_processor.py)

**Purpose**: Transform raw API data into structured report data

```python
class DataProcessor:
    def __init__(self, api_client: SonarCloudClient):
        self.api_client = api_client
    
    def fetch_all_data(self, project_key: str) -> ReportData:
        """Fetch and process all data for a project"""
        
    def process_issues(self, raw_issues: List[dict]) -> List[Issue]:
        """Convert API issues to Issue objects"""
    
    def process_metrics(self, raw_metrics: dict) -> List[Metric]:
        """Convert API metrics to Metric objects"""
    
    def calculate_statistics(self, issues: List[Issue]) -> dict:
        """Calculate summary statistics"""
        return {
            'total_issues': len(issues),
            'by_severity': self._count_by_severity(issues),
            'by_type': self._count_by_type(issues),
            'security_issues': len([i for i in issues if i.is_security_issue()]),
            'technical_debt': self._calculate_total_debt(issues)
        }
```

### 2.5 Report Generator (report/generator.py)

**Purpose**: Generate Markdown reports from processed data

```python
class ReportGenerator:
    def __init__(self, template_path: str = None):
        self.template_path = template_path or self._get_default_template()
        self.env = jinja2.Environment(
            loader=jinja2.FileSystemLoader(os.path.dirname(self.template_path))
        )
    
    def generate(self, report_data: ReportData, output_path: str) -> str:
        """Generate report and save to file"""
        
    def _render_template(self, report_data: ReportData) -> str:
        """Render Jinja2 template with data"""
        
    def _format_issue_table(self, issues: List[Issue]) -> str:
        """Format issues as Markdown table"""
        
    def _format_metrics_section(self, metrics: List[Metric]) -> str:
        """Format metrics section"""
```

### 2.6 Markdown Template (report/templates/report.md.j2)

**Template Structure**:
```jinja2
# SAST Report: {{ project_info.name }}

**Generated:** {{ generation_date }}  
**Project Key:** {{ project_info.key }}  
**Organization:** {{ project_info.organization }}  
**Last Analysis:** {{ project_info.last_analysis_date }}

---

## Executive Summary

| Metric | Value |
|--------|-------|
| Quality Gate | {{ quality_gate_status }} |
| Total Issues | {{ statistics.total_issues }} |
| Security Issues | {{ statistics.security_issues }} |
| Blocker Issues | {{ statistics.by_severity.BLOCKER }} |
| Critical Issues | {{ statistics.by_severity.CRITICAL }} |

## Security Overview

### Vulnerabilities by Severity

{% for severity in ['BLOCKER', 'CRITICAL', 'MAJOR'] %}
#### {{ severity }} Severity
{{ vulnerabilities_by_severity[severity]|length }} issue(s)

{% if vulnerabilities_by_severity[severity] %}
| Rule | Message | Location | Line |
|------|---------|----------|------|
{% for issue in vulnerabilities_by_severity[severity][:10] %}
| {{ issue.rule }} | {{ issue.message }} | {{ issue.component }} | {{ issue.line or 'N/A' }} |
{% endfor %}
{% endif %}
{% endfor %}

## Code Quality Metrics

| Metric | Value |
|--------|-------|
{% for metric in metrics %}
| {{ metric.metric_name }} | {{ metric.get_formatted_value() }} |
{% endfor %}

## Detailed Findings

### All Issues by Type

{% for issue_type, issues in issues_by_type.items() %}
#### {{ issue_type }} ({{ issues|length }})
{% endfor %}

---

## Appendix

### Severity Definitions
- **BLOCKER**: Must be fixed immediately
- **CRITICAL**: High priority, fix as soon as possible
- **MAJOR**: Should be fixed
- **MINOR**: Nice to fix
- **INFO**: Informational only

### Report Metadata
- Generated by: SonarCloud SAST Report Generator
- Report Version: 1.0.0
- Data Source: SonarCloud API
```

### 2.7 CLI Interface (cli.py)

**Purpose**: Command-line interface for the tool

```python
import click

@click.group()
def cli():
    """SonarCloud SAST Report Generator"""
    pass

@cli.command()
@click.option('--project-key', required=True, help='SonarCloud project key')
@click.option('--config', type=click.Path(exists=True), help='Config file path')
@click.option('--output', type=click.Path(), help='Output file path')
@click.option('--severity', multiple=True, help='Filter by severity')
@click.option('--include-resolved', is_flag=True, help='Include resolved issues')
@click.option('--verbose', is_flag=True, help='Enable verbose logging')
def generate(project_key, config, output, severity, include_resolved, verbose):
    """Generate SAST report for a project"""
    
@cli.command()
def list_projects():
    """List available projects in organization"""
    
@cli.command()
@click.option('--config', type=click.Path(exists=True))
def validate_config(config):
    """Validate configuration"""

if __name__ == '__main__':
    cli()
```

## Phase 3: Testing Strategy

### 3.1 Unit Tests
- Test each component in isolation
- Mock API responses
- Test error handling
- Test data transformations

### 3.2 Integration Tests
- Test API client with real endpoints (using test project)
- Test end-to-end report generation
- Test configuration loading

### 3.3 Test Coverage Goals
- Minimum 80% code coverage
- 100% coverage for critical paths (API client, data processor)

## Phase 4: Documentation

### 4.1 README.md
- Installation instructions
- Quick start guide
- Configuration options
- Usage examples
- Troubleshooting

### 4.2 API Documentation
- Document all public methods
- Include usage examples
- Document error codes

### 4.3 Example Files
- `config/config.example.yaml`
- `config/.env.example`
- Sample report output

## Implementation Order

1. **Setup** (30 min)
   - Create directory structure
   - Set up requirements.txt
   - Create setup.py
   - Initialize git repository

2. **Configuration** (1 hour)
   - Implement Config class
   - Add environment variable support
   - Add YAML config file support
   - Add validation

3. **API Client** (2 hours)
   - Implement base client with authentication
   - Add endpoint methods
   - Implement pagination
   - Add error handling and retries

4. **Data Models** (1 hour)
   - Create Issue, Metric, ProjectInfo models
   - Add from_api_response methods
   - Add helper methods

5. **Data Processor** (1.5 hours)
   - Implement data fetching
   - Add data transformation logic
   - Calculate statistics

6. **Report Generator** (2 hours)
   - Create Jinja2 template
   - Implement template rendering
   - Add table formatting
   - Test output

7. **CLI Interface** (1 hour)
   - Implement Click commands
   - Add argument parsing
   - Wire up components

8. **Testing** (2 hours)
   - Write unit tests
   - Write integration tests
   - Test with real SonarCloud project

9. **Documentation** (1 hour)
   - Write README
   - Create example configs
   - Add inline documentation

10. **Polish** (30 min)
    - Add logging
    - Improve error messages
    - Final testing

**Total Estimated Time: 12-14 hours**

## Success Metrics

- [ ] Successfully authenticate with SonarCloud API
- [ ] Fetch all required data (issues, metrics, quality gate)
- [ ] Generate well-formatted Markdown report
- [ ] Handle errors gracefully with clear messages
- [ ] Complete report generation in < 30 seconds
- [ ] Easy to configure (< 5 minutes setup)
- [ ] Clear documentation
- [ ] 80%+ test coverage

## Risk Mitigation

### Risk: API Rate Limiting
**Mitigation**: Implement exponential backoff, cache responses during development

### Risk: Large Projects (>10k issues)
**Mitigation**: Implement pagination, add filtering options, limit report to top N issues

### Risk: API Changes
**Mitigation**: Version lock API endpoints, add error handling for unexpected responses

### Risk: Authentication Issues
**Mitigation**: Clear error messages, validate token before making requests

## Next Steps

After completing the implementation:
1. Test with multiple real projects
2. Gather user feedback
3. Add HTML/PDF export options
4. Add trend analysis (compare with previous reports)
5. Create CI/CD integration examples