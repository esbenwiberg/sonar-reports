# Quick Start Guide

Get started with the SonarCloud SAST Report Generator in 5 minutes!

## Prerequisites

- Python 3.8 or higher
- SonarCloud account with API access
- A SonarCloud project to analyze

## Installation

```bash
# Clone or navigate to the repository
cd sonar-reports

# Install dependencies
pip install -r requirements.txt

# Or install in development mode
pip install -e .
```

## Configuration

### Option 1: Environment Variables (Recommended for Quick Start)

```bash
# Set your SonarCloud API token
export SONARCLOUD_TOKEN="your-api-token-here"

# Optional: Set default organization
export SONARCLOUD_ORGANIZATION="your-org"
```

Get your API token at: https://sonarcloud.io/account/security

### Option 2: Configuration File

```bash
# Copy example config
cp config/config.example.yaml config/config.yaml

# Edit with your values
nano config/config.yaml
```

## Generate Your First Report

```bash
# Basic usage (using environment variables)
python -m sonar_reports generate --project-key your-org_your-project

# Using config file
python -m sonar_reports generate --project-key your-org_your-project --config config/config.yaml

# With custom output path
python -m sonar_reports generate --project-key your-org_your-project --output ./my-report.md

# Filter by severity
python -m sonar_reports generate --project-key your-org_your-project --severity BLOCKER --severity CRITICAL
```

## Verify Installation

```bash
# Check version
python -m sonar_reports version

# Validate configuration
python -m sonar_reports validate-config
```

## Example Output

Your report will be saved to `./reports/your-project-key_YYYY-MM-DD.md` by default.

The report includes:
- ✅ Executive summary with quality gate status
- 🔒 Security vulnerabilities and hotspots
- 📊 Code quality metrics
- 📝 Detailed findings by type and severity
- 💡 Prioritized recommendations
- 📋 Compliance information

## Common Issues

### Authentication Error

```
Error: 401 Unauthorized - Invalid or expired token
```

**Solution**: Verify your API token is correct and hasn't expired. Generate a new one at https://sonarcloud.io/account/security

### Project Not Found

```
Error: 404 Not Found - Project 'my-project' does not exist
```

**Solution**: 
- Check the project key format: `organization_project-name`
- Verify you have access to the project in SonarCloud
- Ensure the organization is correct

### Missing Token

```
Configuration Error: SonarCloud token is required
```

**Solution**: Set the `SONARCLOUD_TOKEN` environment variable or add it to your config file.

## Next Steps

1. Review the generated report
2. Share with your team or customers
3. Set up automated report generation in CI/CD
4. Customize the report template if needed

For more details, see the full [README.md](README.md) and [ARCHITECTURE.md](ARCHITECTURE.md).

## Getting Help

- 📖 Full documentation: [README.md](README.md)
- 🏗️ Architecture details: [ARCHITECTURE.md](ARCHITECTURE.md)
- 📋 Implementation guide: [IMPLEMENTATION_PLAN.md](IMPLEMENTATION_PLAN.md)
- 📊 Sample report: [SAMPLE_REPORT.md](SAMPLE_REPORT.md)

## Example: Complete Workflow

```bash
# 1. Set up environment
export SONARCLOUD_TOKEN="squ_abc123..."

# 2. Validate configuration
python -m sonar_reports validate-config

# 3. Generate report
python -m sonar_reports generate --project-key my-org_my-project

# 4. View the report
cat reports/my-org_my-project_2025-12-03.md
```

That's it! You're ready to generate professional SAST reports from SonarCloud. 🎉