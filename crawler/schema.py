"""
Schema mapping to transform parsed data into the reference schema format.
"""

from typing import Dict, List, Any, Optional
import re


class SchemaMapper:
    """Maps scraped data to the reference schema format."""
    
    @staticmethod
    def map_to_schema(scraped_data: Dict, make: str, model: str, images: List[str] = None, 
                     category: str = "", subcategory: str = "", source_url: str = "") -> Dict:
        """
        Transform scraped data to match reference schema format.
        
        Args:
            scraped_data: Parsed data from detail page
            make: Make name (normalized)
            model: Model name (normalized)
            images: List of image URLs from gallery
            category: Category name (e.g., "SUV", "Coupe")
            subcategory: Subcategory name (e.g., "Premium")
            source_url: URL of the source page for this data
            
        Returns:
            Dict matching reference schema:
            {
                "make": "mercedes_benz",
                "model": "glc_coupe",
                "years": {
                    "2024": {
                        "main_images": [...],
                        "expert_review": "...",
                        "trims": [...],
                        "source_url": "https://...",
                        "category": "SUV",
                        "subcategory": "Premium"
                    }
                }
            }
        """
        # Normalize make and model names
        # Prefer model from URL parsing (passed as parameter) over scraped data
        # The model parameter should already be clean from URL parsing
        model_to_normalize = model or scraped_data.get('model', '')
        
        # If model name looks like a full title, try to extract just the model part from URL
        if ' - ' in model_to_normalize or 'pictures' in model_to_normalize.lower() or 'information' in model_to_normalize.lower():
            # Try to extract from URL if available
            if 'url' in scraped_data:
                from urllib.parse import urlparse
                path = urlparse(scraped_data['url']).path
                parts = path.strip('/').split('/')
                if len(parts) >= 2:
                    year_model = parts[1]
                    # Extract model part (after year-)
                    if '-' in year_model and year_model[0].isdigit():
                        model_to_normalize = year_model.split('-', 1)[1].replace('-', '_')
                    elif not year_model[0].isdigit():
                        # No year prefix, use the whole thing
                        model_to_normalize = year_model.replace('-', '_')
        
        normalized_make = SchemaMapper._normalize_name(make or scraped_data.get('make', ''))
        normalized_model = SchemaMapper._normalize_name(model_to_normalize)
        
        # Get years from scraped data
        years_data = scraped_data.get('years', [])
        if isinstance(years_data, str):
            years_data = [years_data]
        elif not isinstance(years_data, list):
            years_data = []
        
        # If no years found, try to extract from URL or use default
        if not years_data:
            # Try to get year from scraped_data
            if 'year' in scraped_data and scraped_data['year']:
                years_data = [scraped_data['year']]
            else:
                # Default to empty - will need to be filled later
                years_data = []
        
        # Build years structure
        years_dict = {}
        
        for year in years_data:
            if not year:
                continue
            
            year_str = str(year).strip()
            if not year_str or not year_str.isdigit():
                continue
            
            # Get images for this year (or use all images if not year-specific)
            year_images = images or scraped_data.get('images', [])
            if not isinstance(year_images, list):
                year_images = []
            
            # Get expert review
            expert_review = scraped_data.get('expert_review', '')
            if not isinstance(expert_review, str):
                expert_review = str(expert_review) if expert_review else ''
            
            # Get trims
            trims = scraped_data.get('trims', [])
            if not isinstance(trims, list):
                trims = []
            
            # Ensure trims have correct structure
            normalized_trims = []
            for trim in trims:
                if isinstance(trim, dict):
                    normalized_trim = {
                        'name': str(trim.get('name', 'Base')).strip() or 'Base',
                        'price': str(trim.get('price', '')).strip(),
                        'specifications': trim.get('specifications', {})
                    }
                    # Ensure specifications is a dict
                    if not isinstance(normalized_trim['specifications'], dict):
                        normalized_trim['specifications'] = {}
                    normalized_trims.append(normalized_trim)
            
            # If no trims, create default
            if not normalized_trims:
                normalized_trims = [{
                    'name': 'Base',
                    'price': '',
                    'specifications': {}
                }]
            
            # Get source URL - prefer passed parameter, then from scraped_data
            year_source_url = source_url or scraped_data.get('url', '')
            
            years_dict[year_str] = {
                'main_images': year_images,
                'expert_review': expert_review,
                'trims': normalized_trims,
                'source_url': year_source_url,
                'category': category or '',
                'subcategory': subcategory or ''
            }
        
        # If no years were created, create a placeholder structure
        if not years_dict:
            source_url_final = source_url or scraped_data.get('url', '')
            years_dict = {
                'unknown': {
                    'main_images': images or [],
                    'expert_review': scraped_data.get('expert_review', ''),
                    'trims': scraped_data.get('trims', [{
                        'name': 'Base',
                        'price': '',
                        'specifications': {}
                    }]),
                    'source_url': source_url_final,
                    'category': category or '',
                    'subcategory': subcategory or ''
                }
            }
        
        return {
            'make': normalized_make,
            'model': normalized_model,
            'years': years_dict
        }
    
    @staticmethod
    def _normalize_name(name: str) -> str:
        """
        Normalize make/model name to reference format.
        
        Rules:
        - Convert to lowercase
        - Replace spaces and hyphens with underscores
        - Remove special characters
        - Handle common variations
        
        Args:
            name: Original name
            
        Returns:
            Normalized name
        """
        if not name:
            return ''
        
        # Convert to lowercase
        normalized = name.lower().strip()
        
        # Replace spaces and hyphens with underscores
        normalized = re.sub(r'[\s\-]+', '_', normalized)
        
        # Remove special characters (keep alphanumeric and underscores)
        normalized = re.sub(r'[^a-z0-9_]', '', normalized)
        
        # Remove multiple consecutive underscores
        normalized = re.sub(r'_+', '_', normalized)
        
        # Remove leading/trailing underscores
        normalized = normalized.strip('_')
        
        # Handle common make name variations (only for exact matches)
        # This prevents "bmw_x5" from becoming just "bmw"
        make_variations = {
            'mercedes': 'mercedes_benz',
            'mercedesbenz': 'mercedes_benz',
            'mb': 'mercedes_benz',
        }
        
        # Only apply variations for exact matches (not partial matches)
        if normalized in make_variations:
            normalized = make_variations[normalized]
        
        return normalized
    
    @staticmethod
    def merge_years(existing_record: Dict, new_record: Dict) -> Dict:
        """
        Merge years from new_record into existing_record.
        
        Args:
            existing_record: Existing schema-formatted record
            new_record: New schema-formatted record to merge
            
        Returns:
            Merged record with combined years
        """
        if not existing_record:
            return new_record.copy()
        
        if not new_record:
            return existing_record.copy()
        
        merged = existing_record.copy()
        
        # Merge years
        existing_years = merged.get('years', {})
        new_years = new_record.get('years', {})
        
        for year, year_data in new_years.items():
            if year in existing_years:
                # Merge trims if same year
                existing_trims = existing_years[year].get('trims', [])
                new_trims = year_data.get('trims', [])
                
                # Combine trims (avoid duplicates by name)
                trim_names = {trim.get('name', '') for trim in existing_trims}
                for new_trim in new_trims:
                    if new_trim.get('name', '') not in trim_names:
                        existing_trims.append(new_trim)
                
                # Merge images (avoid duplicates)
                existing_images = existing_years[year].get('main_images', [])
                new_images = year_data.get('main_images', [])
                combined_images = list(set(existing_images + new_images))
                
                # Use new expert review if it's longer/more complete
                existing_review = existing_years[year].get('expert_review', '')
                new_review = year_data.get('expert_review', '')
                expert_review = new_review if len(new_review) > len(existing_review) else existing_review
                
                # Preserve source_url, category, subcategory from new record (more recent)
                # But keep existing if new doesn't have them
                source_url = year_data.get('source_url') or existing_years[year].get('source_url', '')
                category = year_data.get('category') or existing_years[year].get('category', '')
                subcategory = year_data.get('subcategory') or existing_years[year].get('subcategory', '')
                
                existing_years[year] = {
                    'main_images': combined_images,
                    'expert_review': expert_review,
                    'trims': existing_trims,
                    'source_url': source_url,
                    'category': category,
                    'subcategory': subcategory
                }
            else:
                # New year, just add it (with all fields including source_url, category, subcategory)
                existing_years[year] = year_data.copy()
        
        merged['years'] = existing_years
        
        return merged
    
    @staticmethod
    def normalize_category_name(category: str) -> str:
        """
        Normalize category name for directory structure.
        
        Args:
            category: Category name (e.g., "Crossover SUV", "SUV")
            
        Returns:
            Normalized name (e.g., "SUV")
        """
        if not category:
            return 'Unknown'
        
        normalized = category.lower().strip()
        
        # Map variations to standard names
        category_map = {
            'crossover-suv': 'SUV',
            'crossover_suv': 'SUV',
            'crossover suv': 'SUV',
            'suv': 'SUV',
            'sedan': 'Sedan',
            'coupe': 'Coupe',
            'cabrio': 'Cabriolet',
            'cabriolet': 'Cabriolet',
            'pickup': 'Pickup',
            'truck': 'Pickup',
            'estate-wagon': 'Wagon',
            'estate_wagon': 'Wagon',
            'wagon': 'Wagon',
            'hatchback': 'Hatchback',
            'mpv': 'MPV',
            'concept': 'Concept',
        }
        
        # Check for exact match or contains
        for variant, standard in category_map.items():
            if variant in normalized:
                return standard
        
        # Capitalize first letter of each word
        return ' '.join(word.capitalize() for word in normalized.split())
    
    @staticmethod
    def normalize_subcategory_name(subcategory: str) -> str:
        """
        Normalize subcategory name for directory structure.
        
        Args:
            subcategory: Subcategory name (e.g., "Premium", "Midsize")
            
        Returns:
            Normalized name
        """
        if not subcategory:
            return 'General'
        
        normalized = subcategory.strip()
        
        # Capitalize first letter
        return normalized.capitalize()

