"""SonarCloud API client for fetching project data."""

import time
import logging
from typing import List, Dict, Optional
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry


logger = logging.getLogger(__name__)


class SonarCloudAPIError(Exception):
    """Exception raised for SonarCloud API errors."""
    pass


class SonarCloudClient:
    """Client for interacting with SonarCloud API."""
    
    def __init__(self, token: str, base_url: str = "https://sonarcloud.io/api", timeout: int = 30):
        """
        Initialize SonarCloud API client.
        
        Args:
            token: SonarCloud API token
            base_url: Base URL for API
            timeout: Request timeout in seconds
        """
        self.token = token
        self.base_url = base_url.rstrip('/')
        self.timeout = timeout
        self.session = self._create_session()
    
    def _create_session(self) -> requests.Session:
        """
        Create requests session with retry logic.
        
        Returns:
            Configured requests session
        """
        session = requests.Session()
        
        # Configure retry strategy
        retry_strategy = Retry(
            total=3,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["GET", "POST"]
        )
        
        adapter = HTTPAdapter(max_retries=retry_strategy)
        session.mount("http://", adapter)
        session.mount("https://", adapter)
        
        # Set default headers
        session.headers.update({
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json",
        })
        
        return session
    
    def _make_request(self, endpoint: str, params: Optional[Dict] = None) -> Dict:
        """
        Make API request with error handling.
        
        Args:
            endpoint: API endpoint (without base URL)
            params: Query parameters
            
        Returns:
            JSON response as dictionary
            
        Raises:
            SonarCloudAPIError: If request fails
        """
        url = f"{self.base_url}/{endpoint.lstrip('/')}"
        
        try:
            logger.debug(f"Making request to {url} with params {params}")
            response = self.session.get(url, params=params, timeout=self.timeout)
            response.raise_for_status()
            return response.json()
        
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 401:
                raise SonarCloudAPIError(
                    "Authentication failed. Please check your API token. "
                    "Generate a new token at: https://sonarcloud.io/account/security"
                ) from e
            elif e.response.status_code == 403:
                raise SonarCloudAPIError(
                    "Access forbidden. Ensure your token has access to this project."
                ) from e
            elif e.response.status_code == 404:
                raise SonarCloudAPIError(
                    f"Resource not found. Please check the project key and organization."
                ) from e
            elif e.response.status_code == 429:
                raise SonarCloudAPIError(
                    "Rate limit exceeded. Please wait a moment and try again."
                ) from e
            else:
                raise SonarCloudAPIError(f"API request failed: {e}") from e
        
        except requests.exceptions.Timeout:
            raise SonarCloudAPIError(
                f"Request timed out after {self.timeout} seconds. "
                "Try increasing the timeout or check your network connection."
            )
        
        except requests.exceptions.RequestException as e:
            raise SonarCloudAPIError(f"Request failed: {e}") from e
    
    def _paginate(self, endpoint: str, params: Dict, items_key: str = 'issues') -> List[Dict]:
        """
        Fetch all pages of results.
        
        Args:
            endpoint: API endpoint
            params: Query parameters
            items_key: Key in response containing items
            
        Returns:
            List of all items across all pages
        """
        all_items = []
        page = 1
        
        while True:
            params['p'] = page
            params['ps'] = 500  # Maximum page size
            
            logger.debug(f"Fetching page {page}")
            response = self._make_request(endpoint, params)
            
            items = response.get(items_key, [])
            all_items.extend(items)
            
            # Check if there are more pages
            paging = response.get('paging', {})
            total = paging.get('total', 0)
            page_size = paging.get('pageSize', 500)
            
            if len(all_items) >= total or len(items) < page_size:
                break
            
            page += 1
            time.sleep(0.1)  # Small delay to avoid rate limiting
        
        logger.info(f"Fetched {len(all_items)} items from {endpoint}")
        return all_items
    
    def get_issues(self, project_key: str, statuses: Optional[List[str]] = None, severities: Optional[List[str]] = None) -> List[Dict]:
        """
        Fetch all issues for a project.
        
        Args:
            project_key: SonarCloud project key
            statuses: List of issue statuses to include (default: OPEN, CONFIRMED, REOPENED)
            severities: List of severities to filter by (e.g., ['BLOCKER', 'CRITICAL', 'MAJOR'])
            
        Returns:
            List of issue dictionaries
        """
        if statuses is None:
            statuses = ['OPEN', 'CONFIRMED', 'REOPENED']
        
        params = {
            'componentKeys': project_key,
            'types': 'VULNERABILITY,BUG,CODE_SMELL',
            'statuses': ','.join(statuses),
        }
        
        # Add severity filter if provided
        if severities:
            params['severities'] = ','.join(severities)
            logger.info(f"Filtering issues by severities: {', '.join(severities)}")
        
        return self._paginate('/api/issues/search', params, 'issues')
    
    def get_security_hotspots(self, project_key: str) -> List[Dict]:
        """
        Fetch security hotspots for a project.
        
        Args:
            project_key: SonarCloud project key
            
        Returns:
            List of security hotspot dictionaries
        """
        params = {
            'projectKey': project_key,
            'status': 'TO_REVIEW,REVIEWED',
        }
        
        try:
            return self._paginate('/api/hotspots/search', params, 'hotspots')
        except SonarCloudAPIError as e:
            logger.warning(f"Failed to fetch security hotspots: {e}")
            return []
    
    def get_metrics(self, project_key: str) -> List[Dict]:
        """
        Fetch project metrics.
        
        Args:
            project_key: SonarCloud project key
            
        Returns:
            List of metric dictionaries
        """
        metric_keys = [
            'ncloc',
            'coverage',
            'duplicated_lines_density',
            'sqale_index',
            'reliability_rating',
            'security_rating',
            'sqale_rating',
            'vulnerabilities',
            'bugs',
            'code_smells',
            'security_hotspots',
        ]
        
        params = {
            'component': project_key,
            'metricKeys': ','.join(metric_keys),
        }
        
        response = self._make_request('/api/measures/component', params)
        component = response.get('component', {})
        measures = component.get('measures', [])
        
        return measures
    
    def get_project_info(self, project_key: str) -> Dict:
        """
        Fetch project information.
        
        Args:
            project_key: SonarCloud project key
            
        Returns:
            Project information dictionary
        """
        params = {'component': project_key}
        response = self._make_request('/api/components/show', params)
        return response.get('component', {})
    
    def get_quality_gate_status(self, project_key: str) -> Dict:
        """
        Fetch quality gate status for a project.
        
        Args:
            project_key: SonarCloud project key
            
        Returns:
            Quality gate status dictionary
        """
        params = {'projectKey': project_key}
        
        try:
            return self._make_request('/api/qualitygates/project_status', params)
        except SonarCloudAPIError as e:
            logger.warning(f"Failed to fetch quality gate status: {e}")
            return {'projectStatus': {'status': 'UNKNOWN'}}
    
    def validate_connection(self) -> bool:
        """
        Validate API connection and authentication.
        
        Returns:
            True if connection is valid
            
        Raises:
            SonarCloudAPIError: If connection fails
        """
        try:
            self._make_request('/api/authentication/validate')
            return True
        except SonarCloudAPIError:
            raise
    
    def close(self):
        """Close the session."""
        self.session.close()
    
    def __enter__(self):
        """Context manager entry."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()