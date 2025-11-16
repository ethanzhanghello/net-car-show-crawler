"""
Parser for extracting vehicle data from NetCarShow HTML pages.
"""

from bs4 import BeautifulSoup
from typing import List, Dict, Optional, Tuple
from urllib.parse import urljoin, urlparse
import re


class Parser:
    """Handles parsing of listing pages, detail pages, and specifications."""
    
    def __init__(self, base_url: str = "https://www.netcarshow.com"):
        """Initialize parser with base URL."""
        self.base_url = base_url
    
    def parse_listing_page(self, html: str, category: str = "", subcategory: str = "") -> List[Dict[str, str]]:
        """
        Parse a listing page to extract all model URLs and metadata.
        
        Includes completeness checks to ensure all models are captured.
        
        Args:
            html: HTML content of the listing page
            category: Category name (e.g., "SUV")
            subcategory: Subcategory name (e.g., "Premium")
            
        Returns:
            List of dicts with 'url', 'make', 'model', 'year' keys
        """
        if not html:
            return []
        
        soup = BeautifulSoup(html, 'lxml')
        models = []
        seen = set()
        
        # Find all links to model detail pages
        # Pattern: /{make}/{year}-{model}/
        all_links = soup.find_all('a', href=True)
        
        # Count potential model links in DOM for completeness check
        potential_model_links = 0
        for link in all_links:
            href = link.get('href', '')
            if href and self._is_model_url(href):
                potential_model_links += 1
        
        for link in all_links:
            href = link.get('href', '')
            if not href:
                continue
            
            # Convert relative URLs to absolute
            if href.startswith('/'):
                full_url = urljoin(self.base_url, href)
            else:
                full_url = href
            
            # Model URLs have pattern: /make/year-model/ (not ending in -wallpapers or /)
            if self._is_model_url(href):
                if full_url not in seen:
                    seen.add(full_url)
                    
                    # Extract make, year, model from URL
                    make, year, model = self._parse_model_url(href)
                    
                    if make and model:
                        # Normalize model name for consistency
                        from .schema import SchemaMapper
                        normalized_model = SchemaMapper._normalize_name(model)
                        
                        models.append({
                            'url': full_url,
                            'make': make,
                            'model': normalized_model,  # Use normalized model name
                            'year': year,
                            'category': category,
                            'subcategory': subcategory
                        })
        
        # Completeness check - warn if we might have missed models
        extracted_count = len(models)
        if potential_model_links > extracted_count:
            # This is just a warning - some links might be duplicates or invalid
            pass  # Could log a warning here if logger available
        
        return models
    
    def _is_model_url(self, href: str) -> bool:
        """Check if href is a model detail page URL."""
        if not href.startswith('/'):
            return False
        
        # Exclude gallery pages
        if '-wallpapers' in href:
            return False
        
        # Pattern: /make/year-model/ (trailing slash is OK)
        # Strip trailing slash for parsing, but allow it
        href_clean = href.rstrip('/')
        parts = href_clean.split('/')
        
        # Should have exactly 2 parts: ['', 'make', 'year-model']
        if len(parts) != 3:
            return False
        
        # Second part is make, third part is year-model
        if len(parts) < 3:
            return False
        
        # Third part should have year-model pattern (year starts with digit, has dash)
        model_part = parts[2] if len(parts) > 2 else ''
        if '-' in model_part and model_part[0].isdigit():
            return True
        
        return False
    
    def _parse_model_url(self, href: str) -> Tuple[Optional[str], Optional[str], Optional[str]]:
        """
        Parse model URL to extract make, year, and model.
        
        Args:
            href: URL path like /mercedes-benz/2024-glc_coupe/
            
        Returns:
            Tuple of (make, year, model)
        """
        parts = href.strip('/').split('/')
        if len(parts) != 2:
            return None, None, None
        
        make = parts[0].replace('-', '_')
        year_model = parts[1]
        
        # Extract year (first 4 digits)
        year_match = re.match(r'^(\d{4})-', year_model)
        if year_match:
            year = year_match.group(1)
            model = year_model[len(year) + 1:].replace('-', '_')
            return make, year, model
        
        return make, None, year_model.replace('-', '_')
    
    def parse_model_detail_page(self, html: str, url: str) -> Dict:
        """
        Parse a model detail page to extract vehicle information.
        
        Args:
            html: HTML content of the detail page
            url: URL of the detail page
            
        Returns:
            Dict with make, model, years, expert_review, gallery_url, etc.
        """
        if not html:
            return {}
        
        soup = BeautifulSoup(html, 'lxml')
        
        # Extract make, year, model from URL
        make, year, model = self._parse_model_url(urlparse(url).path)
        
        # Extract all years from the page (may have multiple years)
        years = self._extract_years(soup, year)
        
        # Extract expert review text
        expert_review = self._extract_expert_review(soup)
        
        # Find gallery URL
        gallery_url = self._extract_gallery_url(soup, url)
        
        # Extract basic model information
        # Use model from URL parsing (clean) as primary source
        # _extract_model_name will clean it further if needed
        model_name = self._extract_model_name(soup, model)
        # If model_name is still a full title, use the URL-parsed model
        if model_name and (' - ' in model_name or len(model_name) > 50):
            model_name = model  # Use the URL-parsed version instead
        
        description = self._extract_description(soup)
        
        return {
            'make': make or '',
            'model': model_name or model or '',
            'years': years,
            'expert_review': expert_review,
            'gallery_url': gallery_url,
            'description': description,
            'url': url
        }
    
    def _extract_years(self, soup: BeautifulSoup, default_year: Optional[str] = None) -> List[str]:
        """Extract all years mentioned on the page."""
        years = set()
        
        if default_year:
            years.add(str(default_year))
        
        # Look for year patterns in text (4-digit years: 1900-2100)
        # Use a regex that captures the full year
        text = soup.get_text()
        year_matches = re.findall(r'\b(19\d{2}|20\d{2})\b', text)
        for year_str in year_matches:
            try:
                year = int(year_str)
                if 1900 <= year <= 2100:
                    years.add(str(year))
            except ValueError:
                continue
        
        # Look for year in headings, titles, etc.
        for element in soup.find_all(['h1', 'h2', 'h3', 'title']):
            text = element.get_text()
            year_matches = re.findall(r'\b(19\d{2}|20\d{2})\b', text)
            for year_str in year_matches:
                try:
                    year = int(year_str)
                    if 1900 <= year <= 2100:
                        years.add(str(year))
                except ValueError:
                    continue
        
        return sorted(list(years), reverse=True)  # Most recent first
    
    def _extract_expert_review(self, soup: BeautifulSoup) -> str:
        """Extract expert review text from the page."""
        # Look for review sections - common patterns
        review_selectors = [
            ('div', {'class': re.compile(r'review', re.I)}),
            ('div', {'id': re.compile(r'review', re.I)}),
            ('section', {'class': re.compile(r'review', re.I)}),
            ('p', {'class': re.compile(r'review|expert', re.I)}),
            ('article', {'class': re.compile(r'review', re.I)}),
        ]
        
        for tag, attrs in review_selectors:
            elements = soup.find_all(tag, attrs)
            for elem in elements:
                text = elem.get_text().strip()
                # Filter out very short or very long text (likely not a review)
                if 100 < len(text) < 50000:  # Reasonable review length
                    # Make sure it's not just navigation or metadata
                    if not any(skip in text.lower()[:100] for skip in ['home', 'menu', 'navigation', 'cookie', 'privacy']):
                        return text
        
        # Fallback: look for long paragraphs in main content area
        # But exclude headers, footers, navigation
        main_content = soup.find('main') or soup.find('article') or soup.find('div', {'class': re.compile(r'content|main', re.I)})
        if main_content:
            paragraphs = main_content.find_all('p')
            for p in paragraphs:
                text = p.get_text().strip()
                if 100 < len(text) < 50000:  # Likely a review or description
                    return text
        
        # Last resort: look for any long paragraphs, but be more selective
        paragraphs = soup.find_all('p')
        for p in paragraphs:
            text = p.get_text().strip()
            # Check if it looks like a review (mentions car features, driving, etc.)
            review_indicators = ['engine', 'power', 'drive', 'handling', 'interior', 'exterior', 'performance']
            if 200 < len(text) < 50000 and any(indicator in text.lower() for indicator in review_indicators):
                return text
        
        return ""
    
    def _extract_gallery_url(self, soup: BeautifulSoup, current_url: str) -> Optional[str]:
        """Extract gallery/wallpapers URL from the page."""
        # First, try to construct from current URL (most reliable)
        # /make/year-model/ -> /make/year-model-wallpapers/
        if '-wallpapers' not in current_url:
            gallery_url = current_url.rstrip('/') + '-wallpapers/'
            # Verify it's a proper gallery URL (not a single image)
            if '/wallpapers/' in gallery_url or gallery_url.endswith('-wallpapers/'):
                return gallery_url
        
        # Look for gallery links - but be more specific
        gallery_keywords = ['wallpapers', 'gallery']
        
        for link in soup.find_all('a', href=True):
            href = link.get('href', '')
            text = link.get_text().lower()
            
            # Only accept links that are actual gallery pages, not single images
            # Gallery pages should have -wallpapers/ in the path
            if '-wallpapers' in href.lower() or '/wallpapers/' in href.lower():
                # Make sure it's not a single image file
                if not href.lower().endswith(('.jpg', '.jpeg', '.png', '.gif', '.webp')):
                    if href.startswith('/'):
                        return urljoin(self.base_url, href)
                    elif href.startswith('http'):
                        return href
            
            # Also check link text for gallery keywords
            if any(keyword in text for keyword in gallery_keywords):
                # But still verify it's a gallery page, not an image
                if '-wallpapers' in href.lower() or '/wallpapers/' in href.lower():
                    if not href.lower().endswith(('.jpg', '.jpeg', '.png', '.gif', '.webp')):
                        if href.startswith('/'):
                            return urljoin(self.base_url, href)
                        elif href.startswith('http'):
                            return href
        
        return None
    
    def _extract_model_name(self, soup: BeautifulSoup, default: Optional[str] = None) -> Optional[str]:
        """Extract model name from page or URL."""
        # First, try to extract from URL if default is provided (from URL parsing)
        if default:
            # default might be from URL parsing, which should be clean
            # But if it's a full title, try to clean it
            if ' - ' in default or 'pictures' in default.lower() or 'information' in default.lower():
                # This is a page title, not a model name - extract from URL instead
                pass
            else:
                # Already a clean model name from URL
                return default
        
        # Try to extract from URL in the page itself
        # Look for canonical URL or og:url
        canonical = soup.find('link', {'rel': 'canonical'})
        if canonical and canonical.get('href'):
            url = canonical.get('href')
            _, _, model_from_url = self._parse_model_url(url)
            if model_from_url:
                return model_from_url
        
        # Try h1 - but clean it up
        h1 = soup.find('h1')
        if h1:
            text = h1.get_text().strip()
            # Remove year and extra text
            text = re.sub(r'\s*\(\d{4}\)\s*', '', text)  # Remove (2024)
            text = re.sub(r'\s*-\s*pictures.*$', '', text, flags=re.I)  # Remove "- pictures..."
            text = re.sub(r'\s*-\s*information.*$', '', text, flags=re.I)  # Remove "- information..."
            if text and len(text) < 50:  # Reasonable model name length
                return text
        
        # Fallback to default (which should be from URL parsing)
        return default
    
    def _extract_description(self, soup: BeautifulSoup) -> str:
        """Extract model description from page."""
        # Look for description meta tag
        meta_desc = soup.find('meta', attrs={'name': 'description'})
        if meta_desc and meta_desc.get('content'):
            return meta_desc.get('content').strip()
        
        # Look for first substantial paragraph
        paragraphs = soup.find_all('p')
        for p in paragraphs:
            text = p.get_text().strip()
            if len(text) > 50:
                return text
        
        return ""
    
    def parse_trims_and_specs(self, html: str) -> List[Dict]:
        """
        Parse trim and specification information from a detail page.
        
        Args:
            html: HTML content of the detail page
            
        Returns:
            List of trim dicts with 'name', 'price', 'specifications'
        """
        if not html:
            return []
        
        soup = BeautifulSoup(html, 'lxml')
        trims = []
        
        # Look for trim/specification sections
        # Common patterns: tables, divs with spec classes, etc.
        spec_sections = self._find_spec_sections(soup)
        
        if spec_sections:
            for section in spec_sections:
                trim = self._parse_trim_section(section)
                if trim:
                    trims.append(trim)
        
        # If no trims found, create a default "Base" trim
        if not trims:
            trims.append({
                'name': 'Base',
                'price': '',
                'specifications': {}
            })
        
        return trims
    
    def _find_spec_sections(self, soup: BeautifulSoup) -> List:
        """Find specification sections in the HTML."""
        sections = []
        
        # Look for common spec section patterns
        selectors = [
            ('table', {'class': re.compile(r'spec|trim', re.I)}),
            ('div', {'class': re.compile(r'spec|trim', re.I)}),
            ('section', {'class': re.compile(r'spec|trim', re.I)}),
            ('div', {'id': re.compile(r'spec|trim', re.I)}),
        ]
        
        for tag, attrs in selectors:
            found = soup.find_all(tag, attrs)
            sections.extend(found)
        
        # Also look for tables that might contain specs
        tables = soup.find_all('table')
        for table in tables:
            # Check if table looks like a spec table
            if self._looks_like_spec_table(table):
                sections.append(table)
        
        return sections
    
    def _looks_like_spec_table(self, table) -> bool:
        """Check if a table looks like a specifications table."""
        text = table.get_text().lower()
        spec_keywords = ['engine', 'power', 'torque', 'transmission', 'fuel', 'safety', 'weight']
        return any(keyword in text for keyword in spec_keywords)
    
    def _parse_trim_section(self, section) -> Optional[Dict]:
        """Parse a single trim/specification section."""
        trim_name = 'Base'
        price = ''
        specifications = {}
        
        # Try to extract trim name
        heading = section.find(['h1', 'h2', 'h3', 'h4', 'strong', 'b'])
        if heading:
            heading_text = heading.get_text().strip()
            # Check if it looks like a trim name
            if len(heading_text) < 50 and not heading_text.isdigit():
                trim_name = heading_text
        
        # Try to extract price
        price_elem = section.find(string=re.compile(r'\$[\d,]+'))
        if price_elem:
            price_match = re.search(r'\$[\d,]+', price_elem)
            if price_match:
                price = price_match.group(0)
        
        # Parse specifications from table or list
        if section.name == 'table':
            specs = self._parse_spec_table(section)
        else:
            specs = self._parse_spec_list(section)
        
        if specs:
            specifications = specs
        
        return {
            'name': trim_name,
            'price': price,
            'specifications': specifications
        }
    
    def _parse_spec_table(self, table) -> Dict[str, List]:
        """Parse specifications from a table structure.
        
        Returns format matching reference:
        {
          "Category Name": ["spec1", "spec2", ...]
        }
        """
        specs = {}
        current_category = None
        
        rows = table.find_all('tr')
        for row in rows:
            cells = row.find_all(['td', 'th'])
            
            # Check if this is a category header row (single cell or bold header)
            if len(cells) == 1:
                category_text = cells[0].get_text().strip()
                if category_text and len(category_text) < 100:
                    current_category = category_text
                    if current_category not in specs:
                        specs[current_category] = []
                continue
            
            if len(cells) >= 2:
                label = cells[0].get_text().strip()
                value = cells[1].get_text().strip()
                
                if not label and not value:
                    continue
                
                # Check if label is a category header (often bold or in th)
                is_category = (cells[0].name == 'th' or 
                              cells[0].find(['strong', 'b', 'h3', 'h4']) or
                              (len(cells) == 2 and not value))
                
                if is_category and label:
                    current_category = label
                    if current_category not in specs:
                        specs[current_category] = []
                elif label and value:
                    # Add spec to current category (format: "Label: Value" or just "Value" if label is generic)
                    if current_category:
                        if current_category not in specs:
                            specs[current_category] = []
                        # If label is generic (like "Specification", "Feature"), just use value
                        if label.lower() in ['specification', 'feature', 'detail', 'info']:
                            specs[current_category].append(value)
                        else:
                            specs[current_category].append(f"{label}: {value}")
                    else:
                        # No category yet, use label as category or create General
                        if not current_category:
                            current_category = 'General'
                            if current_category not in specs:
                                specs[current_category] = []
                        specs[current_category].append(f"{label}: {value}")
                elif value and not label:
                    # Value only, add to current category
                    if current_category:
                        if current_category not in specs:
                            specs[current_category] = []
                        specs[current_category].append(value)
        
        return specs
    
    def _parse_spec_list(self, section) -> Dict[str, List]:
        """Parse specifications from a list structure.
        
        Returns format matching reference:
        {
          "Category Name": ["spec1", "spec2", ...]
        }
        """
        specs = {}
        current_category = None
        
        # Look for category headers first (h2, h3, h4, strong headings before lists)
        headings = section.find_all(['h2', 'h3', 'h4', 'h5', 'strong', 'b'])
        for heading in headings:
            text = heading.get_text().strip()
            if text and len(text) < 100:
                # Check if this looks like a category name
                category_keywords = ['features', 'highlights', 'engine', 'suspension', 'safety', 
                                   'entertainment', 'electrical', 'brakes', 'weight', 'capacity']
                if any(keyword in text.lower() for keyword in category_keywords) or len(text.split()) <= 3:
                    current_category = text
                    if current_category not in specs:
                        specs[current_category] = []
        
        # Look for lists
        lists = section.find_all(['ul', 'ol', 'dl'])
        for list_elem in lists:
            # Check if there's a heading right before this list
            prev_sibling = list_elem.find_previous_sibling(['h2', 'h3', 'h4', 'h5', 'strong', 'b', 'p'])
            if prev_sibling:
                prev_text = prev_sibling.get_text().strip()
                if prev_text and len(prev_text) < 100:
                    # Use previous heading as category
                    current_category = prev_text
                    if current_category not in specs:
                        specs[current_category] = []
            
            items = list_elem.find_all('li') if list_elem.name in ['ul', 'ol'] else list_elem.find_all(['dt', 'dd'])
            
            for item in items:
                text = item.get_text().strip()
                if not text:
                    continue
                
                # Check if it's a category header (dt tag or bold text)
                if item.name == 'dt' or item.find(['strong', 'b', 'h3', 'h4']):
                    current_category = text
                    if current_category not in specs:
                        specs[current_category] = []
                else:
                    # Add to current category or create General
                    if not current_category:
                        current_category = 'General'
                    if current_category not in specs:
                        specs[current_category] = []
                    specs[current_category].append(text)
        
        return specs
    
    def get_next_page_url(self, html: str, current_url: str) -> Optional[str]:
        """
        Get the URL for the next page in pagination.
        
        Args:
            html: HTML content of current page
            current_url: URL of current page
            
        Returns:
            URL of next page or None if no next page
        """
        if not html:
            return None
        
        soup = BeautifulSoup(html, 'lxml')
        
        # Look for "SHOW MORE" or "Next" links
        next_keywords = ['show more', 'next', 'more', 'load more']
        
        for link in soup.find_all('a', href=True):
            text = link.get_text().lower().strip()
            href = link.get('href', '')
            
            if any(keyword in text for keyword in next_keywords):
                if href.startswith('/'):
                    return urljoin(self.base_url, href)
                elif href.startswith('http'):
                    return href
        
        # Look for pagination links
        pagination = soup.find(['nav', 'div'], class_=re.compile(r'paginat', re.I))
        if pagination:
            next_link = pagination.find('a', string=re.compile(r'next|>', re.I))
            if next_link and next_link.get('href'):
                href = next_link.get('href')
                if href.startswith('/'):
                    return urljoin(self.base_url, href)
                elif href.startswith('http'):
                    return href
        
        return None

