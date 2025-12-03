"""Metric data model for SonarCloud metrics."""

from dataclasses import dataclass
from typing import Optional


@dataclass
class Metric:
    """Represents a SonarCloud project metric."""
    
    key: str
    value: str
    metric_name: str
    
    @classmethod
    def from_api_response(cls, data: dict) -> 'Metric':
        """
        Create a Metric instance from SonarCloud API response.
        
        Args:
            data: Dictionary from SonarCloud API
            
        Returns:
            Metric instance
        """
        metric_key = data.get('metric', '')
        return cls(
            key=metric_key,
            value=data.get('value', '0'),
            metric_name=cls._get_metric_display_name(metric_key),
        )
    
    @staticmethod
    def _get_metric_display_name(key: str) -> str:
        """
        Get human-readable name for metric key.
        
        Args:
            key: Metric key from API
            
        Returns:
            Display name
        """
        metric_names = {
            'ncloc': 'Lines of Code',
            'coverage': 'Code Coverage',
            'duplicated_lines_density': 'Duplicated Lines',
            'sqale_index': 'Technical Debt',
            'reliability_rating': 'Reliability Rating',
            'security_rating': 'Security Rating',
            'sqale_rating': 'Maintainability Rating',
            'vulnerabilities': 'Vulnerabilities',
            'bugs': 'Bugs',
            'code_smells': 'Code Smells',
            'security_hotspots': 'Security Hotspots',
            'complexity': 'Cyclomatic Complexity',
            'cognitive_complexity': 'Cognitive Complexity',
            'comment_lines_density': 'Comment Density',
            'classes': 'Classes',
            'functions': 'Functions',
            'files': 'Files',
        }
        return metric_names.get(key, key.replace('_', ' ').title())
    
    def get_formatted_value(self) -> str:
        """
        Format metric value for display.
        
        Returns:
            Formatted value string
        """
        # Handle percentage metrics
        if self.key in ['coverage', 'duplicated_lines_density', 'comment_lines_density']:
            try:
                return f"{float(self.value):.1f}%"
            except ValueError:
                return self.value
        
        # Handle time-based metrics (technical debt)
        if self.key == 'sqale_index':
            return self._format_minutes(self.value)
        
        # Handle rating metrics
        if 'rating' in self.key:
            return self._format_rating(self.value)
        
        # Handle numeric metrics with thousands separator
        try:
            num_value = int(float(self.value))
            return f"{num_value:,}"
        except ValueError:
            return self.value
    
    @staticmethod
    def _format_minutes(minutes_str: str) -> str:
        """
        Format minutes into human-readable time.
        
        Args:
            minutes_str: Minutes as string
            
        Returns:
            Formatted time (e.g., "2d 4h")
        """
        try:
            minutes = int(float(minutes_str))
            
            days = minutes // (8 * 60)  # 8 hour work day
            remaining_minutes = minutes % (8 * 60)
            hours = remaining_minutes // 60
            mins = remaining_minutes % 60
            
            parts = []
            if days > 0:
                parts.append(f"{days}d")
            if hours > 0:
                parts.append(f"{hours}h")
            if mins > 0 and days == 0:  # Only show minutes if less than a day
                parts.append(f"{mins}min")
            
            return " ".join(parts) if parts else "0min"
        except ValueError:
            return minutes_str
    
    @staticmethod
    def _format_rating(rating_str: str) -> str:
        """
        Format rating value.
        
        Args:
            rating_str: Rating as string (1-5)
            
        Returns:
            Rating letter (A-E)
        """
        rating_map = {
            '1': 'A',
            '1.0': 'A',
            '2': 'B',
            '2.0': 'B',
            '3': 'C',
            '3.0': 'C',
            '4': 'D',
            '4.0': 'D',
            '5': 'E',
            '5.0': 'E',
        }
        return rating_map.get(rating_str, rating_str)
    
    def __str__(self) -> str:
        """String representation of the metric."""
        return f"{self.metric_name}: {self.get_formatted_value()}"