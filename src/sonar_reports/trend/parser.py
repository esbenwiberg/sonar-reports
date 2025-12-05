"""Parser for extracting metadata from markdown report files."""

import re
import logging
from pathlib import Path
from typing import Optional, List
from datetime import datetime
import yaml

from .models import ReportMetadata


logger = logging.getLogger(__name__)


class ReportParser:
    """Parse metadata from markdown report files."""
    
    METADATA_MARKER = "# REPORT_METADATA"
    
    def parse_report(self, file_path: str) -> Optional[ReportMetadata]:
        """
        Extract metadata from a report file.
        
        Args:
            file_path: Path to the markdown report file
            
        Returns:
            ReportMetadata instance or None if parsing fails
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            metadata_dict = self.extract_metadata_block(content)
            if not metadata_dict:
                logger.warning(f"No metadata found in {file_path}")
                return None
            
            if not self.validate_metadata(metadata_dict):
                logger.warning(f"Invalid metadata structure in {file_path}")
                return None
            
            return self._create_metadata_object(metadata_dict, file_path)
            
        except Exception as e:
            logger.error(f"Error parsing report {file_path}: {e}")
            return None
    
    def extract_metadata_block(self, content: str) -> Optional[dict]:
        """
        Find and parse the YAML metadata block.
        
        Args:
            content: Full content of the markdown file
            
        Returns:
            Dictionary with metadata or None if not found
        """
        # Look for the metadata marker
        if self.METADATA_MARKER not in content:
            logger.debug(f"Metadata marker '{self.METADATA_MARKER}' not found in content")
            return None
        
        # Extract the YAML block between ```yaml and ```
        pattern = r'```yaml\s*\n# REPORT_METADATA\s*\n(.*?)```'
        match = re.search(pattern, content, re.DOTALL)
        
        if not match:
            logger.debug("Regex pattern did not match YAML block")
            # Try alternative pattern without strict whitespace
            pattern2 = r'```yaml.*?# REPORT_METADATA.*?\n(.*?)```'
            match = re.search(pattern2, content, re.DOTALL)
            if not match:
                logger.debug("Alternative regex pattern also failed")
                return None
        
        yaml_content = match.group(1).strip()
        logger.debug(f"Extracted YAML content length: {len(yaml_content)} characters")
        
        try:
            metadata = yaml.safe_load(yaml_content)
            logger.debug(f"Successfully parsed YAML metadata with keys: {list(metadata.keys()) if metadata else 'None'}")
            return metadata
        except yaml.YAMLError as e:
            logger.error(f"Error parsing YAML metadata: {e}")
            logger.debug(f"YAML content that failed: {yaml_content[:200]}")
            return None
    
    def validate_metadata(self, metadata: dict) -> bool:
        """
        Validate metadata structure.
        
        Args:
            metadata: Dictionary with metadata
            
        Returns:
            True if valid, False otherwise
        """
        required_fields = [
            'report_version',
            'generated_date',
            'analysis_date',
            'project',
            'quality_gate',
            'metrics',
            'categories'
        ]
        
        for field in required_fields:
            if field not in metadata:
                logger.warning(f"Missing required field: {field}")
                return False
        
        # Validate nested structures
        if 'key' not in metadata.get('project', {}):
            logger.warning("Missing project.key")
            return False
        
        if 'status' not in metadata.get('quality_gate', {}):
            logger.warning("Missing quality_gate.status")
            return False
        
        return True
    
    def _create_metadata_object(self, metadata: dict, file_path: str) -> ReportMetadata:
        """
        Create ReportMetadata object from dictionary.
        
        Args:
            metadata: Dictionary with metadata
            file_path: Path to the report file
            
        Returns:
            ReportMetadata instance
        """
        project = metadata.get('project', {})
        quality_gate = metadata.get('quality_gate', {})
        metrics = metadata.get('metrics', {})
        categories = metadata.get('categories', {})
        
        # Parse dates
        generated_date = self._parse_date(metadata.get('generated_date', ''))
        analysis_date = self._parse_date(metadata.get('analysis_date', ''))
        
        # Parse coverage (remove % if present)
        coverage_str = str(metrics.get('code_coverage', '0'))
        coverage = float(coverage_str.replace('%', '').strip() or 0)
        
        return ReportMetadata(
            report_version=metadata.get('report_version', '1.0'),
            generated_date=generated_date,
            analysis_date=analysis_date,
            file_path=file_path,
            project_key=project.get('key', ''),
            project_name=project.get('name', ''),
            organization=project.get('organization', ''),
            quality_gate_status=quality_gate.get('status', 'UNKNOWN'),
            quality_gate_passed=quality_gate.get('passed', False),
            total_issues=metrics.get('total_issues', 0),
            blocker_issues=metrics.get('blocker_issues', 0),
            critical_issues=metrics.get('critical_issues', 0),
            major_issues=metrics.get('major_issues', 0),
            minor_issues=metrics.get('minor_issues', 0),
            info_issues=metrics.get('info_issues', 0),
            security_issues=metrics.get('security_issues', 0),
            reliability_issues=metrics.get('reliability_issues', 0),
            maintainability_issues=metrics.get('maintainability_issues', 0),
            vulnerabilities=metrics.get('vulnerabilities', 0),
            bugs=metrics.get('bugs', 0),
            code_smells=metrics.get('code_smells', 0),
            security_hotspots=metrics.get('security_hotspots', 0),
            code_coverage=coverage,
            reliability_rating=metrics.get('reliability_rating', 'N/A'),
            security_rating=metrics.get('security_rating', 'N/A'),
            maintainability_rating=metrics.get('maintainability_rating', 'N/A'),
            security_by_severity=categories.get('security', {}),
            reliability_by_severity=categories.get('reliability', {}),
            maintainability_by_severity=categories.get('maintainability', {}),
        )
    
    def _parse_date(self, date_str: str) -> datetime:
        """
        Parse date string to datetime object.
        
        Args:
            date_str: Date string in ISO format
            
        Returns:
            datetime object
        """
        if not date_str:
            return datetime.now()
        
        try:
            # Try ISO format with Z
            if date_str.endswith('Z'):
                return datetime.fromisoformat(date_str[:-1])
            return datetime.fromisoformat(date_str)
        except ValueError:
            logger.warning(f"Could not parse date: {date_str}")
            return datetime.now()
    
    def parse_directory(self, directory: str, project_filter: Optional[str] = None) -> List[ReportMetadata]:
        """
        Parse all markdown files in a directory.
        
        Args:
            directory: Path to directory containing report files
            project_filter: Optional project key/name filter
            
        Returns:
            List of ReportMetadata objects
        """
        reports = []
        dir_path = Path(directory)
        
        if not dir_path.exists():
            logger.error(f"Directory not found: {directory}")
            return reports
        
        # Find all .md files
        md_files = list(dir_path.glob('*.md'))
        logger.info(f"Found {len(md_files)} markdown files in {directory}")
        
        for md_file in md_files:
            metadata = self.parse_report(str(md_file))
            if metadata:
                # Apply project filter if specified
                if project_filter:
                    if project_filter.lower() in metadata.project_key.lower() or \
                       project_filter.lower() in metadata.project_name.lower():
                        reports.append(metadata)
                else:
                    reports.append(metadata)
        
        # Sort by analysis date
        reports.sort(key=lambda x: x.analysis_date)
        
        logger.info(f"Successfully parsed {len(reports)} reports")
        return reports