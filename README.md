# SonarCloud SAST Report Generator

A Python-based tool to generate customer-facing SAST (Static Application Security Testing) reports from SonarCloud API data. Since SonarCloud doesn't provide built-in report generation, this tool fills that gap by creating professional, comprehensive Markdown reports suitable for sharing with customers.

## Features

- 🔒 **Security-Focused**: Highlights vulnerabilities, security hotspots, and OWASP Top 10 coverage
- 📊 **Comprehensive Metrics**: Includes code quality, coverage, technical debt, and maintainability ratings
- 📝 **Customer-Ready**: Professional formatting suitable for external stakeholders
- 🚀 **Easy to Use**: Simple CLI interface with minimal configuration
- 🔧 **Flexible**: Configurable via environment variables, config files, or command-line arguments
- 📈 **Actionable**: Provides prioritized recommendations and remediation guidance

## Quick Start

### Prerequisites

- Python 3.8 or higher
- SonarCloud account with API access
- SonarCloud API token ([Generate one here](https://sonarcloud.io/account/security))

### Installation

```bash
# Clone the repository
git clone https://github.com/esbenwiberg/sonar-reports.git
cd sonar-reports

# Install dependencies
pip install -r requirements.txt

# Or install in development mode
pip install -e .
```

### Basic Usage

1. **Set up your API token** (choose one method):

   ```bash
   # Option 1: Environment variable
   export SONARCLOUD_TOKEN="your-api-token-here"
   
   # Option 2: Create a .env file
   echo "SONARCLOUD_TOKEN=your-api-token-here" > .env
   
   # Option 3: Use a config file (see config/config.example.yaml)
   cp config/config.example.yaml config/config.yaml
   # Edit config.yaml with your settings
   ```

2. **Generate a report**:

   ```bash
   # Basic usage
   python -m sonar_reports generate --project-key your-project-key
   
   # With custom output path
   python -m sonar_reports generate --project-key your-project-key --output ./reports/my-report.md
   
   # With config file
   python -m sonar_reports generate --project-key your-project-key --config config/config.yaml
   
   # Filter by severity
   python -m sonar_reports generate --project-key your-project-key --severity BLOCKER --severity CRITICAL
   ```

3. **View your report**:

   ```bash
   # Reports are saved to ./reports/ by default
   cat reports/your-project-key_2025-12-03.md
   ```

## Configuration

### Environment Variables

```bash
SONARCLOUD_TOKEN=your-api-token          # Required: Your SonarCloud API token
SONARCLOUD_ORGANIZATION=your-org         # Optional: Your organization key
SONARCLOUD_PROJECT_KEY=your-project      # Optional: Default project key
SONARCLOUD_BASE_URL=https://sonarcloud.io  # Optional: API base URL
```

### Config File (YAML)

Create a `config.yaml` file:

```yaml
sonarcloud:
  token: "your-api-token"
  organization: "your-organization"
  project_key: "your-project-key"
  base_url: "https://sonarcloud.io"

report:
  output_path: "./reports"
  include_resolved: false
  severity_filter:
    - BLOCKER
    - CRITICAL
    - MAJOR
  max_issues_per_section: 10
```

### Command-Line Options

```bash
Options:
  --project-key TEXT       SonarCloud project key (required)
  --config PATH           Path to config file
  --output PATH           Output file path
  --severity TEXT         Filter by severity (can be used multiple times)
  --include-resolved      Include resolved issues
  --verbose              Enable verbose logging
  --help                 Show this message and exit
```

## Report Contents

The generated report includes:

### 1. Executive Summary
- Quality gate status
- Total issues by severity
- Security issues count
- Technical debt estimation

### 2. Security Overview
- Critical vulnerabilities with details
- Security hotspots requiring review
- OWASP Top 10 coverage analysis
- CWE (Common Weakness Enumeration) references

### 3. Code Quality Metrics
- Lines of code
- Code coverage percentage
- Code duplication
- Technical debt
- Maintainability, reliability, and security ratings

### 4. Detailed Findings
- Bugs by severity
- Vulnerabilities with locations
- Code smells (top issues)
- File and line number references

### 5. Recommendations
- Prioritized action items
- Remediation guidance
- Effort estimates

### 6. Compliance Information
- Security standards compliance
- Industry best practices alignment

## Examples

### Example 1: Generate Report for a Single Project

```bash
python -m sonar_reports generate \
  --project-key my-org_my-project \
  --output reports/weekly-report.md
```

### Example 2: Generate Report with Severity Filter

```bash
# Only show BLOCKER and CRITICAL issues
python -m sonar_reports generate \
  --project-key my-org_my-project \
  --severity BLOCKER \
  --severity CRITICAL
```

### Example 3: Using Config File

```bash
# Create config file
cat > config/my-config.yaml << EOF
sonarcloud:
  token: "${SONARCLOUD_TOKEN}"
  organization: "my-org"
  project_key: "my-project"

report:
  output_path: "./customer-reports"
  severity_filter: ["BLOCKER", "CRITICAL", "MAJOR"]
EOF

# Generate report
python -m sonar_reports generate --config config/my-config.yaml
```

### Example 4: Batch Processing Multiple Projects

```bash
#!/bin/bash
# generate-all-reports.sh

PROJECTS=(
  "my-org_project-1"
  "my-org_project-2"
  "my-org_project-3"
)

for project in "${PROJECTS[@]}"; do
  echo "Generating report for $project..."
  python -m sonar_reports generate \
    --project-key "$project" \
    --output "reports/${project}_$(date +%Y-%m-%d).md"
done
```

## Sample Output

See [`docs/SAMPLE_REPORT.md`](docs/SAMPLE_REPORT.md) for an example of what the generated report looks like.

## Documentation

For detailed information, see the [`docs/`](docs/) folder:
- [`docs/QUICKSTART.md`](docs/QUICKSTART.md) - Quick start guide
- [`docs/INSTALLATION.md`](docs/INSTALLATION.md) - Detailed installation instructions
- [`docs/HOW_TO_RUN.md`](docs/HOW_TO_RUN.md) - Usage examples and guides
- [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) - System design and component overview
- [`docs/AZURE_DEVOPS_INTEGRATION.md`](docs/AZURE_DEVOPS_INTEGRATION.md) - Azure DevOps integration guide
- [`docs/SAMPLE_REPORT.md`](docs/SAMPLE_REPORT.md) - Example report output

## Development

### Setup Development Environment

```bash
# Clone repository
git clone https://github.com/esbenwiberg/sonar-reports.git
cd sonar-reports

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install development dependencies
pip install -r requirements-dev.txt

# Install pre-commit hooks
pre-commit install
```

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=sonar_reports --cov-report=html

# Run specific test file
pytest tests/test_api.py

# Run with verbose output
pytest -v
```

### Code Quality

```bash
# Format code
black src/

# Type checking
mypy src/

# Linting
pylint src/

# Run all checks
./scripts/check-quality.sh
```

## Troubleshooting

### Issue: Authentication Failed

```
Error: 401 Unauthorized - Invalid or expired token
```

**Solution**: Verify your API token is correct and has not expired. Generate a new token at https://sonarcloud.io/account/security

### Issue: Project Not Found

```
Error: 404 Not Found - Project 'my-project' does not exist
```

**Solution**: 
- Verify the project key is correct (format: `organization_project-name`)
- Ensure you have access to the project in SonarCloud
- Check that the organization is correct

### Issue: Rate Limit Exceeded

```
Error: 429 Too Many Requests - Rate limit exceeded
```

**Solution**: The tool implements automatic retry with exponential backoff. If you continue to see this error, wait a few minutes before retrying.

### Issue: Large Projects Timeout

```
Error: Request timeout after 30 seconds
```

**Solution**: 
- Use severity filters to reduce the amount of data fetched
- Increase timeout in config file
- Consider generating reports for specific components

## API Rate Limits

SonarCloud API has the following rate limits:
- **Authenticated requests**: 10,000 requests per day
- **Burst limit**: 100 requests per minute

The tool implements:
- Automatic retry with exponential backoff
- Request batching where possible
- Efficient pagination

## License

MIT License - see [LICENSE](LICENSE) file for details

## Support

- 🐛 Issues: [GitHub Issues](https://github.com/esbenwiberg/sonar-reports/issues)
- 💬 Discussions: [GitHub Discussions](https://github.com/esbenwiberg/sonar-reports/discussions)
- 📖 Documentation: [Wiki](https://github.com/esbenwiberg/sonar-reports/wiki)

## Acknowledgments

- Built with [SonarCloud API](https://sonarcloud.io/web_api)

---

**Made with ❤️ for better security reporting**