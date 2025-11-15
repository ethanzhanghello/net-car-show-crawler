"""
Checkpointing system for resume capability.
"""

import json
import os
from typing import Dict, Set, Optional
from datetime import datetime


class Checkpoint:
    """Manages checkpoint state for crawler resume capability."""
    
    def __init__(self, checkpoint_dir: str = "checkpoints"):
        """
        Initialize checkpoint system.
        
        Args:
            checkpoint_dir: Directory to store checkpoint files
        """
        self.checkpoint_dir = checkpoint_dir
        self.checkpoint_file = os.path.join(checkpoint_dir, "checkpoint.json")
        self.completed_urls_file = os.path.join(checkpoint_dir, "completed_urls.txt")
        
        # Ensure checkpoint directory exists
        os.makedirs(checkpoint_dir, exist_ok=True)
        
        # Load existing checkpoint
        self.checkpoint_data = self._load_checkpoint()
        self.completed_urls = self._load_completed_urls()
    
    def _load_checkpoint(self) -> Dict[str, Dict]:
        """Load checkpoint JSON file."""
        if os.path.exists(self.checkpoint_file):
            try:
                with open(self.checkpoint_file, 'r') as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError):
                return {}
        return {}
    
    def _load_completed_urls(self) -> Set[str]:
        """Load completed URLs from text file."""
        completed = set()
        if os.path.exists(self.completed_urls_file):
            try:
                with open(self.completed_urls_file, 'r') as f:
                    for line in f:
                        url = line.strip()
                        if url:
                            completed.add(url)
            except IOError:
                pass
        return completed
    
    def _save_checkpoint(self):
        """Save checkpoint to JSON file."""
        try:
            with open(self.checkpoint_file, 'w') as f:
                json.dump(self.checkpoint_data, f, indent=2)
        except IOError as e:
            print(f"Error saving checkpoint: {e}")
    
    def _save_completed_urls(self):
        """Save completed URLs to text file."""
        try:
            with open(self.completed_urls_file, 'w') as f:
                for url in sorted(self.completed_urls):
                    f.write(f"{url}\n")
        except IOError as e:
            print(f"Error saving completed URLs: {e}")
    
    def get_status(self, url: str) -> Optional[str]:
        """
        Get status of a URL.
        
        Args:
            url: URL to check
            
        Returns:
            Status string or None if not found
        """
        if url in self.checkpoint_data:
            return self.checkpoint_data[url].get('status')
        return None
    
    def is_completed(self, url: str) -> bool:
        """
        Check if URL has been completed.
        
        Args:
            url: URL to check
            
        Returns:
            True if URL is marked as completed
        """
        return url in self.completed_urls
    
    def mark_discovered(self, url: str):
        """Mark URL as discovered."""
        self.checkpoint_data[url] = {
            'status': 'discovered',
            'timestamp': datetime.now().isoformat()
        }
        self._save_checkpoint()
    
    def mark_parsed(self, url: str):
        """Mark URL as parsed."""
        if url not in self.checkpoint_data:
            self.checkpoint_data[url] = {}
        self.checkpoint_data[url]['status'] = 'parsed'
        self.checkpoint_data[url]['timestamp'] = datetime.now().isoformat()
        self._save_checkpoint()
    
    def mark_saved(self, url: str):
        """Mark URL as saved (completed)."""
        if url not in self.checkpoint_data:
            self.checkpoint_data[url] = {}
        self.checkpoint_data[url]['status'] = 'saved'
        self.checkpoint_data[url]['timestamp'] = datetime.now().isoformat()
        self.completed_urls.add(url)
        self._save_checkpoint()
        self._save_completed_urls()
    
    def mark_failed(self, url: str, error: str = ""):
        """Mark URL as failed."""
        if url not in self.checkpoint_data:
            self.checkpoint_data[url] = {}
        self.checkpoint_data[url]['status'] = 'failed'
        self.checkpoint_data[url]['error'] = error
        self.checkpoint_data[url]['timestamp'] = datetime.now().isoformat()
        self._save_checkpoint()
    
    def get_incomplete_urls(self) -> list:
        """Get list of URLs that are not completed."""
        incomplete = []
        for url, data in self.checkpoint_data.items():
            if data.get('status') != 'saved':
                incomplete.append(url)
        return incomplete
    
    def get_statistics(self) -> Dict[str, int]:
        """Get checkpoint statistics."""
        stats = {
            'total': len(self.checkpoint_data),
            'discovered': 0,
            'parsed': 0,
            'saved': 0,
            'failed': 0
        }
        
        for url, data in self.checkpoint_data.items():
            status = data.get('status', 'unknown')
            if status in stats:
                stats[status] += 1
        
        return stats
    
    def reset(self):
        """Reset checkpoint (use with caution)."""
        self.checkpoint_data = {}
        self.completed_urls = set()
        if os.path.exists(self.checkpoint_file):
            os.remove(self.checkpoint_file)
        if os.path.exists(self.completed_urls_file):
            os.remove(self.completed_urls_file)


if __name__ == "__main__":
    # Test checkpoint system
    checkpoint = Checkpoint()
    
    # Test marking URLs
    test_url = "https://www.netcarshow.com/test"
    checkpoint.mark_discovered(test_url)
    print(f"Status after discover: {checkpoint.get_status(test_url)}")
    
    checkpoint.mark_parsed(test_url)
    print(f"Status after parse: {checkpoint.get_status(test_url)}")
    
    checkpoint.mark_saved(test_url)
    print(f"Status after save: {checkpoint.get_status(test_url)}")
    print(f"Is completed: {checkpoint.is_completed(test_url)}")
    
    stats = checkpoint.get_statistics()
    print(f"\nStatistics: {stats}")


