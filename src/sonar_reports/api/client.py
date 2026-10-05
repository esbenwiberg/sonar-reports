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
    
    def __init__(self, token: str, base_url: str = "https://sonarcloud.io", timeout: int = 30,
                 organization: Optional[str] = None):
        """
        Initialize SonarCloud API client.
        
        Args:
            token: SonarCloud API token
            base_url: Base URL for API
            timeout: Request timeout in seconds
            organization: SonarCloud organization key. Required when authenticating
                with an organization token — SonarCloud rejects such requests with
                HTTP 400 unless 'organization' is sent on every call.
        """
        self.token = token
        self.base_url = base_url.rstrip('/')
        self.timeout = timeout
        self.organization = organization
        # Endpoints observed to reject the 'organization' param, learned at runtime
        # so we only pay the retry once per endpoint per session.
        self._no_org_endpoints = set()
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
    
    @staticmethod
    def _error_detail(response) -> str:
        """
        Extract SonarCloud's own error message from a failed response.

        SonarCloud returns {"errors":[{"msg":"..."}]}; without this the caller only
        ever sees a bare status code, which makes failures undiagnosable.
        """
        try:
            payload = response.json()
        except (ValueError, AttributeError):
            return (getattr(response, 'text', '') or '').strip()[:500]

        msgs = [
            e.get('msg', '') for e in payload.get('errors', [])
            if isinstance(e, dict)
        ]
        detail = '; '.join(m for m in msgs if m)
        return detail or (getattr(response, 'text', '') or '').strip()[:500]

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
        params = dict(params or {})

        # Organization tokens are only accepted when 'organization' accompanies
        # every request. Harmless for user tokens: SonarCloud ignores it where
        # it is not a documented parameter.
        send_org = bool(self.organization) and endpoint not in self._no_org_endpoints
        if send_org:
            params.setdefault('organization', self.organization)

        try:
            logger.debug(f"Making request to {url} with params {params}")
            response = self.session.get(url, params=params, timeout=self.timeout)
            response.raise_for_status()
            return response.json()
        
        except requests.exceptions.HTTPError as e:
            detail = self._error_detail(e.response)
            status = e.response.status_code

            # An endpoint that does not accept 'organization' — drop it and retry
            # once, remembering the endpoint so later calls skip straight through.
            if (status == 400 and send_org and 'organization' in detail.lower()
                    and 'required' not in detail.lower()):
                logger.debug(
                    f"{endpoint} rejected the 'organization' parameter "
                    f"({detail}); retrying without it"
                )
                self._no_org_endpoints.add(endpoint)
                params.pop('organization', None)
                return self._make_request(endpoint, params)

            if status == 400 and 'organization' in detail.lower() and 'required' in detail.lower():
                raise SonarCloudAPIError(
                    f"{detail}. This token is a SonarCloud organization token, so the "
                    "organization key must be supplied. Pass --organization <key>, set "
                    "SONARCLOUD_ORGANIZATION, or add sonarcloud.organization to your "
                    "config file."
                ) from e

            if e.response.status_code == 401:
                raise SonarCloudAPIError(
                    "Authentication failed. Please check your API token. "
                    "Generate a new token at: https://sonarcloud.io/account/security"
                ) from e
            elif e.response.status_code == 403:
                raise SonarCloudAPIError(
                    "Access forbidden. Ensure your token has access to this project."
                    + (f" ({detail})" if detail else "")
                ) from e
            elif e.response.status_code == 404:
                raise SonarCloudAPIError(
                    f"Resource not found ({detail or 'no detail'}). "
                    "Please check the project key and organization."
                ) from e
            elif e.response.status_code == 429:
                raise SonarCloudAPIError(
                    "Rate limit exceeded. Please wait a moment and try again."
                ) from e
            else:
                raise SonarCloudAPIError(
                    f"API request failed: HTTP {status}"
                    + (f" — {detail}" if detail else "")
                    + f" for {url}"
                ) from e
        
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
    
    def get_security_hotspots(self, project_key: str,
                              statuses: Optional[List[str]] = None) -> List[Dict]:
        """
        Fetch security hotspots for a project.

        api/hotspots/search takes a SINGLE 'status' value — a comma-separated
        list is rejected with HTTP 400 — so each status is fetched separately
        and the results merged.

        Args:
            project_key: SonarCloud project key
            statuses: Hotspot statuses to fetch (default: TO_REVIEW, REVIEWED)

        Returns:
            List of security hotspot dictionaries
        """
        if statuses is None:
            statuses = ['TO_REVIEW', 'REVIEWED']

        hotspots: List[Dict] = []
        for status in statuses:
            params = {'projectKey': project_key, 'status': status}
            try:
                hotspots.extend(
                    self._paginate('/api/hotspots/search', params, 'hotspots')
                )
            except SonarCloudAPIError as e:
                # Keep whatever we did retrieve; hotspots are supplementary.
                logger.warning(f"Failed to fetch '{status}' security hotspots: {e}")
        return hotspots
    
    def enrich_hotspots(self, hotspots: List[Dict]) -> List[Dict]:
        """
        Add review context to hotspots from api/hotspots/show (one call each).

        api/hotspots/search returns the scanner's view only. The show endpoint
        adds the human side: the rule's readable title and the reviewer's
        comments explaining why a hotspot was marked safe or fixed. Both are
        what a reader needs to see a reviewed hotspot as closed rather than as
        an unaddressed finding.

        Adds ``ruleName`` (str or None) and ``reviewComments`` (list of str,
        de-duplicated, in order). Never raises: a hotspot whose detail call
        fails keeps its search-result fields and gets an empty comment list.
        """
        for hotspot in hotspots:
            hotspot.setdefault('ruleName', None)
            hotspot.setdefault('reviewComments', [])
            key = hotspot.get('key')
            if not key:
                continue
            try:
                detail = self._make_request('/api/hotspots/show', {'hotspot': key})
            except SonarCloudAPIError as e:
                logger.warning(f"Could not fetch details for hotspot {key}: {e}")
                continue
            rule = detail.get('rule') or {}
            hotspot['ruleName'] = rule.get('name') or hotspot.get('ruleName')
            seen = set()
            comments = []
            for c in detail.get('comment') or []:
                text = (c.get('markdown') or c.get('htmlText') or '').strip()
                if text and text not in seen:
                    seen.add(text)
                    comments.append(text)
            hotspot['reviewComments'] = comments
        return hotspots

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
        
        try:
            response = self._make_request('/api/measures/component', params)
        except SonarCloudAPIError as e:
            # Organization tokens are refused by the component-addressed
            # endpoints (404 "Project doesn't exist"). Recover what we can from
            # the branch listing rather than dropping the section entirely.
            logger.warning(
                f"api/measures/component unavailable for {project_key} ({e}); "
                "deriving headline metrics from api/project_branches/list"
            )
            return self._metrics_from_branches(project_key)

        component = response.get('component', {})
        measures = component.get('measures', [])
        
        return measures

    # Branch-status field -> SonarCloud metric key.
    _BRANCH_STATUS_METRICS = (
        ('bugs', 'bugs'),
        ('vulnerabilities', 'vulnerabilities'),
        ('codeSmells', 'code_smells'),
        ('securityHotspots', 'security_hotspots'),
    )

    def _metrics_from_branches(self, project_key: str) -> List[Dict]:
        """
        Derive headline metrics from api/project_branches/list.

        That endpoint is permitted for organization tokens and its main-branch
        entry carries bug, vulnerability and code-smell counts. Size and
        coverage metrics (ncloc, coverage, ratings) are not available here and
        are simply absent from the report.

        Args:
            project_key: SonarCloud project key

        Returns:
            List of measure dicts shaped like api/measures/component's output
        """
        try:
            response = self._make_request(
                '/api/project_branches/list', {'project': project_key}
            )
        except SonarCloudAPIError as e:
            logger.warning(f"Could not derive metrics for {project_key}: {e}")
            return []

        branches = response.get('branches', [])
        main_branch = next((b for b in branches if b.get('isMain')), None)
        if main_branch is None:
            logger.warning(f"No main branch reported for {project_key}")
            return []

        status = main_branch.get('status', {}) or {}
        measures = [
            {'metric': metric_key, 'value': str(status[field])}
            for field, metric_key in self._BRANCH_STATUS_METRICS
            if status.get(field) is not None
        ]

        if measures:
            logger.info(
                f"Derived {len(measures)} metric(s) for {project_key} from "
                f"branch '{main_branch.get('name', '?')}'"
            )
        return measures
    
    def get_project_info(self, project_key: str) -> Dict:
        """
        Fetch project information.
        
        Args:
            project_key: SonarCloud project key
            
        Returns:
            Project information dictionary
        """
        try:
            response = self._make_request('/api/components/show', {'component': project_key})
            return response.get('component', {})
        except SonarCloudAPIError as e:
            logger.warning(
                f"api/components/show unavailable for {project_key} ({e}); "
                "falling back to api/projects/search"
            )
            return self._project_info_from_search(project_key)

    def _project_info_from_search(self, project_key: str) -> Dict:
        """
        Recover project metadata via api/projects/search.

        Organization tokens are refused by the component-addressed endpoints,
        but can still list projects — and that listing carries everything the
        report header needs (key, name, organization, lastAnalysisDate).

        Args:
            project_key: SonarCloud project key

        Returns:
            Component-shaped dict, or {} if the project could not be recovered
        """
        if not self.organization:
            logger.warning(
                "Cannot recover project info without an organization key "
                "(pass --organization or set SONARCLOUD_ORGANIZATION)"
            )
            return {}

        try:
            response = self._make_request(
                '/api/projects/search',
                {'organization': self.organization, 'q': project_key, 'ps': 100},
            )
        except SonarCloudAPIError as e:
            logger.warning(f"Could not recover project info for {project_key}: {e}")
            return {}

        for component in response.get('components', []):
            if component.get('key') == project_key:
                info = dict(component)
                # projects/search returns 'lastAnalysisDate'; components/show
                # returns 'analysisDate'. ProjectInfo expects the latter.
                if 'analysisDate' not in info:
                    info['analysisDate'] = component.get('lastAnalysisDate', '')
                info.setdefault('organization', self.organization)
                return info

        logger.warning(f"Project {project_key} not found via api/projects/search")
        return {}
    
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