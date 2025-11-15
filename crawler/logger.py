"""
Structured logging for the crawler.
"""

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional, Any


class CrawlerLogger:
    """Structured logger for crawler operations."""
    
    def __init__(self, log_dir: str = "logs"):
        """
        Initialize logger.
        
        Args:
            log_dir: Directory for log files
        """
        self.log_dir = log_dir
        os.makedirs(log_dir, exist_ok=True)
        
        # Create log file with date
        date_str = datetime.now().strftime("%Y%m%d")
        self.log_file = os.path.join(log_dir, f"crawl_{date_str}.log")
    
    def _write_log(self, level: str, message: str, **kwargs):
        """
        Write a log entry.
        
        Args:
            level: Log level (INFO, WARNING, ERROR, DEBUG)
            message: Log message
            **kwargs: Additional fields to include in log
        """
        log_entry = {
            'timestamp': datetime.now().isoformat(),
            'level': level,
            'message': message,
            **kwargs
        }
        
        try:
            with open(self.log_file, 'a', encoding='utf-8') as f:
                f.write(json.dumps(log_entry) + '\n')
        except IOError:
            # Fallback to stdout if file write fails
            print(f"[{level}] {message}")
    
    def info(self, message: str, url: Optional[str] = None, **kwargs):
        """Log info message."""
        if url:
            kwargs['url'] = url
        self._write_log('INFO', message, **kwargs)
    
    def warning(self, message: str, url: Optional[str] = None, **kwargs):
        """Log warning message."""
        if url:
            kwargs['url'] = url
        self._write_log('WARNING', message, **kwargs)
    
    def error(self, message: str, error: Optional[str] = None, url: Optional[str] = None, **kwargs):
        """Log error message."""
        if error:
            kwargs['error'] = str(error)
        if url:
            kwargs['url'] = url
        self._write_log('ERROR', message, **kwargs)
    
    def debug(self, message: str, **kwargs):
        """Log debug message."""
        self._write_log('DEBUG', message, **kwargs)
    
    def log_crawl_start(self, category: Optional[str] = None, subcategory: Optional[str] = None):
        """Log crawl start."""
        kwargs = {}
        if category:
            kwargs['category'] = category
        if subcategory:
            kwargs['subcategory'] = subcategory
        self.info("Crawl started", **kwargs)
    
    def log_crawl_complete(self, stats: Dict[str, Any]):
        """Log crawl completion with statistics."""
        self.info("Crawl completed", **stats)
    
    def log_url_discovered(self, url: str, count: Optional[int] = None):
        """Log URL discovery."""
        kwargs = {'url': url}
        if count is not None:
            kwargs['count'] = count
        self.info("URL discovered", **kwargs)
    
    def log_url_parsed(self, url: str, make: Optional[str] = None, model: Optional[str] = None):
        """Log URL parsing."""
        kwargs = {'url': url}
        if make:
            kwargs['make'] = make
        if model:
            kwargs['model'] = model
        self.info("URL parsed", **kwargs)
    
    def log_url_saved(self, url: str, file_path: Optional[str] = None):
        """Log URL saved."""
        kwargs = {'url': url}
        if file_path:
            kwargs['file_path'] = file_path
        self.info("URL saved", **kwargs)
    
    def log_url_failed(self, url: str, error: str):
        """Log URL failure."""
        self.error("URL failed", error=error, url=url)
    
    def log_parse_error(self, url: str, error: str, html_saved: Optional[str] = None):
        """Log parsing error."""
        kwargs = {'url': url, 'error': error}
        if html_saved:
            kwargs['html_saved'] = html_saved
        self.error("Parse error", **kwargs)
    
    def save_html_for_debugging(self, html: str, url: str, error_dir: str = "logs/errors") -> Optional[str]:
        """
        Save HTML for debugging on parse failures.
        
        Args:
            html: HTML content to save
            url: URL that failed
            error_dir: Directory to save error HTML files
            
        Returns:
            Path to saved HTML file or None if save failed
        """
        os.makedirs(error_dir, exist_ok=True)
        
        # Create safe filename from URL
        safe_filename = url.replace('https://', '').replace('http://', '').replace('/', '_')
        safe_filename = ''.join(c if c.isalnum() or c in '._-' else '_' for c in safe_filename)
        safe_filename = safe_filename[:200]  # Limit length
        
        file_path = os.path.join(error_dir, f"{safe_filename}.html")
        
        try:
            with open(file_path, 'w', encoding='utf-8', errors='ignore') as f:
                f.write(html)
            return file_path
        except IOError:
            return None

