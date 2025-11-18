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
        
        # If no trims found, extract specifications from text content
        if not trims or (len(trims) == 1 and not trims[0].get('specifications')):
            # Extract specifications from the main content area
            specs = self._extract_specs_from_text(soup)
            
            # Create a default "Base" trim with extracted specs
            trim = {
                'name': 'Base',
                'price': '',
                'specifications': specs if specs else {}
            }
            
            # If we already have a trim but no specs, add the extracted specs
            if trims and not trims[0].get('specifications'):
                trims[0]['specifications'] = specs if specs else {}
            elif not trims:
                trims.append(trim)
        
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
    
    def _extract_specs_from_text(self, soup: BeautifulSoup) -> Dict[str, List]:
        """
        Extract specifications from unstructured prose text on netcarshow.com pages.
        
        NOTE: NetCarShow.com does not have structured specification tables like cars.com.
        However, some pages have structured lists (<ul><li>) that can be extracted more reliably.
        Specifications are also embedded in prose text that varies significantly by model.
        This method extracts what it can using pattern matching, but results will be
        limited and inconsistent compared to structured sources.
        
        Returns format matching reference:
        {
          "Category Name": ["spec1", "spec2", ...]
        }
        """
        specs = {}
        
        # Find main content area
        main_content = soup.find('div', class_='a-b') or soup.find('main') or soup.find('article') or soup.find('div', class_=re.compile(r'content|main', re.I))
        if not main_content:
            return specs
        
        text_content = main_content.get_text()
        
        # FIRST: Extract from structured lists (<ul><li>) - these are more reliable
        list_specs = self._extract_from_structured_lists(main_content)
        specs = self._merge_spec_dicts(specs, list_specs)
        
        # THEN: Extract from prose text using pattern matching and MERGE (don't overwrite)
        prose_specs = {
            'Notable features': self._extract_features(text_content, main_content),
            'Highlights': self._extract_highlights(text_content, main_content),
            'Engine': self._extract_engine_specs(text_content, main_content),
            'Suspension': self._extract_suspension_specs(text_content, main_content),
            'Weight & Capacity': self._extract_weight_capacity(text_content, main_content),
            'Safety': self._extract_safety_features(text_content, main_content),
            'Entertainment': self._extract_entertainment_features(text_content, main_content),
            'Electrical': self._extract_electrical_specs(text_content, main_content),
            'Brakes': self._extract_brake_specs(text_content, main_content),
        }
        specs = self._merge_spec_dicts(specs, prose_specs)
        
        # Capture additional label/value style specs found in paragraphs or bullet lists
        label_specs = self._extract_label_value_specs(main_content)
        specs = self._merge_spec_dicts(specs, label_specs)
        
        # Remove empty categories
        specs = {k: v for k, v in specs.items() if v}
        
        return specs
    
    def _extract_from_structured_lists(self, main_content) -> Dict[str, List[str]]:
        """
        Extract specifications from structured <ul><li> lists in the HTML.
        These are more reliable than prose text extraction.
        """
        specs = {}
        if not main_content:
            return specs
        
        # Find all lists in the main content (including nested ones)
        lists = main_content.find_all('ul', recursive=True)
        
        for ul in lists:
            # Skip navigation lists and other non-spec lists
            if ul.get('class'):
                classes = ' '.join(ul.get('class', []))
                if any(skip in classes.lower() for skip in ['nav', 'menu', 'swbx', 'shl', 'tmsm', 'navlist']):
                    continue
            
            # Skip if this list is inside navigation/menu structures
            parent = ul.find_parent(['nav', 'header', 'footer'])
            if parent:
                continue
            
            # Get the heading before this list (often indicates category)
            category = None
            # Look for headings in previous siblings or parents
            prev = ul.find_previous(['h2', 'h3', 'h4', 'strong', 'b'])
            if not prev:
                # Also check parent for headings
                parent = ul.find_parent(['div', 'section', 'article'])
                if parent:
                    heading = parent.find(['h2', 'h3', 'h4', 'strong', 'b'])
                    if heading:
                        prev = heading
            
            if prev:
                prev_text = prev.get_text().strip()
                # Check if it's a category heading
                category_keywords = {
                    'new': 'Highlights',
                    'summary': 'Highlights',
                    "what's new": 'Highlights',
                    'feature': 'Notable features',
                    'spec': 'Notable features',
                    'safety': 'Safety',
                    'technology': 'Entertainment',
                    'interior': 'Notable features',
                    'exterior': 'Notable features',
                    'engine': 'Engine',
                    'performance': 'Engine',
                    'a-spec': 'Notable features',
                }
                for keyword, cat in category_keywords.items():
                    if keyword in prev_text.lower():
                        category = cat
                        break
            
            # Extract list items (both direct and nested)
            items = ul.find_all('li', recursive=False)
            if not items:
                # Try nested items if no direct items found
                items = ul.find_all('li', recursive=True)
            
            for li in items:
                text = li.get_text().strip()
                if not text or len(text) < 3:
                    continue
                
                # Skip very long items (likely not specs) but allow up to 300 chars for some features
                if len(text) > 300:
                    continue
                
                # Skip items that are clearly navigation or metadata
                if any(skip in text.lower()[:50] for skip in ['show more', 'read more', 'next', 'previous', 'home']):
                    continue
                
                # Determine category for this item
                item_category = category or self._infer_category_from_label(text) or 'Notable features'
                
                # Clean up the text
                text = re.sub(r'\s+', ' ', text)
                text = re.sub(r'\s*[•·]\s*', '', text)  # Remove bullet characters
                
                # Add to specs
                self._add_spec_entry(specs, item_category, text)
        
        return specs

    def _normalize_spec_text(self, text: str) -> str:
        if not text:
            return ''
        text = re.sub(r'\s+', ' ', text)
        return text.strip()

    def _add_spec_entry(self, specs: Dict[str, List[str]], category: str, value: str):
        category = (category or '').strip()
        value = self._normalize_spec_text(value)
        if not category or not value:
            return
        if category not in specs:
            specs[category] = []
        if value not in specs[category]:
            specs[category].append(value)

    def _standardize_category_name(self, heading: str) -> Optional[str]:
        if not heading:
            return None
        key = heading.lower().strip()
        mapping = [
            ('engine', 'Engine'),
            ('powertrain', 'Engine'),
            ('motor', 'Engine'),
            ('performance', 'Highlights'),
            ('fuel', 'Highlights'),
            ('economy', 'Highlights'),
            ('drivetrain', 'Highlights'),
            ('transmission', 'Highlights'),
            ('suspension', 'Suspension'),
            ('chassis', 'Suspension'),
            ('weight', 'Weight & Capacity'),
            ('capacity', 'Weight & Capacity'),
            ('dimension', 'Weight & Capacity'),
            ('cargo', 'Weight & Capacity'),
            ('safety', 'Safety'),
            ('security', 'Safety'),
            ('entertainment', 'Entertainment'),
            ('infotainment', 'Entertainment'),
            ('audio', 'Entertainment'),
            ('technology', 'Entertainment'),
            ('electrical', 'Electrical'),
            ('battery', 'Electrical'),
            ('brake', 'Brakes'),
            ('notable', 'Notable features'),
            ('feature', 'Notable features'),
            ('comfort', 'Notable features'),
            ('convenience', 'Notable features'),
            ('interior', 'Notable features'),
            ('exterior', 'Highlights'),
        ]
        for match, category in mapping:
            if match in key:
                return category
        if len(heading.split()) <= 3:
            return heading.strip().title()
        return None

    def _infer_category_from_label(self, label: str) -> Optional[str]:
        if not label:
            return None
        text = label.lower()
        if any(k in text for k in ['hp', 'horsepower', 'torque', 'engine', 'cylinder', 'displacement', 'powertrain']):
            return 'Engine'
        if any(k in text for k in ['suspension', 'damp', 'chassis']):
            return 'Suspension'
        if any(k in text for k in ['weight', 'capacity', 'cargo', 'fuel tank', 'ground clearance', 'wheelbase', 'length', 'width', 'height']):
            return 'Weight & Capacity'
        if any(k in text for k in ['safety', 'assist', 'warning', 'airbag', 'camera', 'monitor']):
            return 'Safety'
        if any(k in text for k in ['brake', 'abs', 'rotor']):
            return 'Brakes'
        if any(k in text for k in ['mpg', 'fuel economy', 'performance', 'drive', 'drivetrain', 'transmission', 'speed']):
            return 'Highlights'
        if any(k in text for k in ['seat', 'leather', 'sunroof', 'moonroof', 'heated', 'ventilated', 'lighting', 'feature']):
            return 'Notable features'
        if any(k in text for k in ['bluetooth', 'audio', 'speaker', 'infotainment', 'touchscreen', 'apple carplay', 'android auto', 'navigation']):
            return 'Entertainment'
        if any(k in text for k in ['alternator', 'amp', 'battery', 'voltage']):
            return 'Electrical'
        return None

    def _extract_label_value_specs(self, main_content) -> Dict[str, List[str]]:
        specs: Dict[str, List[str]] = {}
        if not main_content:
            return specs
        current_category = None
        heading_tags = ['h2', 'h3', 'h4', 'h5', 'strong', 'b']
        for elem in main_content.find_all(['h2', 'h3', 'h4', 'h5', 'strong', 'b', 'p', 'li'], recursive=True):
            text = elem.get_text(" ", strip=True)
            if not text:
                continue
            if elem.name in heading_tags:
                cat = self._standardize_category_name(text)
                if cat:
                    current_category = cat
                continue
            if ':' in text and len(text.split(':', 1)[0]) < 80:
                label, value = text.split(':', 1)
                label = label.strip()
                value = value.strip()
                if not value:
                    continue
                category = self._infer_category_from_label(label) or current_category or 'Notable features'
                self._add_spec_entry(specs, category, f"{label}: {value}")
            else:
                category = self._infer_category_from_label(text)
                if category:
                    self._add_spec_entry(specs, category, text)
        return specs

    def _merge_spec_dicts(self, base: Dict[str, List[str]], extra: Dict[str, List[str]]) -> Dict[str, List[str]]:
        for category, values in extra.items():
            for value in values:
                self._add_spec_entry(base, category, value)
        return base
    
    def _extract_features(self, text: str, soup_element) -> List[str]:
        """Extract notable features from text."""
        features = []
        
        # Look for feature lists or feature mentions
        feature_patterns = [
            r'(\d+[-\s]?(inch|inch|")\s+(display|screen|wheel|rim))',
            r'(\d+[.\s]?\d*\s*(inch|")\s+(display|screen))',
            r'(wireless\s+(charging|android\s+auto|apple\s+carplay))',
            r'(heated\s+(front|rear)\s+seats)',
            r'(ventilated\s+seats)',
            r'(panoramic\s+moonroof)',
            r'(power\s+(liftgate|tailgate|trunk))',
            r'(digital\s+instrument\s+cluster)',
            r'(ambient\s+lighting)',
            r'(\d+\s+color[s]?\s+ambient\s+lighting)',
            r'(leather\s+upholstery)',
            r'(nappa\s+leather)',
            r'(premium\s+sound\s+system)',
            r'(bang\s+&\s+olufsen)',
            r'(burmester)',
            r'(all[-\s]?wheel\s+drive|4matric|awd)',
            r'(rear[-\s]?wheel\s+drive|rwd)',
            r'(front[-\s]?wheel\s+drive|fwd)',
        ]
        
        for pattern in feature_patterns:
            matches = re.findall(pattern, text, re.I)
            for match in matches:
                if isinstance(match, tuple):
                    feature = ' '.join(match).strip()
                else:
                    feature = match.strip()
                if feature and feature not in features:
                    features.append(feature)
        
        # Look for strong/bold text that might be features
        for strong in soup_element.find_all(['strong', 'b']):
            strong_text = strong.get_text().strip()
            if strong_text and len(strong_text) < 100 and strong_text not in features:
                # Check if it looks like a feature
                if any(keyword in strong_text.lower() for keyword in ['inch', 'wheel', 'seat', 'system', 'lighting', 'display']):
                    features.append(strong_text)
        
        return features[:20]  # Limit to top 20 features
    
    def _extract_highlights(self, text: str, soup_element) -> List[str]:
        """Extract highlights (MPG, capacity, etc.)."""
        highlights = []
        
        # MPG patterns
        mpg_patterns = [
            r'(\d+\s*/\s*\d+\s*/\s*\d+\s*mpg\s*(city|highway|combined))',
            r'(\d+\s*/\s*\d+\s*mpg\s*(city|highway))',
            r'(\d+\s*mpg\s*(city|highway|combined))',
        ]
        
        for pattern in mpg_patterns:
            matches = re.findall(pattern, text, re.I)
            for match in matches:
                if isinstance(match, tuple):
                    highlight = ' '.join(match).strip()
                else:
                    highlight = match.strip()
                if highlight and highlight not in highlights:
                    highlights.append(highlight)
        
        # Seat capacity
        seat_match = re.search(r'(\d+[-\s]?seat)', text, re.I)
        if seat_match:
            highlights.append(f"{seat_match.group(1)} capacity")
        
        # Drivetrain
        drivetrain_match = re.search(r'(front[-\s]?wheel\s+drive|rear[-\s]?wheel\s+drive|all[-\s]?wheel\s+drive|4matric|awd|fwd|rwd)', text, re.I)
        if drivetrain_match:
            highlights.append(f"{drivetrain_match.group(1).title()} Drivetrain")
        
        return highlights[:10]
    
    def _extract_engine_specs(self, text: str, soup_element) -> List[str]:
        """Extract engine specifications matching reference format."""
        engine_specs = []
        
        # FIRST: Try to extract from prose patterns (most reliable for NetCarShow.com)
        # Pattern: "XXX-horsepower (SAE net), X.X-liter, ..."
        prose_pattern = r'(\d+)[-\s]?(horsepower|hp)\s*\([^)]*\)[,\s]+(\d+\.\d+)[-\s]?(liter|l|litre)[,\s]+([^,]+?)(?:engine|mated)'
        prose_match = re.search(prose_pattern, text, re.I)
        if prose_match:
            hp = prose_match.group(1)
            displacement = prose_match.group(3)
            unit = prose_match.group(4)
            details = prose_match.group(5).strip()
            
            # Only process if horsepower is reasonable (not "4" from "4-cylinder")
            if hp.isdigit() and int(hp) >= 50:
                # Try to extract engine type from details
                engine_type = None
                if re.search(r'(inline|i[-\s]?4|four[-\s]?cylinder)', details, re.I):
                    engine_type = "I-4"
                elif re.search(r'v6|six[-\s]?cylinder', details, re.I):
                    engine_type = "V6"
                elif re.search(r'v8|eight[-\s]?cylinder', details, re.I):
                    engine_type = "V8"
                elif re.search(r'v12|twelve[-\s]?cylinder', details, re.I):
                    engine_type = "V12"
                
                if engine_type:
                    engine_specs.append(f"Gas {engine_type} Engine Type")
                
                # Add displacement
                engine_specs.append(f"{displacement} {unit.upper()} Displacement")
                
                # Add horsepower
                engine_specs.append(f"{hp} @ SAE Net Horsepower @ RPM")
        
        # Engine Type patterns - match formats like "Gas I4 Engine Type", "Premium Unleaded I-4 Engine Type"
        engine_type_patterns = [
            r'((gas|premium\s+unleaded|diesel|petrol)\s+(i[-\s]?4|inline[-\s]?4|four[-\s]?cylinder|v6|v8|v12)\s+engine\s+type)',
            r'((i[-\s]?4|inline[-\s]?4|four[-\s]?cylinder|v6|v8|v12)\s+(gas|premium\s+unleaded|diesel|petrol)\s+engine\s+type)',
            r'((intercooled\s+)?(turbo|twin[-\s]?turbo|supercharged)\s+(premium\s+unleaded|gas|diesel)\s+(i[-\s]?4|inline[-\s]?4|v6|v8)\s+engine\s+type)',
            r'(\d+[-\s]?horsepower[-\s]?,\s+\d+\.\d+[-\s]?liter\s+(inline[-\s]?)?(four|4|v6|v8|v12)[-\s]?cylinder)',
        ]
        
        for pattern in engine_type_patterns:
            matches = re.findall(pattern, text, re.I)
            for match in matches:
                if isinstance(match, tuple):
                    spec = ' '.join([m for m in match if m]).strip()
                else:
                    spec = match.strip()
                if spec and len(spec) > 3 and spec not in engine_specs:
                    # Format to match reference: "Premium Unleaded I-4 Engine Type"
                    spec = spec.title().replace('I-4', 'I-4').replace('I4', 'I-4')
                    if 'Engine Type' not in spec:
                        spec = f"{spec} Engine Type"
                    engine_specs.append(spec)
        
        # Displacement patterns - match "2.0L/122 Displacement" or "2.4 L/144 Displacement"
        displacement_patterns = [
            r'(\d+\.\d+)\s*(l|lit[re]?[s]?)[\/\s](\d+)\s*(displacement|disp)',
            r'(\d+\.\d+)\s*(l|lit[re]?[s]?)\s*\/\s*(\d+)\s*(displacement|disp)',
            r'(\d+\.\d+)\s*(l|lit[re]?[s]?)\s+(\d+)\s*(displacement|disp)',
        ]
        
        for pattern in displacement_patterns:
            matches = re.findall(pattern, text, re.I)
            for match in matches:
                if isinstance(match, tuple) and len(match) >= 3:
                    displacement = f"{match[0]} {match[1].upper()}/{match[2]} Displacement"
                    if displacement not in engine_specs:
                        engine_specs.append(displacement)
        
        # Horsepower patterns - match "150 @ 6500 SAE Net Horsepower @ RPM" or "201 @ 6800 SAE Net Horsepower @ RPM"
        # Also match prose patterns like "201-horsepower (SAE net)"
        hp_patterns = [
            r'(\d+)\s*@\s*(\d+)\s*(sae\s+net\s+)?(horsepower|hp)[\s@]*(\d+)?\s*(rpm)?',
            r'(\d+)[-\s]?(horsepower|hp)\s*\([^)]*sae[^)]*\)',  # "201-horsepower (SAE net)"
            r'(\d+)\s*(hp|horsepower)\s*@\s*(\d+)\s*(rpm)?',
            r'(\d+)[-\s]?(horsepower|hp)(?:\s+\([^)]*\))?',  # "201-horsepower" or "201 hp"
        ]
        
        for pattern in hp_patterns:
            matches = re.findall(pattern, text, re.I)
            for match in matches:
                if isinstance(match, tuple):
                    parts = [m for m in match if m]
                    if len(parts) >= 1:
                        hp_val = parts[0]
                        # Only add if it's a reasonable horsepower value (not "4" from "4-cylinder")
                        if hp_val.isdigit() and int(hp_val) >= 50:  # Reasonable minimum
                            rpm_val = None
                            if len(parts) > 1 and parts[-1].isdigit() and len(parts[-1]) >= 3:
                                rpm_val = parts[-1]
                            if rpm_val:
                                spec = f"{hp_val} @ {rpm_val} SAE Net Horsepower @ RPM"
                            else:
                                spec = f"{hp_val} @ SAE Net Horsepower @ RPM"
                            if spec not in engine_specs:
                                engine_specs.append(spec)
        
        # Torque patterns - match "140 @ 4300 SAE Net Torque @ RPM" or "180 @ 3600 SAE Net Torque @ RPM"
        torque_patterns = [
            r'(\d+)\s*@\s*(\d+)\s*(sae\s+net\s+)?(torque|lb[-\s]?ft|pounds[-\s]?feet)[\s@]*(\d+)?\s*(rpm)?',
            r'(\d+)\s*(lb[-\s]?ft|pounds[-\s]?feet|nm|torque)\s*@\s*(\d+)\s*(rpm)?',
            r'(\d+)\s*(lb[-\s]?ft|pounds[-\s]?feet)\s*of\s+torque\s*@\s*(\d+)?',
        ]
        
        for pattern in torque_patterns:
            matches = re.findall(pattern, text, re.I)
            for match in matches:
                if isinstance(match, tuple):
                    parts = [m for m in match if m]
                    if len(parts) >= 2:
                        torque_val = parts[0]
                        rpm_val = parts[-1] if parts[-1].isdigit() else None
                        if rpm_val:
                            spec = f"{torque_val} @ {rpm_val} SAE Net Torque @ RPM"
                        else:
                            spec = f"{torque_val} @ SAE Net Torque @ RPM"
                        if spec not in engine_specs:
                            engine_specs.append(spec)
        
        # Fallback: Look for common engine descriptions in prose text
        # NetCarShow.com often has patterns like "201-horsepower (SAE net), 2.4-liter, 16-valve DOHC i-VTEC™ engine"
        if not engine_specs:
            # Pattern: "XXX-horsepower (SAE net), X.X-liter, ..."
            prose_pattern = r'(\d+)[-\s]?(horsepower|hp)\s*\([^)]*\)[,\s]+(\d+\.\d+)[-\s]?(liter|l|litre)[,\s]+([^,]+?)(?:engine|mated)'
            prose_match = re.search(prose_pattern, text, re.I)
            if prose_match:
                hp = prose_match.group(1)
                displacement = prose_match.group(3)
                unit = prose_match.group(4)
                details = prose_match.group(5).strip()
                
                # Try to extract engine type from details
                engine_type = None
                if re.search(r'(inline|i[-\s]?4|four[-\s]?cylinder)', details, re.I):
                    engine_type = "I-4"
                elif re.search(r'v6|six[-\s]?cylinder', details, re.I):
                    engine_type = "V6"
                elif re.search(r'v8|eight[-\s]?cylinder', details, re.I):
                    engine_type = "V8"
                elif re.search(r'v12|twelve[-\s]?cylinder', details, re.I):
                    engine_type = "V12"
                
                if engine_type:
                    engine_specs.append(f"Gas {engine_type} Engine Type")
                
                # Add displacement
                engine_specs.append(f"{displacement} {unit.upper()} Displacement")
                
                # Add horsepower
                engine_specs.append(f"{hp} @ SAE Net Horsepower @ RPM")
            
            # Simpler patterns for when the above doesn't match
            simple_patterns = [
                r'(\d+\.\d+)[-\s]?(liter|l|litre)[,\s]+([^,]+?)(?:inline[-\s]?4|four[-\s]?cylinder|v6|v8|v12)',
                r'(\d+)[-\s]?(hp|horsepower)[,\s]+(\d+\.\d+)[-\s]?(liter|l|litre)',
                r'(\d+\.\d+)[-\s]?(liter|l|litre)\s+(inline[-\s]?)?(four|4|six|v6|v8)[-\s]?cylinder',
            ]
            for pattern in simple_patterns:
                matches = re.findall(pattern, text, re.I)
                for match in matches:
                    if isinstance(match, tuple):
                        parts = [m for m in match if m]
                        if len(parts) >= 2:
                            # Try to construct a meaningful spec
                            if any('hp' in p.lower() or 'horsepower' in p.lower() for p in parts):
                                # Has horsepower
                                hp_val = next((p for p in parts if p.isdigit() and len(p) >= 2), None)
                                if hp_val:
                                    engine_specs.append(f"{hp_val} @ SAE Net Horsepower @ RPM")
                            if any('liter' in p.lower() or 'l' == p.lower() for p in parts):
                                # Has displacement
                                disp_val = next((p for p in parts if re.match(r'\d+\.\d+', p)), None)
                                if disp_val:
                                    engine_specs.append(f"{disp_val} L Displacement")
        
        return engine_specs[:15]
    
    def _extract_suspension_specs(self, text: str, soup_element) -> List[str]:
        """Extract suspension specifications matching reference format."""
        suspension_specs = []
        
        # Match formats like "Strut Suspension Type - Front", "Multi-Link Suspension Type - Rear"
        suspension_patterns = [
            r'(strut|macpherson\s+strut)\s+suspension\s+type[-\s]?(front|rear|\(cont\.\))?',
            r'(multi[-\s]?link)\s+suspension\s+type[-\s]?(front|rear|\(cont\.\))?',
            r'(double[-\s]?wishbone)\s+suspension\s+type[-\s]?(front|rear)?',
            r'(independent)\s+(front|rear)\s+suspension\s+type',
            r'(air\s+suspension|adaptive\s+suspension|dynamic\s+body\s+control)',
        ]
        
        for pattern in suspension_patterns:
            matches = re.findall(pattern, text, re.I)
            for match in matches:
                if isinstance(match, tuple):
                    parts = [m for m in match if m]
                    if len(parts) >= 1:
                        suspension_type = parts[0].title()
                        location = parts[1].title() if len(parts) > 1 and parts[1] else None
                        
                        # Format to match reference
                        if location and location.lower() in ['front', 'rear']:
                            spec = f"{suspension_type} Suspension Type - {location}"
                        elif location and '(cont.)' in location.lower():
                            spec = f"{suspension_type} Suspension Type - {location}"
                        else:
                            spec = f"{suspension_type} Suspension Type"
                        
                        if spec not in suspension_specs:
                            suspension_specs.append(spec)
                else:
                    spec = match.strip().title()
                    if spec and spec not in suspension_specs:
                        if 'Suspension Type' not in spec:
                            spec = f"{spec} Suspension Type"
                        suspension_specs.append(spec)
        
        # Also look for common suspension mentions
        if not suspension_specs:
            common_patterns = [
                r'(mcpherson\s+strut|double\s+wishbone|multi[-\s]?link|independent)',
            ]
            for pattern in common_patterns:
                matches = re.findall(pattern, text, re.I)
                for match in matches:
                    if isinstance(match, tuple):
                        spec = ' '.join(match).strip().title()
                    else:
                        spec = match.strip().title()
                    if spec and spec not in suspension_specs:
                        suspension_specs.append(f"{spec} Suspension Type")
        
        return suspension_specs[:10]
    
    def _extract_weight_capacity(self, text: str, soup_element) -> List[str]:
        """Extract weight and capacity specifications matching reference format."""
        weight_specs = []
        
        # Weight patterns - match "2,970 lbs Base Curb Weight" or "3,148 lbs Base Curb Weight"
        weight_patterns = [
            r'(\d+[,\.]?\d*)\s*(lbs?|kg|kilograms?)\s*(base\s+)?(curb\s+weight)',
            r'(curb\s+weight|base\s+curb\s+weight)[:\s]+(\d+[,\.]?\d*)\s*(lbs?|kg)',
            r'(\d+[,\.]?\d*)\s*(lbs?|kg)\s*(curb\s+weight)',
        ]
        
        for pattern in weight_patterns:
            matches = re.findall(pattern, text, re.I)
            for match in matches:
                if isinstance(match, tuple):
                    parts = [m for m in match if m]
                    if len(parts) >= 2:
                        # Find weight value and unit
                        weight_val = None
                        weight_unit = None
                        for part in parts:
                            if re.match(r'\d+[,\.]?\d*', part):
                                weight_val = part.replace(',', '')
                            elif part.lower() in ['lb', 'lbs', 'kg', 'kilograms']:
                                weight_unit = part
                        
                        if weight_val and weight_unit:
                            spec = f"{weight_val} {weight_unit} Base Curb Weight"
                            if spec not in weight_specs:
                                weight_specs.append(spec)
        
        # Fuel tank capacity - match "13 gal Fuel Tank Capacity, Approx"
        fuel_patterns = [
            r'(\d+)\s*(gal|lit[re]?[s]?|gallons?)\s*(fuel\s+tank\s+capacity)',
            r'(fuel\s+tank\s+capacity)[:\s]+(\d+)\s*(gal|lit[re]?[s]?|gallons?)',
        ]
        
        for pattern in fuel_patterns:
            matches = re.findall(pattern, text, re.I)
            for match in matches:
                if isinstance(match, tuple):
                    parts = [m for m in match if m]
                    if len(parts) >= 2:
                        fuel_val = None
                        fuel_unit = None
                        for part in parts:
                            if part.isdigit():
                                fuel_val = part
                            elif part.lower() in ['gal', 'gallon', 'gallons', 'l', 'liter', 'litre', 'liters', 'litres']:
                                fuel_unit = part
                        
                        if fuel_val and fuel_unit:
                            spec = f"{fuel_val} {fuel_unit} Fuel Tank Capacity, Approx"
                            if spec not in weight_specs:
                                weight_specs.append(spec)
        
        # Dimensions
        dim_patterns = [
            r'(\d+[,\.]?\d*)\s*(mm|millimetres?|inches?|"|in)\s*(long|wide|high|length|width|height)',
            r'(length|width|height|wheelbase)[:\s]+(\d+[,\.]?\d*)\s*(mm|inches?|in|"|millimetres?)',
        ]
        
        for pattern in dim_patterns:
            matches = re.findall(pattern, text, re.I)
            for match in matches:
                if isinstance(match, tuple):
                    parts = [m for m in match if m]
                    if len(parts) >= 2:
                        dim_val = None
                        dim_unit = None
                        dim_type = None
                        for part in parts:
                            if re.match(r'\d+[,\.]?\d*', part):
                                dim_val = part
                            elif part.lower() in ['mm', 'millimetres', 'millimeters', 'in', 'inch', 'inches', '"']:
                                dim_unit = part if part != '"' else 'in'
                            elif part.lower() in ['length', 'width', 'height', 'long', 'wide', 'high', 'wheelbase']:
                                dim_type = part
                        
                        if dim_val and dim_unit:
                            if dim_type:
                                spec = f"{dim_val} {dim_unit} {dim_type.title()}"
                            else:
                                spec = f"{dim_val} {dim_unit}"
                            if spec not in weight_specs:
                                weight_specs.append(spec)
        
        return weight_specs[:15]
    
    def _extract_safety_features(self, text: str, soup_element) -> List[str]:
        """Extract safety features."""
        safety_features = []
        
        safety_patterns = [
            r'(standard\s+)?(stability\s+control)',
            r'(standard\s+)?(automatic\s+emergency\s+braking)',
            r'(standard\s+)?(backup\s+camera|reversing\s+camera)',
            r'(standard\s+)?(blind\s+spot\s+monitor|blind\s+spot\s+assist)',
            r'(standard\s+)?(lane\s+departure\s+warning)',
            r'(standard\s+)?(rear\s+cross\s+traffic\s+alert)',
            r'(standard\s+)?(active\s+brake\s+assist)',
            r'(standard\s+)?(attention\s+assist)',
            r'(standard\s+)?(active\s+lane\s+keeping\s+assist)',
            r'(standard\s+)?(speed\s+limit\s+assist)',
            r'(standard\s+)?(distronic|active\s+distance\s+assist)',
            r'(standard\s+)?(pre[-\s]?safe)',
            r'(standard\s+)?(airbag[s]?)',
            r'(standard\s+)?(abs\s+brake\s+system)',
        ]
        
        for pattern in safety_patterns:
            matches = re.findall(pattern, text, re.I)
            for match in matches:
                if isinstance(match, tuple):
                    feature = ' '.join([m for m in match if m]).strip()
                else:
                    feature = match.strip()
                if feature:
                    # Standardize format
                    if not feature.lower().startswith('standard'):
                        feature = f"Standard {feature.title()}"
                    else:
                        feature = feature.title()
                    if feature not in safety_features:
                        safety_features.append(feature)
        
        return safety_features[:15]
    
    def _extract_entertainment_features(self, text: str, soup_element) -> List[str]:
        """Extract entertainment features."""
        entertainment_features = []
        
        entertainment_patterns = [
            r'(standard\s+)?(bluetooth)',
            r'(wireless\s+(android\s+auto|apple\s+carplay))',
            r'(\d+\s+speaker\s+(sound\s+)?system)',
            r'(premium\s+sound\s+system)',
            r'(bang\s+&\s+olufsen)',
            r'(burmester)',
            r'(harman\s+kardon)',
            r'(bose)',
            r'(dolby\s+atmos)',
            r'(spatial\s+audio)',
            r'(internet\s+radio)',
            r'(music\s+streaming)',
        ]
        
        for pattern in entertainment_patterns:
            matches = re.findall(pattern, text, re.I)
            for match in matches:
                if isinstance(match, tuple):
                    feature = ' '.join([m for m in match if m]).strip()
                else:
                    feature = match.strip()
                if feature:
                    if not feature.lower().startswith('standard'):
                        feature = f"Standard {feature.title()}"
                    else:
                        feature = feature.title()
                    if feature not in entertainment_features:
                        entertainment_features.append(feature)
        
        return entertainment_features[:10]
    
    def _extract_electrical_specs(self, text: str, soup_element) -> List[str]:
        """Extract electrical specifications."""
        electrical_specs = []
        
        # Battery/electrical patterns
        electrical_patterns = [
            r'(\d+[-\s]?volt\s+(electrical\s+)?system)',
            r'(\d+\s+amp[s]?\s+(alternator|battery))',
            r'(cold\s+cranking\s+amps)',
            r'(maximum\s+alternator\s+capacity)',
        ]
        
        for pattern in electrical_patterns:
            matches = re.findall(pattern, text, re.I)
            for match in matches:
                if isinstance(match, tuple):
                    spec = ' '.join(match).strip()
                else:
                    spec = match.strip()
                if spec and spec not in electrical_specs:
                    electrical_specs.append(spec.title())
        
        return electrical_specs[:5]
    
    def _extract_brake_specs(self, text: str, soup_element) -> List[str]:
        """Extract brake specifications matching reference format."""
        brake_specs = []
        
        # Match formats like "4-Wheel Disc Brake Type", "Pwr Brake Type"
        brake_type_patterns = [
            r'(\d+[-\s]?wheel\s+disc\s+brake\s+type)',
            r'(pwr|power)\s+brake\s+type',
            r'(disc\s+brake\s+type)',
            r'(drum\s+brake\s+type)',
        ]
        
        for pattern in brake_type_patterns:
            matches = re.findall(pattern, text, re.I)
            for match in matches:
                if isinstance(match, tuple):
                    spec = ' '.join([m for m in match if m]).strip()
                else:
                    spec = match.strip()
                if spec and spec not in brake_specs:
                    if 'Brake Type' not in spec:
                        spec = f"{spec.title()} Brake Type"
                    else:
                        spec = spec.title()
                    brake_specs.append(spec)
        
        # Match "4-Wheel Brake ABS System"
        abs_patterns = [
            r'(\d+[-\s]?wheel\s+brake\s+abs\s+system)',
            r'(abs\s+brake\s+system)',
            r'(anti[-\s]?lock\s+brake\s+system)',
        ]
        
        for pattern in abs_patterns:
            matches = re.findall(pattern, text, re.I)
            for match in matches:
                if isinstance(match, tuple):
                    spec = ' '.join([m for m in match if m]).strip()
                else:
                    spec = match.strip()
                if spec and spec not in brake_specs:
                    if 'ABS System' not in spec and 'Brake ABS System' not in spec:
                        spec = f"{spec.title()} Brake ABS System"
                    else:
                        spec = spec.title()
                    brake_specs.append(spec)
        
        # Match "Yes Disc - Front (Yes or )" or "Disc - Front"
        disc_patterns = [
            r'((yes|standard)\s+)?disc[-\s]?(front|rear)',
            r'(disc[-\s]?(front|rear)\s*\(yes\s+or\s+\)?)',
        ]
        
        for pattern in disc_patterns:
            matches = re.findall(pattern, text, re.I)
            for match in matches:
                if isinstance(match, tuple):
                    parts = [m for m in match if m]
                    if len(parts) >= 2:
                        location = parts[-1].title() if parts[-1].lower() in ['front', 'rear'] else None
                        if location:
                            spec = f"Yes Disc - {location} (Yes or )"
                            if spec not in brake_specs:
                                brake_specs.append(spec)
        
        # Match "11.100 x -TBD- in Front Brake Rotor Diam x Thickness" or similar
        rotor_patterns = [
            r'(\d+[\.]?\d*)\s*(x|×)\s*([-\w]+)?\s*(in|inch|inches)\s*(front|rear)\s+brake\s+rotor\s+(diam|diameter)\s*(x|×)\s*(thickness)?',
            r'(\d+[\.]?\d*)\s*(in|inch|inches)\s*(front|rear)\s+brake\s+rotor',
        ]
        
        for pattern in rotor_patterns:
            matches = re.findall(pattern, text, re.I)
            for match in matches:
                if isinstance(match, tuple):
                    parts = [m for m in match if m]
                    if len(parts) >= 3:
                        diameter = parts[0]
                        location = None
                        thickness = None
                        for i, part in enumerate(parts):
                            if part.lower() in ['front', 'rear']:
                                location = part.title()
                            if part.lower() in ['thickness', 'x', '×'] and i < len(parts) - 1:
                                thickness = parts[i+1] if i+1 < len(parts) else '-TBD-'
                        
                        if location:
                            if thickness and thickness != 'x' and thickness != '×':
                                spec = f"{diameter} x {thickness} in {location} Brake Rotor Diam x Thickness"
                            else:
                                spec = f"{diameter} x -TBD- in {location} Brake Rotor Diam x Thickness"
                            if spec not in brake_specs:
                                brake_specs.append(spec)
        
        return brake_specs[:15]
    
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

