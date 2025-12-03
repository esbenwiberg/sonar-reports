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
def generate(project_key, config, output, severity, include_resolved, verbose):
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
        
        # Override severity filter if provided
        if severity:
            cfg.severity_filter = [s.upper() for s in severity]
        
        # Override include_resolved if provided
        if include_resolved:
            cfg.include_resolved = True
        
        # Validate configuration
        cfg.validate()
        logger.info(f"Configuration loaded: {cfg}")
        
        # Determine output path
        if not output:
            timestamp = datetime.now().strftime('%Y-%m-%d')
            output = f"{cfg.output_path}/{project_key}_{timestamp}.md"
        
        # Create API client
        logger.info("Connecting to SonarCloud API...")
        with SonarCloudClient(cfg.sonarcloud_token, cfg.base_url, cfg.timeout) as client:
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
            report_data = processor.fetch_all_data(project_key, cfg.include_resolved)
            
            # Generate report
            logger.info("Generating report...")
            generator = ReportGenerator(max_issues_per_section=cfg.max_issues_per_section)
            output_file = generator.generate(report_data, output)
            
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
            click.echo(f"  Critical: {stats['by_severity'].get('CRITICAL', 0)}")
            click.echo(f"  Major: {stats['by_severity'].get('MAJOR', 0)}")
            click.echo(f"  Technical Debt: {stats['technical_debt']}")
            click.echo(f"\nReport saved to: {output_file}")
            click.echo("="*60 + "\n")
    
    except SonarCloudAPIError as e:
        logger.error(f"API Error: {e}")
        click.echo(f"\n✗ Error: {e}\n", err=True)
        sys.exit(1)
    
    except ValueError as e:
        logger.error(f"Configuration Error: {e}")
        click.echo(f"\n✗ Configuration Error: {e}\n", err=True)
        sys.exit(1)
    
    except Exception as e:
        logger.exception("Unexpected error occurred")
        click.echo(f"\n✗ Unexpected Error: {e}\n", err=True)
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
        with SonarCloudClient(cfg.sonarcloud_token, cfg.base_url) as client:
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
def version():
    """Show version information."""
    click.echo("SonarCloud SAST Report Generator v1.0.0")
    click.echo("Generate customer-facing SAST reports from SonarCloud")


if __name__ == '__main__':
    cli()