"""Issue data model for SonarCloud issues."""

from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional


@dataclass
class Issue:
    """Represents a SonarCloud issue (bug, vulnerability, or code smell)."""
    
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
    effort: Optional[str]  # Technical debt (e.g., "2h", "1d")
    author: Optional[str] = None
    
    @classmethod
    def from_api_response(cls, data: dict) -> 'Issue':
        """
        Create an Issue instance from SonarCloud API response.
        
        Args:
            data: Dictionary from SonarCloud API
            
        Returns:
            Issue instance
        """
        # Parse creation date
        creation_date_str = data.get('creationDate', '')
        try:
            creation_date = datetime.fromisoformat(creation_date_str.replace('Z', '+00:00'))
        except (ValueError, AttributeError):
            creation_date = datetime.now()
        
        return cls(
            key=data.get('key', ''),
            type=data.get('type', 'CODE_SMELL'),
            severity=data.get('severity', 'INFO'),
            status=data.get('status', 'OPEN'),
            message=data.get('message', ''),
            component=data.get('component', ''),
            line=data.get('line'),
            creation_date=creation_date,
            tags=data.get('tags', []),
            rule=data.get('rule', ''),
            effort=data.get('effort'),
            author=data.get('author'),
        )
    
    def get_severity_priority(self) -> int:
        """
        Get numeric priority for sorting by severity.
        
        Returns:
            Integer priority (higher = more severe)
        """
        priorities = {
            'BLOCKER': 5,
            'CRITICAL': 4,
            'MAJOR': 3,
            'MINOR': 2,
            'INFO': 1
        }
        return priorities.get(self.severity, 0)
    
    def is_security_issue(self) -> bool:
        """
        Check if this is a security-related issue.
        
        Returns:
            True if issue is a vulnerability or security hotspot
        """
        return self.type in ['VULNERABILITY', 'SECURITY_HOTSPOT']
    
    def get_component_name(self) -> str:
        """
        Get simplified component name (filename).
        
        Returns:
            Component name without project prefix
        """
        # Remove project key prefix if present
        parts = self.component.split(':')
        if len(parts) > 1:
            return parts[-1]
        return self.component
    
    def get_effort_minutes(self) -> int:
        """
        Convert effort string to minutes.
        
        Returns:
            Effort in minutes, or 0 if not available
        """
        if not self.effort:
            return 0
        
        effort = self.effort.lower()
        minutes = 0
        
        # Parse formats like "2h", "30min", "1d"
        if 'd' in effort:
            days = int(effort.replace('d', ''))
            minutes = days * 8 * 60  # 8 hours per day
        elif 'h' in effort:
            hours = int(effort.replace('h', ''))
            minutes = hours * 60
        elif 'min' in effort:
            minutes = int(effort.replace('min', ''))
        
        return minutes
    
    def __str__(self) -> str:
        """String representation of the issue."""
        location = f"{self.get_component_name()}:{self.line}" if self.line else self.get_component_name()
        return f"[{self.severity}] {self.type}: {self.message} ({location})"