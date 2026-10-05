"""Command-line interface for SonarCloud SAST Report Generator."""

import sys
import logging
from pathlib import Path
from datetime import datetime
import click

from .config import Config
from .api.client import SonarCloudClient, SonarCloudAPIError
from .processors import DataProcessor
from .report import ReportGenerator
from .report.json_export import build_payload, write_json
from .report.html_report import HtmlReportRenderer, html_to_pdf, find_chrome, PayloadError, AUDIENCES


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@click.group()
@click.version_option(version='1.0.0')
def cli():
    """SonarCloud SAST Report Generator
    
    Generate customer-facing SAST reports from SonarCloud API data.
    """
    pass


@cli.command()
@click.option(
    '--project-key',
    required=True,
    help='SonarCloud project key (format: organization_project-name)'
)
@click.option(
    '--organization',
    default=None,
    help='SonarCloud organization key (required when using an organization token). '
         'Falls back to SONARCLOUD_ORGANIZATION or the config file.'
)
@click.option(
    '--config',
    type=click.Path(exists=True),
    help='Path to YAML configuration file'
)
@click.option(
    '--output',
    type=click.Path(),
    help='Output file path (default: ./reports/PROJECT_KEY_DATE.md)'
)
@click.option(
    '--json-output',
    type=click.Path(),
    help='Also write machine-readable JSON to this path (for the portfolio HTML builder)'
)
@click.option(
    '--severity',
    multiple=True,
    type=click.Choice(['BLOCKER', 'CRITICAL', 'MAJOR', 'MINOR', 'INFO'], case_sensitive=False),
    help='Filter by severity (can be used multiple times)'
)
@click.option(
    '--include-resolved',
    is_flag=True,
    help='Include resolved issues in the report'
)
@click.option(
    '--verbose',
    is_flag=True,
    help='Enable verbose logging'
)
def generate(project_key, organization, config, output, json_output, severity, include_resolved, verbose):
    """Generate SAST report for a project.
    
    Example:
        sonar-report generate --project-key my-org_my-project
    """
    # Set logging level
    if verbose:
        logging.getLogger().setLevel(logging.DEBUG)
        logger.debug("Verbose logging enabled")
    
    try:
        # Load configuration
        logger.info("Loading configuration...")
        if config:
            cfg = Config.from_file(config, project_key=project_key)
        else:
            cfg = Config.from_env(project_key=project_key)
        
        # Explicit --organization wins over env var / config file
        if organization:
            cfg.organization = organization

        # Override severity filter if provided
        if severity:
            cfg.severity_filter = [s.upper() for s in severity]
        
        # Override include_resolved if provided
        if include_resolved:
            cfg.include_resolved = True
        
        # Validate configuration
        try:
            cfg.validate()
        except ValueError as e:
            logger.error(f"Configuration Error: {e}")
            click.echo(f"\n✗ Configuration Error: {e}\n", err=True)
            sys.exit(1)
        logger.info(f"Configuration loaded: {cfg}")
        
        # Determine output path
        if not output:
            timestamp = datetime.now().strftime('%Y-%m-%d')
            output = f"{cfg.output_path}/{project_key}_{timestamp}.md"
        
        # Create API client
        logger.info("Connecting to SonarCloud API...")
        with SonarCloudClient(cfg.sonarcloud_token, cfg.base_url, cfg.timeout,
                              organization=cfg.organization) as client:
            # Validate connection
            try:
                client.validate_connection()
                logger.info("✓ Successfully connected to SonarCloud API")
            except SonarCloudAPIError as e:
                logger.error(f"✗ Failed to connect to SonarCloud API: {e}")
                sys.exit(1)
            
            # Fetch and process data
            logger.info(f"Fetching data for project: {project_key}")
            processor = DataProcessor(client)
            report_data = processor.fetch_all_data(project_key, cfg.include_resolved, cfg.severity_filter)
            
            # Generate report
            logger.info("Generating report...")
            generator = ReportGenerator(max_issues_per_section=cfg.max_issues_per_section)
            output_file = generator.generate(report_data, output)

            if json_output:
                try:
                    Path(json_output).parent.mkdir(parents=True, exist_ok=True)
                    write_json(json_output, build_payload(
                        report_data,
                        severity_filter=cfg.severity_filter,
                        base_url=cfg.base_url,
                        include_resolved=cfg.include_resolved,
                    ))
                except Exception as e:
                    # A sidecar failure must not invalidate a good report.
                    logger.warning(f"Could not write JSON output to {json_output}: {e}")
            
            # Display summary
            stats = report_data.calculate_statistics()
            click.echo("\n" + "="*60)
            click.echo("✓ Report generated successfully!")
            click.echo("="*60)
            click.echo(f"\nProject: {report_data.project_info.name}")
            click.echo(f"Quality Gate: {report_data.project_info.quality_gate_status} {report_data.project_info.get_quality_gate_emoji()}")
            click.echo(f"\nIssues Summary:")
            click.echo(f"  Total Issues: {stats['total_issues']}")
            click.echo(f"  Security Issues: {stats['security_issues']}")
            click.echo(f"  Blocker: {stats['by_severity'].get('BLOCKER', 0)}")
            click.echo(f"  High: {stats['by_severity'].get('CRITICAL', 0)}")
            click.echo(f"  Medium: {stats['by_severity'].get('MAJOR', 0)}")
            click.echo(f"  Minor: {stats['by_severity'].get('MINOR', 0)}")
            click.echo(f"  Info: {stats['by_severity'].get('INFO', 0)}")
            click.echo(f"  Technical Debt: {stats['technical_debt']}")
            click.echo(f"\nReport saved to: {output_file}")
            click.echo("="*60 + "\n")
    
    except SonarCloudAPIError as e:
        logger.error(f"API Error: {e}")
        click.echo(f"\n✗ Error: {e}\n", err=True)
        sys.exit(1)
    
    except Exception as e:
        logger.exception("Unexpected error occurred")
        click.echo(f"\n✗ Unexpected Error: {type(e).__name__}: {e}\n", err=True)
        sys.exit(1)


@cli.command()
@click.option(
    '--config',
    type=click.Path(exists=True),
    help='Path to YAML configuration file'
)
def validate_config(config):
    """Validate configuration file or environment variables.
    
    Example:
        sonar-report validate-config --config config.yaml
    """
    try:
        if config:
            cfg = Config.from_file(config)
            click.echo(f"✓ Configuration file is valid: {config}")
        else:
            cfg = Config.from_env()
            click.echo("✓ Environment configuration is valid")
        
        cfg.validate()
        
        click.echo(f"\nConfiguration Details:")
        click.echo(f"  Organization: {cfg.organization or 'Not set'}")
        click.echo(f"  Project Key: {cfg.project_key or 'Not set'}")
        click.echo(f"  Base URL: {cfg.base_url}")
        click.echo(f"  Output Path: {cfg.output_path}")
        click.echo(f"  Severity Filter: {', '.join(cfg.severity_filter)}")
        click.echo(f"  Include Resolved: {cfg.include_resolved}")
        
        # Test API connection
        click.echo("\nTesting API connection...")
        with SonarCloudClient(cfg.sonarcloud_token, cfg.base_url,
                              organization=cfg.organization) as client:
            client.validate_connection()
            click.echo("✓ Successfully connected to SonarCloud API\n")
    
    except ValueError as e:
        click.echo(f"\n✗ Configuration Error: {e}\n", err=True)
        sys.exit(1)
    
    except SonarCloudAPIError as e:
        click.echo(f"\n✗ API Connection Error: {e}\n", err=True)
        sys.exit(1)
    
    except Exception as e:
        click.echo(f"\n✗ Error: {e}\n", err=True)
        sys.exit(1)


@cli.command()
@click.option(
    '--reports-dir',
    required=True,
    type=click.Path(exists=True),
    help='Directory containing report markdown files'
)
@click.option(
    '--output',
    type=click.Path(),
    help='Output path for trend report (default: ./reports/trend-report.html)'
)
@click.option(
    '--project-filter',
    help='Filter reports by project name or key'
)
@click.option(
    '--verbose',
    is_flag=True,
    help='Enable verbose logging'
)
def trend(reports_dir, output, project_filter, verbose):
    """Generate trend analysis from multiple report files.
    
    Analyzes multiple SAST reports and generates an interactive HTML
    trend report showing how metrics change over time.
    
    Example:
        sonar-report trend --reports-dir ./reports
        sonar-report trend --reports-dir ./reports --project-filter "PM.PowerHub"
    """
    if verbose:
        logging.getLogger().setLevel(logging.DEBUG)
        logger.debug("Verbose logging enabled")
    
    try:
        from .trend import ReportParser, TrendDataAggregator, HTMLTrendReportGenerator
        
        if not output:
            timestamp = datetime.now().strftime('%Y-%m-%d')
            output = f"./reports/trend-report-{timestamp}.html"
        
        logger.info(f"Parsing reports from {reports_dir}")
        parser = ReportParser()
        reports = parser.parse_directory(reports_dir, project_filter)
        
        if not reports:
            click.echo(f"\n✗ No reports found in {reports_dir}", err=True)
            if project_filter:
                click.echo(f"   (with filter: {project_filter})", err=True)
            sys.exit(1)
        
        if len(reports) < 2:
            click.echo(f"\n✗ Need at least 2 reports for trend analysis (found {len(reports)})", err=True)
            sys.exit(1)
        
        logger.info(f"Found {len(reports)} reports")
        click.echo(f"\n📊 Analyzing {len(reports)} reports...")
        
        aggregator = TrendDataAggregator()
        trend_data = aggregator.aggregate_reports(reports)
        
        click.echo(f"📈 Generating HTML trend report...")
        generator = HTMLTrendReportGenerator()
        output_file = generator.generate(trend_data, output)
        
        summary = trend_data.calculate_summary_stats()
        
        click.echo("\n" + "="*60)
        click.echo("✓ Trend report generated successfully!")
        click.echo("="*60)
        click.echo(f"\nProject: {trend_data.project_name}")
        click.echo(f"Analysis Period: {trend_data.get_date_range_str()}")
        click.echo(f"Reports Analyzed: {trend_data.get_report_count()}")
        click.echo(f"\nOverall Trend: {summary['overall_trend'].upper()}")
        click.echo(f"Quality Gate Pass Rate: {summary['quality_gate_pass_rate']:.0f}%")
        click.echo(f"\nReport saved to: {output_file}")
        click.echo("="*60 + "\n")
    
    except ImportError as e:
        logger.error(f"Import Error: {e}")
        click.echo(f"\n✗ Error: Missing dependencies for trend analysis\n", err=True)
        sys.exit(1)
    
    except ValueError as e:
        logger.error(f"Value Error: {e}")
        click.echo(f"\n✗ Error: {e}\n", err=True)
        sys.exit(1)
    
    except Exception as e:
        logger.exception("Unexpected error occurred")
        click.echo(f"\n✗ Unexpected Error: {e}\n", err=True)
        sys.exit(1)


@cli.command()
@click.argument('json_files', nargs=-1, required=True, type=click.Path(exists=True, dir_okay=False))
@click.option(
    '--output-dir',
    type=click.Path(file_okay=False),
    help='Directory for the HTML/PDF files (default: next to each JSON file)'
)
@click.option(
    '--pdf',
    is_flag=True,
    help='Also print each HTML report to PDF using a locally installed Chrome/Chromium'
)
@click.option(
    '--max-rows',
    default=25,
    show_default=True,
    help='Maximum rows per findings table'
)
@click.option(
    '--audience',
    type=click.Choice(AUDIENCES),
    default='customer',
    show_default=True,
    help='customer: security and reliability only. internal: adds maintainability, '
         'size/coverage/duplication metrics and recommendations.'
)
@click.option(
    '--verbose',
    is_flag=True,
    help='Enable verbose logging'
)
def render(json_files, output_dir, pdf, max_rows, audience, verbose):
    """Render JSON report payload(s) to a self-contained HTML document, optionally PDF.

    Takes the JSON written by `generate --json-output`, so rendering never
    re-queries SonarCloud and can be repeated offline.

    Example:
        sonar-report render reports/*.json --pdf
        sonar-report render reports/*.json --audience internal
    """
    import json as _json

    if verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    if pdf and not find_chrome():
        click.echo("\n✗ --pdf requested but no Chrome/Chromium was found. "
                   "Install Google Chrome or set SONAR_REPORT_CHROME to the browser binary.\n", err=True)
        sys.exit(1)

    renderer = HtmlReportRenderer(max_rows=max_rows, audience=audience)
    failures = 0
    for jf in json_files:
        src = Path(jf)
        out_dir = Path(output_dir) if output_dir else src.parent
        html_path = out_dir / (src.stem + '.html')
        try:
            with open(src, encoding='utf-8') as fh:
                payload = _json.load(fh)
            renderer.render_to_file(payload, str(html_path))
            line = f"✓ {src.name} → {html_path}"
            if pdf:
                pdf_path = out_dir / (src.stem + '.pdf')
                html_to_pdf(str(html_path), str(pdf_path))
                line += f", {pdf_path.name}"
            click.echo(line)
        except (PayloadError, _json.JSONDecodeError) as e:
            failures += 1
            click.echo(f"✗ {src.name}: invalid payload: {e}", err=True)
        except RuntimeError as e:
            failures += 1
            click.echo(f"✗ {src.name}: {e}", err=True)

    if failures:
        click.echo(f"\n{failures} of {len(json_files)} file(s) failed.", err=True)
        sys.exit(1)


@cli.command()
def version():
    """Show version information."""
    click.echo("SonarCloud SAST Report Generator v1.0.0")
    click.echo("Generate customer-facing SAST reports from SonarCloud")


if __name__ == '__main__':
    cli()