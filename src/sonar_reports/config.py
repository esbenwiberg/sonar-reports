"""
Configuration management for SonarCloud SAST Report Generator.

Supports loading configuration from:
1. Command-line arguments (highest priority)
2. Environment variables
3. YAML config file
4. Defaults (lowest priority)
"""

import os
from dataclasses import dataclass, field
from typing import List, Optional
from pathlib import Path
import yaml
from dotenv import load_dotenv


@dataclass
class Config:
    """Configuration for SonarCloud report generation."""
    
    # SonarCloud settings
    sonarcloud_token: str
    organization: Optional[str] = None
    project_key: Optional[str] = None
    base_url: str = "https://sonarcloud.io"
    
    # Report settings
    output_path: str = "./reports"
    include_resolved: bool = False
    severity_filter: List[str] = field(default_factory=lambda: ["BLOCKER", "CRITICAL", "MAJOR"])
    max_issues_per_section: int = 10
    
    # API settings
    timeout: int = 30
    max_retries: int = 3
    
    def __post_init__(self):
        """Validate configuration after initialization."""
        if not self.sonarcloud_token:
            raise ValueError("SonarCloud token is required")
        
        # Ensure output path exists
        Path(self.output_path).mkdir(parents=True, exist_ok=True)
    
    @classmethod
    def from_env(cls, project_key: Optional[str] = None) -> 'Config':
        """
        Load configuration from environment variables.
        
        Args:
            project_key: Optional project key to override environment variable
            
        Returns:
            Config instance
            
        Raises:
            ValueError: If required configuration is missing
        """
        load_dotenv()
        
        token = os.getenv("SONARCLOUD_TOKEN")
        if not token:
            raise ValueError(
                "SONARCLOUD_TOKEN environment variable is required. "
                "Get your token at: https://sonarcloud.io/account/security"
            )
        
        return cls(
            sonarcloud_token=token,
            organization=os.getenv("SONARCLOUD_ORGANIZATION"),
            project_key=project_key or os.getenv("SONARCLOUD_PROJECT_KEY"),
            base_url=os.getenv("SONARCLOUD_BASE_URL", "https://sonarcloud.io"),
            output_path=os.getenv("REPORT_OUTPUT_PATH", "./reports"),
            include_resolved=os.getenv("REPORT_INCLUDE_RESOLVED", "false").lower() == "true",
        )
    
    @classmethod
    def from_file(cls, config_path: str, project_key: Optional[str] = None) -> 'Config':
        """
        Load configuration from YAML file.
        
        Args:
            config_path: Path to YAML configuration file
            project_key: Optional project key to override config file
            
        Returns:
            Config instance
            
        Raises:
            FileNotFoundError: If config file doesn't exist
            ValueError: If required configuration is missing
        """
        config_file = Path(config_path)
        if not config_file.exists():
            raise FileNotFoundError(f"Configuration file not found: {config_path}")
        
        with open(config_file, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f)
        
        sonarcloud = data.get('sonarcloud', {})
        report = data.get('report', {})
        
        token = sonarcloud.get('token')
        if not token:
            # Try to get from environment as fallback
            load_dotenv()
            token = os.getenv("SONARCLOUD_TOKEN")
        
        if not token:
            raise ValueError(
                "SonarCloud token is required in config file or SONARCLOUD_TOKEN environment variable"
            )
        
        return cls(
            sonarcloud_token=token,
            organization=sonarcloud.get('organization'),
            project_key=project_key or sonarcloud.get('project_key'),
            base_url=sonarcloud.get('base_url', 'https://sonarcloud.io'),
            output_path=report.get('output_path', './reports'),
            include_resolved=report.get('include_resolved', False),
            severity_filter=report.get('severity_filter', ['BLOCKER', 'CRITICAL', 'MAJOR']),
            max_issues_per_section=report.get('max_issues_per_section', 10),
        )
    
    def validate(self) -> bool:
        """
        Validate the configuration.
        
        Returns:
            True if configuration is valid
            
        Raises:
            ValueError: If configuration is invalid
        """
        if not self.sonarcloud_token:
            raise ValueError("SonarCloud token is required")
        
        if not self.base_url:
            raise ValueError("Base URL is required")
        
        if self.timeout <= 0:
            raise ValueError("Timeout must be positive")
        
        if self.max_retries < 0:
            raise ValueError("Max retries must be non-negative")
        
        valid_severities = ['BLOCKER', 'CRITICAL', 'MAJOR', 'MINOR', 'INFO']
        for severity in self.severity_filter:
            if severity not in valid_severities:
                raise ValueError(
                    f"Invalid severity '{severity}'. Must be one of: {', '.join(valid_severities)}"
                )
        
        return True
    
    def get_headers(self) -> dict:
        """
        Get HTTP headers for API requests.
        
        Returns:
            Dictionary of headers including authorization
        """
        return {
            "Authorization": f"Bearer {self.sonarcloud_token}",
            "Content-Type": "application/json",
        }
    
    def __repr__(self) -> str:
        """String representation with masked token."""
        token_preview = f"{self.sonarcloud_token[:8]}..." if self.sonarcloud_token else "None"
        return (
            f"Config(organization={self.organization}, "
            f"project_key={self.project_key}, "
            f"token={token_preview}, "
            f"base_url={self.base_url})"
        )