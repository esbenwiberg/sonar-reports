"""Project information data model."""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass
class ProjectInfo:
    """Represents SonarCloud project information."""
    
    key: str
    name: str
    organization: str
    last_analysis_date: Optional[datetime]
    quality_gate_status: str
    version: Optional[str] = None
    
    @classmethod
    def from_api_response(cls, component_data: dict, qg_data: dict) -> 'ProjectInfo':
        """
        Create a ProjectInfo instance from SonarCloud API responses.
        
        Args:
            component_data: Component data from API
            qg_data: Quality gate data from API
            
        Returns:
            ProjectInfo instance
        """
        # Parse last analysis date
        analysis_date_str = component_data.get('analysisDate', '')
        last_analysis_date = None
        if analysis_date_str:
            try:
                last_analysis_date = datetime.fromisoformat(analysis_date_str.replace('Z', '+00:00'))
            except (ValueError, AttributeError):
                pass
        
        # Get quality gate status
        qg_status = qg_data.get('projectStatus', {}).get('status', 'UNKNOWN')
        
        return cls(
            key=component_data.get('key', ''),
            name=component_data.get('name', ''),
            organization=component_data.get('organization', ''),
            last_analysis_date=last_analysis_date,
            quality_gate_status=qg_status,
            version=component_data.get('version'),
        )
    
    def get_quality_gate_emoji(self) -> str:
        """
        Get emoji representation of quality gate status.
        
        Returns:
            Emoji string
        """
        status_emojis = {
            'OK': '✅',
            'PASSED': '✅',
            'WARN': '⚠️',
            'WARNING': '⚠️',
            'ERROR': '❌',
            'FAILED': '❌',
            'NONE': '❓',
            'UNKNOWN': '❓',
        }
        return status_emojis.get(self.quality_gate_status.upper(), '❓')
    
    def get_formatted_analysis_date(self) -> str:
        """
        Get formatted analysis date.
        
        Returns:
            Formatted date string
        """
        if self.last_analysis_date:
            return self.last_analysis_date.strftime('%Y-%m-%d %H:%M:%S UTC')
        return 'N/A'
    
    def __str__(self) -> str:
        """String representation of project info."""
        return f"{self.name} ({self.key}) - Quality Gate: {self.quality_gate_status}"