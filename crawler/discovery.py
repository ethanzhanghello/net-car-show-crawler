"""
Discovery logic for finding categories, subcategories, and model URLs.
"""

from bs4 import BeautifulSoup
from typing import List, Dict, Optional
from .fetcher import Fetcher


class Discovery:
    """Handles discovery of categories, subcategories, and model listings."""
    
    def __init__(self, fetcher: Optional[Fetcher] = None):
        """Initialize discovery with optional fetcher."""
        self.fetcher = fetcher or Fetcher()
        self.base_url = "https://www.netcarshow.com"
    
    def discover_main_categories(self) -> List[Dict[str, str]]:
        """
        Discover all main type-based categories from homepage.
        
        Returns:
            List of dicts with 'name' and 'url' keys
        """
        html = self.fetcher.fetch_url_simple(f"{self.base_url}/")
        if not html:
            return []
        
        soup = BeautifulSoup(html, 'lxml')
        categories = []
        
        # Find all category links in the Explore section
        # Categories are in links like /explore/coupe/, /explore/sedan/, etc.
        explore_links = soup.find_all('a', href=lambda x: x and x.startswith('/explore/'))
        
        seen = set()
        for link in explore_links:
            href = link.get('href', '')
            # Filter out subcategory links (they have more path segments)
            # Main categories: /explore/coupe/ (2 segments after stripping)
            # Subcategories: /explore/crossover-suv/premium/ (3 segments after stripping)
            href_clean = href.rstrip('/')
            parts = href_clean.split('/')
            # Main category has exactly 2 parts: ['', 'explore', 'category']
            if len(parts) == 3 and parts[1] == 'explore' and href not in seen:
                seen.add(href)
                category_name = parts[2] if len(parts) > 2 else ''
                name = link.get_text().strip() or category_name.replace('-', ' ').title()
                categories.append({
                    'name': name,
                    'url': f"{self.base_url}{href_clean}",
                    'type': category_name
                })
        
        return categories
    
    def discover_subcategories(self, category_url: str) -> List[Dict[str, str]]:
        """
        Discover subcategories from a category page.
        
        Args:
            category_url: URL of the category page (e.g., /explore/crossover-suv/)
            
        Returns:
            List of dicts with 'name' and 'url' keys
        """
        html = self.fetcher.fetch_url_simple(category_url)
        if not html:
            return []
        
        soup = BeautifulSoup(html, 'lxml')
        subcategories = []
        
        # Look for subcategory links - they appear as "SHOW MORE" links or direct links
        # Pattern: /explore/{category}/{subcategory}/
        category_type = category_url.rstrip('/').split('/')[-1]
        
        # Find links that match the subcategory pattern
        all_links = soup.find_all('a', href=True)
        seen = set()
        
        for link in all_links:
            href = link.get('href', '')
            # Check if it's a subcategory link
            if f'/explore/{category_type}/' in href and href.count('/') == 4:
                if href not in seen:
                    seen.add(href)
                    # Extract subcategory name from URL or link text
                    subcat_name = href.rstrip('/').split('/')[-1]
                    # Try to get better name from link text or nearby elements
                    link_text = link.get_text().strip()
                    if link_text and 'show more' not in link_text.lower():
                        subcat_name = link_text
                    
                    subcategories.append({
                        'name': subcat_name.replace('-', ' ').title(),
                        'url': f"{self.base_url}{href}",
                        'subtype': href.rstrip('/').split('/')[-1]
                    })
        
        # Also look for subcategory section dividers (like "Premium SUV", "Midsize SUV")
        # These appear as <span class="seDi"> elements with links
        subcat_sections = soup.find_all('span', class_='seDi')
        for section in subcat_sections:
            link = section.find('a')
            if link:
                href = link.get('href', '')
                if href and href not in seen:
                    seen.add(href)
                    name = link.get_text().strip()
                    subcategories.append({
                        'name': name,
                        'url': f"{self.base_url}{href}",
                        'subtype': href.rstrip('/').split('/')[-1]
                    })
        
        return subcategories
    
    def discover_model_urls_from_listing(self, listing_url: str) -> List[str]:
        """
        Discover all model URLs from a listing page.
        
        Args:
            listing_url: URL of a listing page (category or subcategory)
            
        Returns:
            List of model URLs
        """
        html = self.fetcher.fetch_url_simple(listing_url)
        if not html:
            return []
        
        soup = BeautifulSoup(html, 'lxml')
        model_urls = []
        
        # Find all links to model detail pages
        # Pattern: /{make}/{year}-{model}/
        all_links = soup.find_all('a', href=True)
        seen = set()
        
        for link in all_links:
            href = link.get('href', '')
            # Model URLs have pattern: /make/year-model/ (not ending in -wallpapers)
            if href.startswith('/') and '/' in href[1:] and not href.endswith('/'):
                parts = href.strip('/').split('/')
                if len(parts) == 2 and '-' in parts[1] and '-wallpapers' not in href:
                    full_url = f"{self.base_url}{href}"
                    if full_url not in seen:
                        seen.add(full_url)
                        model_urls.append(full_url)
        
        return model_urls


if __name__ == "__main__":
    # Test discovery
    discovery = Discovery()
    
    print("Discovering main categories...")
    categories = discovery.discover_main_categories()
    print(f"Found {len(categories)} categories:")
    for cat in categories[:5]:
        print(f"  - {cat['name']}: {cat['url']}")
    
    if categories:
        print(f"\nDiscovering subcategories for {categories[0]['name']}...")
        subcats = discovery.discover_subcategories(categories[0]['url'])
        print(f"Found {len(subcats)} subcategories:")
        for subcat in subcats[:5]:
            print(f"  - {subcat['name']}: {subcat['url']}")


