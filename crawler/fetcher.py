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
    
    def __init__(self, rate_limit: float = 3.0, max_retries: int = 5):
        """
        Initialize fetcher.
        
        Args:
            rate_limit: Seconds between requests (default 3.0)
            max_retries: Maximum retry attempts for failed requests
        """
        self.rate_limit = rate_limit
        self.last_request_time = 0
        self.session = requests.Session()
        self.max_retries = max_retries
        
        # Configure retry strategy with exponential backoff
        retry_strategy = Retry(
            total=max_retries,
            backoff_factor=2,  # Exponential backoff: 1s, 2s, 4s, 8s, 16s
            status_forcelist=[500, 502, 503, 504, 429],
            allowed_methods=["GET", "HEAD"],
            raise_on_status=False
        )
        adapter = HTTPAdapter(
            max_retries=retry_strategy,
            pool_connections=10,
            pool_maxsize=10
        )
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)
        
        # Set browser-like User-Agent to avoid blocking
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1'
        })
    
    def _wait_for_rate_limit(self):
        """Wait if necessary to respect rate limit."""
        elapsed = time.time() - self.last_request_time
        if elapsed < self.rate_limit:
            time.sleep(self.rate_limit - elapsed)
        self.last_request_time = time.time()
    
    def fetch_url(self, url: str, timeout: int = 60) -> Tuple[Optional[str], Optional[int], Optional[str]]:
        """
        Fetch URL with rate limiting, retries, and error handling.
        
        Args:
            url: URL to fetch
            timeout: Request timeout in seconds (increased default to 60)
            
        Returns:
            Tuple of (html_content, status_code, error_message)
            Returns (None, status_code, error) on failure
        """
        self._wait_for_rate_limit()
        
        # Manual retry loop for connection errors
        last_error = None
        for attempt in range(self.max_retries):
            try:
                response = self.session.get(
                    url, 
                    timeout=timeout,
                    allow_redirects=True,
                    stream=False
                )
                response.raise_for_status()
                return response.text, response.status_code, None
                
            except requests.exceptions.Timeout as e:
                last_error = f"Timeout after {timeout}s"
                if attempt < self.max_retries - 1:
                    wait_time = 2 ** attempt  # Exponential backoff: 1s, 2s, 4s, 8s
                    time.sleep(wait_time)
                    continue
                return None, None, last_error
                
            except requests.exceptions.ConnectionError as e:
                last_error = f"Connection error: {str(e)}"
                if attempt < self.max_retries - 1:
                    wait_time = 2 ** attempt  # Exponential backoff
                    time.sleep(wait_time)
                    continue
                return None, None, last_error
                
            except requests.exceptions.HTTPError as e:
                status_code = e.response.status_code if e.response else None
                if status_code and 400 <= status_code < 500:
                    # 4xx errors are permanent, don't retry
                    return None, status_code, f"Client error {status_code}: {str(e)}"
                # 5xx errors - retry with backoff
                last_error = f"HTTP error {status_code}: {str(e)}"
                if attempt < self.max_retries - 1:
                    wait_time = 2 ** attempt
                    time.sleep(wait_time)
                    continue
                return None, status_code, last_error
                
            except requests.exceptions.RequestException as e:
                last_error = f"Request failed: {str(e)}"
                if attempt < self.max_retries - 1:
                    wait_time = 2 ** attempt
                    time.sleep(wait_time)
                    continue
                return None, None, last_error
        
        return None, None, last_error or "Max retries exceeded"
    
    def fetch_url_simple(self, url: str, timeout: int = 60) -> Optional[str]:
        """
        Simple fetch that returns HTML or None.
        
        Args:
            url: URL to fetch
            timeout: Request timeout in seconds (increased default to 60)
            
        Returns:
            HTML content or None on failure
        """
        html, status, error = self.fetch_url(url, timeout=timeout)
        if error:
            # Only print error on final failure (after all retries)
            pass  # Errors are logged by the logger, no need to print here
        return html


if __name__ == "__main__":
    # Test the fetcher
    fetcher = Fetcher(rate_limit=3.0)
    
    test_url = "https://www.netcarshow.com/"
    print(f"Testing fetch of {test_url}...")
    html = fetcher.fetch_url_simple(test_url)
    
    if html:
        print(f"Success! Fetched {len(html)} characters")
    else:
        print("Failed to fetch")


