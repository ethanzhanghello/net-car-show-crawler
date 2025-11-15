"""
HTTP Fetcher with rate limiting and error handling for NetCarShow crawler.
"""

import time
import requests
from typing import Optional, Tuple
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry


class Fetcher:
    """Handles HTTP requests with rate limiting and retry logic."""
    
    def __init__(self, rate_limit: float = 1.5, max_retries: int = 3):
        """
        Initialize fetcher.
        
        Args:
            rate_limit: Seconds between requests (default 1.5 = ~0.67 QPS)
            max_retries: Maximum retry attempts for failed requests
        """
        self.rate_limit = rate_limit
        self.last_request_time = 0
        self.session = requests.Session()
        
        # Configure retry strategy
        retry_strategy = Retry(
            total=max_retries,
            backoff_factor=1,
            status_forcelist=[500, 502, 503, 504],
            allowed_methods=["GET", "HEAD"]
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)
        
        # Set custom User-Agent
        self.session.headers.update({
            'User-Agent': 'NetCarShowResearchBot/1.0 (Educational Research)'
        })
    
    def _wait_for_rate_limit(self):
        """Wait if necessary to respect rate limit."""
        elapsed = time.time() - self.last_request_time
        if elapsed < self.rate_limit:
            time.sleep(self.rate_limit - elapsed)
        self.last_request_time = time.time()
    
    def fetch_url(self, url: str, timeout: int = 30) -> Tuple[Optional[str], Optional[int], Optional[str]]:
        """
        Fetch URL with rate limiting and error handling.
        
        Args:
            url: URL to fetch
            timeout: Request timeout in seconds
            
        Returns:
            Tuple of (html_content, status_code, error_message)
            Returns (None, status_code, error) on failure
        """
        self._wait_for_rate_limit()
        
        try:
            response = self.session.get(url, timeout=timeout)
            response.raise_for_status()
            return response.text, response.status_code, None
            
        except requests.exceptions.Timeout:
            return None, None, f"Timeout after {timeout}s"
            
        except requests.exceptions.HTTPError as e:
            status_code = e.response.status_code if e.response else None
            if status_code and 400 <= status_code < 500:
                # 4xx errors are permanent, don't retry
                return None, status_code, f"Client error {status_code}: {str(e)}"
            # 5xx errors will be retried by the retry strategy
            return None, status_code, f"HTTP error {status_code}: {str(e)}"
            
        except requests.exceptions.RequestException as e:
            return None, None, f"Request failed: {str(e)}"
    
    def fetch_url_simple(self, url: str) -> Optional[str]:
        """
        Simple fetch that returns HTML or None.
        
        Args:
            url: URL to fetch
            
        Returns:
            HTML content or None on failure
        """
        html, status, error = self.fetch_url(url)
        if error:
            print(f"Error fetching {url}: {error}")
        return html


if __name__ == "__main__":
    # Test the fetcher
    fetcher = Fetcher(rate_limit=1.0)
    
    test_url = "https://www.netcarshow.com/"
    print(f"Testing fetch of {test_url}...")
    html = fetcher.fetch_url_simple(test_url)
    
    if html:
        print(f"Success! Fetched {len(html)} characters")
    else:
        print("Failed to fetch")


