"""
Image gallery parser for extracting high-resolution images from NetCarShow gallery pages.
"""

from bs4 import BeautifulSoup
from typing import List, Optional, Dict
from urllib.parse import urljoin
import json
import re


THZ_ARRAY_REGEX = re.compile(r"var\s+thz\s*=\s*(\[[^\]]*\]);", re.S)
THZ_MO_REGEX = re.compile(r"var\s+thzMo\s*=\s*'([^']+)';")
THZ_U_REGEX = re.compile(r"var\s+thU\s*=\s*'([^']+)';")


class GalleryParser:
    """Handles parsing of gallery pages to extract image URLs."""
    
    def __init__(self, base_url: str = "https://www.netcarshow.com"):
        """Initialize gallery parser with base URL."""
        self.base_url = base_url
    
    def parse_gallery_page(self, html: str, make: str = None, model: str = None, year: str = None) -> List[str]:
        """
        Parse a gallery page to extract all high-resolution image URLs.
        
        NOTE: When year=None, this gathers ALL images matching make/model.
        Year filtering happens later in parse_all_gallery_pages() after all pages are gathered.
        
        Args:
            html: HTML content of the gallery page
            make: Make name to filter images (e.g., "acura")
            model: Model name to filter images (e.g., "ilx")
            year: Year to filter (if None, gathers all years for this make/model)
            
        Returns:
            List of image URLs (filtered by make/model, optionally by year)
        """
        if not html:
            return []
        
        soup = BeautifulSoup(html, 'lxml')
        image_urls = []
        seen = set()
        
        # Normalize make and model for filtering
        make_filter = make.lower().replace('_', '-') if make else None
        model_filter = model.lower().replace('_', '-') if model else None
        
        # Find all image tags - gather ALL images first
        img_tags = soup.find_all('img')
        for img in img_tags:
            # Try different attributes for image URLs
            for attr in ['src', 'data-src', 'data-lazy-src', 'data-original', 'data-full']:
                url = img.get(attr)
                if url:
                    # Convert relative URLs to absolute
                    if url.startswith('/'):
                        full_url = urljoin(self.base_url, url)
                    elif url.startswith('http'):
                        full_url = url
                    else:
                        continue
                    
                    # Check if it's an image URL (must end with image extension or be in /R/ directory)
                    if not (self._is_image_url(full_url) or '/R/' in full_url):
                        continue
                    
                    # Gather ALL images - don't filter by resolution during gathering
                    # We want to collect everything, then filter by year afterward
                    
                    # Filter by make and model ONLY (year filtering happens later)
                    if make_filter and model_filter:
                        if not self._matches_model(full_url, make_filter, model_filter, year=None):
                            continue
                    
                    if full_url not in seen:
                        seen.add(full_url)
                        image_urls.append(full_url)
        
        # Also look for links that might point to images
        links = soup.find_all('a', href=True)
        for link in links:
            href = link.get('href', '')
            # Check if it's an image URL or points to /R/ directory
            if self._is_image_url(href) or '/R/' in href.lower():
                if href.startswith('/'):
                    full_url = urljoin(self.base_url, href)
                elif href.startswith('http'):
                    full_url = href
                else:
                    continue
                
                # Filter by make and model ONLY (year filtering happens later)
                if make_filter and model_filter:
                    if not self._matches_model(full_url, make_filter, model_filter, year=None):
                        continue
                
                if full_url not in seen:
                    seen.add(full_url)
                    image_urls.append(full_url)
        
        # Also look for images in /R/ directory pattern: /R/{Make}-{Model}-{Year}-...
        # Extract all URLs that match the pattern from the HTML
        html_text = str(soup)
        # Pattern: /R/{make}-{model}-{year}-{suffix}.jpg
        if make_filter and model_filter:
            # Look for /R/ URLs in the HTML - match full URLs
            # Pattern: /R/Make-Model-Year-suffix.jpg or /R/Make-Model-Year-suffix-ec-...
            r_pattern = rf'/R/[^"\'<> ]*{re.escape(make_filter)}[^"\'<> ]*{re.escape(model_filter)}[^"\'<> ]*\.(jpg|jpeg|png|gif|webp)'
            r_matches = re.finditer(r_pattern, html_text, re.I)
            for match in r_matches:
                url_part = match.group(0)  # Get the full matched URL
                
                if url_part.startswith('/'):
                    full_url = urljoin(self.base_url, url_part)
                elif url_part.startswith('http'):
                    full_url = url_part
                else:
                    continue
                
                if full_url not in seen and self._matches_model(full_url, make_filter, model_filter, year=None):
                    seen.add(full_url)
                    image_urls.append(full_url)
        
        # Sort by resolution (prefer larger images)
        image_urls = self._sort_by_resolution(image_urls)
        
        return image_urls
    
    def _matches_model(self, url: str, make: str, model: str, year: str = None) -> bool:
        """
        Check if image URL matches the specific make, model, and year.
        Uses strict matching to avoid unrelated images from other years.
        
        Args:
            url: Image URL
            make: Make name (normalized, e.g., "acura")
            model: Model name (normalized, e.g., "ilx")
            year: Year to match (e.g., "2019") - if provided, URL must contain this year
            
        Returns:
            True if URL appears to be for this model and year
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
        if not (make_found and model_found):
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
                            make_found = True
                            model_found = True
                            break
                    if make_found and model_found:
                        break
                if make_found and model_found:
                    break
        
        # If year is provided, URL must contain the year (strict matching)
        if year:
            year_str = str(year).strip()
            # Check for year in URL - must be present
            # Patterns: -2019-, _2019_, -2019.jpg, _2019.jpg, /2019/, etc.
            year_patterns = [
                f"-{year_str}-",
                f"-{year_str}_",
                f"-{year_str}.",
                f"-{year_str}/",
                f"_{year_str}-",
                f"_{year_str}_",
                f"_{year_str}.",
                f"_{year_str}/",
                f"/{year_str}-",
                f"/{year_str}_",
                f"/{year_str}/",
            ]
            year_found = any(pattern in url_lower for pattern in year_patterns)
            
            # Also check for year at start/end of filename
            if not year_found:
                # Check if year appears before file extension
                year_at_end = re.search(rf'{re.escape(year_str)}\.[a-z]{{3,4}}$', url_lower)
                if year_at_end:
                    year_found = True
            
            # If year is required but not found, reject this image
            if not year_found:
                return False
        
        # All required matches found
        return make_found and model_found
    
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
                                make: str = None, model: str = None, year: str = None) -> List[str]:
        """
        Parse all pages of a gallery to get all images.
        
        IMPORTANT: Gathers ALL images first, then filters by year afterward.
        This ensures we don't miss any images that might be on later pages.
        
        Args:
            initial_html: HTML of first gallery page
            initial_url: URL of first gallery page
            fetcher: Fetcher instance to get additional pages
            make: Make name to filter images (e.g., "acura")
            model: Model name to filter images (e.g., "ilx")
            year: Year to filter images (e.g., "2019") - filters AFTER gathering all images
            
        Returns:
            List of all image URLs from all gallery pages (filtered by make, model, and year)
        """
        # STEP 1: Gather ALL images from all gallery pages (no year filtering yet)
        all_images = []
        current_html = initial_html
        current_url = initial_url
        seen_urls = {current_url}
        
        # Parse first page - gather all images without year filter
        images = self.parse_gallery_page(current_html, make=make, model=model, year=None)
        all_images.extend(images)
        
        # Follow pagination to get all pages
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
            
            # Parse images from this page - gather all without year filter
            images = self.parse_gallery_page(current_html, make=make, model=model, year=None)
            all_images.extend(images)
        
        # Remove duplicates while preserving order
        seen_images = set()
        unique_images = []
        for img_url in all_images:
            if img_url not in seen_images:
                seen_images.add(img_url)
                unique_images.append(img_url)
        
        return self.filter_images_by_year(unique_images, year)

    def filter_images_by_year(self, images: List[str], year: Optional[str]) -> List[str]:
        """
        Filter a list of image URLs by year (strict match).
        
        Args:
            images: List of image URLs
            year: Year to filter by (e.g., "2019")
            
        Returns:
            Filtered list of image URLs matching the year
        """
        if not year or not images:
            return images or []
        
        year_str = str(year).strip()
        filtered_images = []
        
        for img_url in images:
            url_lower = img_url.lower()
            
            year_patterns = [
                f"-{year_str}-",
                f"-{year_str}.",
                f"-{year_str}_",
                f"_{year_str}-",
                f"_{year_str}.",
                f"_{year_str}_",
                f"/{year_str}-",
                f"/{year_str}_",
                f"/{year_str}/",
            ]
            
            year_found = any(pattern in url_lower for pattern in year_patterns)
            
            if not year_found:
                year_at_end = re.search(rf'{re.escape(year_str)}\.[a-z]{{3,4}}$', url_lower)
                if year_at_end:
                    year_found = True
            
            if year_found:
                filtered_images.append(img_url)
        
        return filtered_images

    def extract_images_from_detail(
        self,
        html: str,
        page_url: str = "",
        fetcher=None,
        year: Optional[str] = None
    ) -> List[str]:
        """
        Extract gallery images by decoding inline thumbnail metadata on detail pages.
        
        Args:
            html: Detail page HTML
            page_url: URL of the detail page (used as referer for JSON calls)
            fetcher: Fetcher instance for additional JSON lookups
            year: Year to filter images
        
        Returns:
            List of high-resolution image URLs derived from inline metadata
        """
        if not html:
            return []
        
        config = self._parse_inline_gallery_config(html)
        if not config:
            return []
        
        thz = config.get('thz') or []
        thz_mo = config.get('thz_mo', '')
        th_u = config.get('th_u', '')
        
        if thz and thz[-1] == 'hh':
            extra = self._fetch_additional_thz(th_u, fetcher, page_url)
            if extra:
                thz = extra
        
        thz = [entry for entry in thz if entry and entry != 'hh']
        if not thz or not thz_mo:
            return []
        
        image_urls = self._build_image_urls_from_thz(thz, thz_mo)
        image_urls = self.filter_images_by_year(image_urls, year)
        
        deduped = []
        seen = set()
        for url in image_urls:
            if url not in seen:
                seen.add(url)
                deduped.append(url)
        
        return deduped
    
    def _parse_inline_gallery_config(self, html: str) -> Optional[Dict[str, List[str]]]:
        thz_match = THZ_ARRAY_REGEX.search(html)
        if not thz_match:
            return None
        
        try:
            thz = json.loads(thz_match.group(1))
        except json.JSONDecodeError:
            return None
        
        thz_mo_match = THZ_MO_REGEX.search(html)
        th_u_match = THZ_U_REGEX.search(html)
        
        return {
            'thz': thz,
            'thz_mo': thz_mo_match.group(1) if thz_mo_match else '',
            'th_u': th_u_match.group(1) if th_u_match else ''
        }
    
    def _fetch_additional_thz(self, th_u: str, fetcher, page_url: str = "") -> Optional[List[str]]:
        if not fetcher or not th_u:
            return None
        
        url_key = self._reverse_and_lower(th_u)
        url = f"{self.base_url}/th.{url_key}.json"
        headers = {'X-RCC': '21'}
        if page_url:
            headers['Referer'] = page_url
        
        html, status, error = fetcher.fetch_url(url, headers=headers)
        if error or not html:
            return None
        
        try:
            data = json.loads(html.strip())
        except json.JSONDecodeError:
            return None
        
        if isinstance(data, list):
            return data
        if isinstance(data, dict):
            for key in ('thz', 'items', 'data'):
                value = data.get(key)
                if isinstance(value, list):
                    return value
        return None
    
    def _build_image_urls_from_thz(self, thz: List[str], thz_mo: str) -> List[str]:
        urls = []
        for idx, entry in enumerate(thz, 1):
            slug = self._gfnk(entry)
            token = self._gfnt(entry)
            url = f"{self.base_url}/{thz_mo}-1280-{slug}.jpg"
            if token:
                url = f"{url}?token={token}"
            urls.append(url)
        return urls
    
    @staticmethod
    def _reverse_and_lower(value: str) -> str:
        return value[::-1].lower() if value else ""
    
    def _gfnk(self, entry: str) -> str:
        chars = []
        n = 0
        while n < len(entry) and len(chars) < 34:
            chars.append(entry[n])
            n += 2
        return self._reverse_and_lower(''.join(chars))
    
    def _gfnt(self, entry: str, np_h: int = 0, np_v: int = 0) -> str:
        out = []
        n = 1
        length_tracker = 0
        while n < len(entry):
            if length_tracker == 45:
                out.append(f"{np_h:x}{np_v:x}")
                n += 1
                length_tracker += 2
            else:
                out.append(entry[n])
                length_tracker += 1
            n += 1
            if n < 68:
                n += 1
        return ''.join(out)

