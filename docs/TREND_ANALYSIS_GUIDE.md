# Trend Analysis Guide

## Overview

The trend analysis feature allows you to track how your code quality metrics evolve over time by analyzing multiple SAST reports. It generates beautiful, interactive HTML reports with Chart.js graphs.

## Quick Start

### 1. Generate Regular Reports

First, generate regular SAST reports over time:

```bash
# Week 1
python -m sonar_reports generate --project-key my-org_my-project

# Week 2
python -m sonar_reports generate --project-key my-org_my-project

# Week 3
python -m sonar_reports generate --project-key my-org_my-project
```

Each report will include metadata at the bottom for trend analysis.

### 2. Generate Trend Report

Once you have multiple reports, generate a trend analysis:

```bash
python -m sonar_reports trend --reports-dir ./reports
```

This creates an interactive HTML report showing how metrics change over time.

## Command Options

```bash
python -m sonar_reports trend [OPTIONS]
```

### Required Options

- `--reports-dir PATH`: Directory containing report markdown files

### Optional Options

- `--output PATH`: Output path for trend report (default: `./reports/trend-report-YYYY-MM-DD.html`)
- `--project-filter TEXT`: Filter reports by project name or key
- `--verbose`: Enable verbose logging

## Usage Examples

### Example 1: Basic Trend Analysis

```bash
# Analyze all reports in the reports directory
python -m sonar_reports trend --reports-dir ./reports
```

Output: `./reports/trend-report-2025-12-05.html`

### Example 2: Filter by Project

```bash
# Only analyze reports for a specific project
python -m sonar_reports trend \
  --reports-dir ./reports \
  --project-filter "PM.PowerHub"
```

### Example 3: Custom Output Location

```bash
# Save trend report to a specific location
python -m sonar_reports trend \
  --reports-dir ./reports \
  --output ./monthly-trends/december-2025.html
```

### Example 4: Verbose Mode

```bash
# Enable detailed logging
python -m sonar_reports trend \
  --reports-dir ./reports \
  --verbose
```

## What Gets Analyzed

The trend analysis tracks the following metrics over time:

### Issue Metrics
- **Blocker Issues**: Critical issues that must be fixed immediately
- **Critical Issues**: High-priority issues requiring immediate attention
- **Major Issues**: Important issues that should be addressed
- **Minor Issues**: Low-priority issues
- **Info Issues**: Informational findings

### Security Metrics
- **Security Issues**: Total security-related issues
- **Vulnerabilities**: Confirmed security vulnerabilities
- **Security Hotspots**: Security-sensitive code requiring review

### Quality Metrics
- **Code Coverage**: Percentage of code covered by tests
- **Quality Gate Status**: Pass/fail status over time
- **Security Rating**: A-E rating for security
- **Reliability Rating**: A-E rating for reliability
- **Maintainability Rating**: A-E rating for maintainability

## Interactive Features

The generated HTML report includes:

### 1. Tabbed Navigation
- Switch between different metric views
- Issues Trend
- Security Metrics
- Quality Gate History
- Code Coverage
- Quality Ratings

### 2. Interactive Charts
- **Hover tooltips**: See exact values on hover
- **Smooth animations**: Charts animate when loaded
- **Color-coded**: Severity-based colors (red for blocker, orange for critical, etc.)
- **Responsive**: Works on desktop, tablet, and mobile

### 3. Executive Summary
- Overall trend indicator (Improving/Declining/Stable)
- Key metrics with percentage changes
- Quick insights at a glance

### 4. Detailed Analysis
- Trend descriptions for each metric
- Recommendations based on trends
- Complete historical data table

## Understanding the Report

### Overall Trend

The report shows an overall trend based on critical metrics:

- **📈 Improving**: Critical and security issues are decreasing
- **📉 Declining**: Critical or security issues are increasing
- **➡️ Stable**: No significant changes

### Change Indicators

Each metric shows:
- **Current value**: Latest measurement
- **Change percentage**: How much it changed
- **Direction**: ✅ Improving, ⚠️ Declining, or ➡️ Stable

### Quality Gate Chart

The quality gate chart shows pass/fail status over time:
- **Green bars**: Quality gate passed ✅
- **Red bars**: Quality gate failed ❌

All bars are the same height for easy visual comparison.

## Requirements

### Minimum Reports

- Need at least **2 reports** for trend analysis
- More reports = better trend visualization
- Recommended: Weekly or bi-weekly reports

### Report Format

Reports must:
- Be in Markdown format (`.md`)
- Include metadata section (automatically added by generator)
- Be for the same project (when using project filter)

## Troubleshooting

### No Reports Found

```
✗ No reports found in ./reports
```

**Solution**: Ensure the directory contains `.md` report files with metadata.

### Not Enough Reports

```
✗ Need at least 2 reports for trend analysis (found 1)
```

**Solution**: Generate more reports over time before running trend analysis.

### Different Projects

If reports are for different projects, use `--project-filter`:

```bash
python -m sonar_reports trend \
  --reports-dir ./reports \
  --project-filter "my-project"
```

## Best Practices

### 1. Regular Report Generation

Generate reports on a consistent schedule:

```bash
# Weekly cron job
0 9 * * 1 cd /path/to/sonar-reports && python -m sonar_reports generate --project-key my-project
```

### 2. Organize Reports

Keep reports organized by project:

```
reports/
├── project-a/
│   ├── project-a_2025-11-01.md
│   ├── project-a_2025-11-08.md
│   └── project-a_2025-11-15.md
└── project-b/
    ├── project-b_2025-11-01.md
    └── project-b_2025-11-08.md
```

### 3. Archive Old Reports

Keep a reasonable number of reports (e.g., last 12 weeks):

```bash
# Archive reports older than 90 days
find ./reports -name "*.md" -mtime +90 -exec mv {} ./archive/ \;
```

### 4. Share Trend Reports

The HTML reports are self-contained and can be:
- Emailed to stakeholders
- Hosted on internal web servers
- Shared via cloud storage
- Opened directly in any browser

## Advanced Usage

### Automated Trend Reports

Create a script to generate both regular and trend reports:

```bash
#!/bin/bash
# generate-reports.sh

PROJECT_KEY="my-org_my-project"
REPORTS_DIR="./reports"

# Generate current report
echo "Generating SAST report..."
python -m sonar_reports generate --project-key $PROJECT_KEY

# Generate trend report if we have enough reports
REPORT_COUNT=$(ls -1 $REPORTS_DIR/*.md 2>/dev/null | wc -l)
if [ $REPORT_COUNT -ge 2 ]; then
    echo "Generating trend report..."
    python -m sonar_reports trend --reports-dir $REPORTS_DIR
fi
```

### CI/CD Integration

Add to your pipeline:

```yaml
# Azure Pipelines example
- task: Bash@3
  displayName: 'Generate Trend Report'
  inputs:
    targetType: 'inline'
    script: |
      python -m sonar_reports trend \
        --reports-dir $(Build.ArtifactStagingDirectory)/reports \
        --output $(Build.ArtifactStagingDirectory)/trend-report.html

- task: PublishBuildArtifacts@1
  displayName: 'Publish Trend Report'
  inputs:
    PathtoPublish: '$(Build.ArtifactStagingDirectory)/trend-report.html'
    ArtifactName: 'trend-report'
```

## Sample Output

See [`docs/sample-trend-report.html`](sample-trend-report.html) for a complete example of what the trend report looks like.

## Technical Details

### Metadata Format

Each report includes a YAML metadata block at the end with all key metrics for trend analysis.

### Data Processing

1. **Parser**: Extracts metadata from each report
2. **Aggregator**: Combines data and sorts by date
3. **Generator**: Creates HTML with Chart.js visualizations

### Chart Library

Uses [Chart.js 4.4.0](https://www.chartjs.org/) for interactive graphs:
- Line charts for trends
- Bar charts for quality gate
- Radar charts for ratings
- Stacked area charts for security metrics

## Support

For issues or questions:
- Check the [main README](../README.md)
- Review [sample reports](SAMPLE_TREND_REPORT.md)
- Open an issue on GitHub

---

**Happy trend tracking! 📈**