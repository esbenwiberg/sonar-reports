"""Issue data model for SonarCloud issues."""

import logging
import re
from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional


logger = logging.getLogger(__name__)


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
    
    def get_ui_severity(self) -> str:
        """
        Get UI-friendly severity name matching SonarCloud UI.
        
        Maps API severity terms to UI terms:
        - BLOCKER -> Blocker
        - CRITICAL -> High
        - MAJOR -> Medium
        - MINOR -> Low
        - INFO -> Info
        
        Returns:
            UI-friendly severity name
        """
        severity_map = {
            'BLOCKER': 'Blocker',
            'CRITICAL': 'High',
            'MAJOR': 'Medium',
            'MINOR': 'Low',
            'INFO': 'Info'
        }
        return severity_map.get(self.severity, self.severity)
    
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
    
    #: Minutes per unit in SonarCloud effort strings. A working day is 8 hours.
    _EFFORT_UNIT_MINUTES = {'min': 1, 'h': 60, 'd': 8 * 60}

    #: 'min' before 'd'/'h' so the longer unit wins the alternation.
    _EFFORT_PATTERN = re.compile(r'(\d+)\s*(min|d|h)')

    def get_effort_minutes(self) -> int:
        """
        Convert a SonarCloud effort string to minutes.

        Efforts are compound — "1h58min", "1d4h", "3d2h15min" — so every
        unit present is summed. A bare number is read as minutes.

        Returns:
            Effort in minutes, or 0 if unset or unparseable
        """
        if not self.effort:
            return 0

        effort = str(self.effort).strip().lower()

        matches = self._EFFORT_PATTERN.findall(effort)
        if matches:
            return sum(
                int(amount) * self._EFFORT_UNIT_MINUTES[unit]
                for amount, unit in matches
            )

        # SonarCloud sometimes reports a plain minute count with no unit.
        try:
            return int(float(effort))
        except ValueError:
            logger.warning(f"Could not parse effort value {self.effort!r}")
            return 0
    
    def __str__(self) -> str:
        """String representation of the issue."""
        location = f"{self.get_component_name()}:{self.line}" if self.line else self.get_component_name()
        return f"[{self.severity}] {self.type}: {self.message} ({location})"