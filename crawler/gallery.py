"""
Image gallery parser for extracting high-resolution images from NetCarShow gallery pages.
"""

from bs4 import BeautifulSoup
from typing import List, Optional
from urllib.parse import urljoin
import re


class GalleryParser:
    """Handles parsing of gallery pages to extract image URLs."""
    
    def __init__(self, base_url: str = "https://www.netcarshow.com"):
        """Initialize gallery parser with base URL."""
        self.base_url = base_url
    
    def parse_gallery_page(self, html: str, make: str = None, model: str = None) -> List[str]:
        """
        Parse a gallery page to extract all high-resolution image URLs.
        
        Args:
            html: HTML content of the gallery page
            make: Make name to filter images (e.g., "acura")
            model: Model name to filter images (e.g., "ilx")
            
        Returns:
            List of image URLs (preferring highest resolution, filtered by model if provided)
        """
        if not html:
            return []
        
        soup = BeautifulSoup(html, 'lxml')
        image_urls = []
        seen = set()
        
        # Normalize make and model for filtering
        make_filter = make.lower().replace('_', '-') if make else None
        model_filter = model.lower().replace('_', '-') if model else None
        
        # Find all image tags
        img_tags = soup.find_all('img')
        for img in img_tags:
            # Try different attributes for image URLs
            for attr in ['src', 'data-src', 'data-lazy-src', 'data-original']:
                url = img.get(attr)
                if url:
                    # Convert relative URLs to absolute
                    if url.startswith('/'):
                        full_url = urljoin(self.base_url, url)
                    elif url.startswith('http'):
                        full_url = url
                    else:
                        continue
                    
                    # Filter for high-resolution images
                    if not self._is_high_res_image(full_url):
                        continue
                    
                    # Filter by model if provided
                    if make_filter and model_filter:
                        if not self._matches_model(full_url, make_filter, model_filter):
                            continue
                    
                    if full_url not in seen:
                        seen.add(full_url)
                        image_urls.append(full_url)
        
        # Also look for links that might point to images
        links = soup.find_all('a', href=True)
        for link in links:
            href = link.get('href', '')
            if self._is_image_url(href):
                if href.startswith('/'):
                    full_url = urljoin(self.base_url, href)
                elif href.startswith('http'):
                    full_url = href
                else:
                    continue
                
                # Filter by model if provided
                if make_filter and model_filter:
                    if not self._matches_model(full_url, make_filter, model_filter):
                        continue
                
                if full_url not in seen:
                    seen.add(full_url)
                    image_urls.append(full_url)
        
        # Sort by resolution (prefer larger images)
        image_urls = self._sort_by_resolution(image_urls)
        
        return image_urls
    
    def _matches_model(self, url: str, make: str, model: str) -> bool:
        """
        Check if image URL matches the specific make and model.
        Uses strict matching to avoid unrelated images.
        
        Args:
            url: Image URL
            make: Make name (normalized, e.g., "acura")
            model: Model name (normalized, e.g., "ilx")
            
        Returns:
            True if URL appears to be for this model
        """
        url_lower = url.lower()
        
        # Normalize make/model for matching (handle variations)
        make_variations = [make, make.replace('_', '-'), make.replace('-', '_')]
        model_variations = [model, model.replace('_', '-'), model.replace('-', '_')]
        
        # Check for make-model pattern in URL (strict matching)
        # Patterns like: Acura-ILX-2019, acura_ilx_2019, acura/ilx/, etc.
        # Must have BOTH make and model in URL
        make_found = False
        model_found = False
        
        # Check if make appears in URL
        for make_var in make_variations:
            # Check various patterns
            make_patterns = [
                f"/{make_var}/",
                f"/{make_var}-",
                f"/{make_var}_",
                f"{make_var}-",
                f"{make_var}_",
            ]
            for pattern in make_patterns:
                if pattern in url_lower:
                    make_found = True
                    break
            if make_found:
                break
        
        # Check if model appears in URL (must be near make or clearly identified)
        for model_var in model_variations:
            # Check various patterns - must be clearly the model
            model_patterns = [
                f"-{model_var}-",  # year-model-year or make-model-year
                f"-{model_var}_",
                f"-{model_var}/",
                f"_{model_var}-",
                f"_{model_var}_",
                f"_{model_var}/",
                f"/{model_var}-",
                f"/{model_var}_",
                f"/{model_var}/",
            ]
            for pattern in model_patterns:
                if pattern in url_lower:
                    model_found = True
                    break
            
            # Also check for capitalized versions
            model_cap = model_var.capitalize()
            model_upper = model_var.upper()
            for var in [model_var, model_cap, model_upper]:
                # Word boundary check - must be clearly the model
                pattern = r'[\/\-_]' + re.escape(var) + r'[\/\-_]'
                if re.search(pattern, url_lower, re.I):
                    model_found = True
                    break
            
            if model_found:
                break
        
        # Both make and model must be present for a match
        if make_found and model_found:
            return True
        
        # Fallback: check for combined make-model pattern
        for make_var in make_variations:
            for model_var in model_variations:
                combined_patterns = [
                    f"{make_var}-{model_var}",
                    f"{make_var}_{model_var}",
                    f"{make_var}/{model_var}",
                ]
                for pattern in combined_patterns:
                    if pattern in url_lower:
                        return True
        
        return False
    
    def _is_high_res_image(self, url: str) -> bool:
        """Check if URL points to a high-resolution image."""
        # Common high-res indicators in URLs
        high_res_patterns = [
            r'wallpaper',
            r'photo',
            r'image',
            r'hd',
            r'high',
            r'large',
            r'full',
            r'original',
            r'\.(jpg|jpeg|png|webp)',
        ]
        
        url_lower = url.lower()
        return any(re.search(pattern, url_lower, re.I) for pattern in high_res_patterns)
    
    def _is_image_url(self, url: str) -> bool:
        """Check if URL is an image URL."""
        image_extensions = ['.jpg', '.jpeg', '.png', '.gif', '.webp', '.bmp']
        url_lower = url.lower()
        return any(url_lower.endswith(ext) for ext in image_extensions) or 'image' in url_lower
    
    def _sort_by_resolution(self, urls: List[str]) -> List[str]:
        """
        Sort image URLs by resolution (prefer larger images).
        
        Args:
            urls: List of image URLs
            
        Returns:
            Sorted list with highest resolution first
        """
        def get_resolution_priority(url: str) -> int:
            """Return priority score (higher = better resolution)."""
            url_lower = url.lower()
            priority = 0
            
            # Check for resolution indicators
            if 'original' in url_lower or 'full' in url_lower:
                priority += 100
            if 'hd' in url_lower or 'high' in url_lower:
                priority += 50
            if 'large' in url_lower or 'big' in url_lower:
                priority += 30
            if 'medium' in url_lower:
                priority += 10
            if 'small' in url_lower or 'thumb' in url_lower:
                priority -= 20
            
            # Check for resolution numbers (e.g., 1920x1080, 4k)
            res_match = re.search(r'(\d+)x(\d+)', url_lower)
            if res_match:
                width = int(res_match.group(1))
                height = int(res_match.group(2))
                priority += (width * height) // 10000  # Scale to reasonable priority
            
            if '4k' in url_lower or '3840' in url_lower:
                priority += 80
            if '1080' in url_lower or '1920' in url_lower:
                priority += 40
            
            return priority
        
        return sorted(urls, key=get_resolution_priority, reverse=True)
    
    def get_next_gallery_page_url(self, html: str, current_url: str) -> Optional[str]:
        """
        Get the URL for the next page in gallery pagination.
        
        Args:
            html: HTML content of current gallery page
            current_url: URL of current gallery page
            
        Returns:
            URL of next gallery page or None if no next page
        """
        if not html:
            return None
        
        soup = BeautifulSoup(html, 'lxml')
        
        # Look for pagination links
        next_keywords = ['next', 'more', '>', 'show more']
        
        for link in soup.find_all('a', href=True):
            text = link.get_text().lower().strip()
            href = link.get('href', '')
            
            if any(keyword in text for keyword in next_keywords):
                if href.startswith('/'):
                    return urljoin(self.base_url, href)
                elif href.startswith('http'):
                    return href
        
        # Look for pagination navigation
        pagination = soup.find(['nav', 'div'], class_=re.compile(r'paginat|page', re.I))
        if pagination:
            next_link = pagination.find('a', string=re.compile(r'next|>', re.I))
            if next_link and next_link.get('href'):
                href = next_link.get('href')
                if href.startswith('/'):
                    return urljoin(self.base_url, href)
                elif href.startswith('http'):
                    return href
        
        return None
    
    def parse_all_gallery_pages(self, initial_html: str, initial_url: str, fetcher, 
                                make: str = None, model: str = None) -> List[str]:
        """
        Parse all pages of a gallery to get all images.
        
        Args:
            initial_html: HTML of first gallery page
            initial_url: URL of first gallery page
            fetcher: Fetcher instance to get additional pages
            make: Make name to filter images (e.g., "acura")
            model: Model name to filter images (e.g., "ilx")
            
        Returns:
            List of all image URLs from all gallery pages (filtered by model if provided)
        """
        all_images = []
        current_html = initial_html
        current_url = initial_url
        seen_urls = {current_url}
        
        # Parse first page
        images = self.parse_gallery_page(current_html, make=make, model=model)
        all_images.extend(images)
        
        # Follow pagination
        max_pages = 50  # Safety limit
        page_count = 0
        
        while page_count < max_pages:
            next_url = self.get_next_gallery_page_url(current_html, current_url)
            
            if not next_url or next_url in seen_urls:
                break
            
            seen_urls.add(next_url)
            page_count += 1
            
            # Fetch next page
            html, status, error = fetcher.fetch_url(next_url)
            if not html or error:
                break
            
            current_html = html
            current_url = next_url
            
            # Parse images from this page
            images = self.parse_gallery_page(current_html, make=make, model=model)
            all_images.extend(images)
        
        # Remove duplicates while preserving order
        seen_images = set()
        unique_images = []
        for img_url in all_images:
            if img_url not in seen_images:
                seen_images.add(img_url)
                unique_images.append(img_url)
        
        return unique_images

