"""
Validator for ensuring records match the reference schema format.
"""

from typing import Dict, List, Optional, Tuple


class Validator:
    """Validates records against the reference schema requirements."""
    
    @staticmethod
    def validate_record(record: Dict) -> Tuple[bool, List[str]]:
        """
        Validate a record against the reference schema.
        
        Required fields:
        - make (required, non-empty string)
        - model (required, non-empty string)
        - years (required, dict with at least one year)
        - Each year must have:
          - main_images (array, can be empty)
          - expert_review (string, can be empty)
          - trims (array, at least one trim)
        - Each trim must have:
          - name (string)
          - price (string, can be empty)
          - specifications (dict)
        
        Args:
            record: Record to validate (should match schema format)
            
        Returns:
            Tuple of (is_valid, list_of_errors)
        """
        errors = []
        
        if not isinstance(record, dict):
            return False, ["Record must be a dictionary"]
        
        # Check required top-level fields
        if 'make' not in record:
            errors.append("Missing required field: 'make'")
        elif not record['make'] or not isinstance(record['make'], str):
            errors.append("Field 'make' must be a non-empty string")
        
        if 'model' not in record:
            errors.append("Missing required field: 'model'")
        elif not record['model'] or not isinstance(record['model'], str):
            errors.append("Field 'model' must be a non-empty string")
        
        if 'years' not in record:
            errors.append("Missing required field: 'years'")
        elif not isinstance(record['years'], dict):
            errors.append("Field 'years' must be a dictionary")
        elif len(record['years']) == 0:
            errors.append("Field 'years' must contain at least one year")
        else:
            # Validate each year
            for year, year_data in record['years'].items():
                year_errors = Validator._validate_year(year, year_data)
                errors.extend([f"Year '{year}': {err}" for err in year_errors])
        
        is_valid = len(errors) == 0
        return is_valid, errors
    
    @staticmethod
    def _validate_year(year: str, year_data: Dict) -> List[str]:
        """
        Validate a single year's data.
        
        Args:
            year: Year string
            year_data: Data for this year
            
        Returns:
            List of error messages
        """
        errors = []
        
        if not isinstance(year_data, dict):
            errors.append("Year data must be a dictionary")
            return errors
        
        # Check main_images
        if 'main_images' not in year_data:
            errors.append("Missing required field: 'main_images'")
        elif not isinstance(year_data['main_images'], list):
            errors.append("Field 'main_images' must be an array")
        
        # Check expert_review
        if 'expert_review' not in year_data:
            errors.append("Missing required field: 'expert_review'")
        elif not isinstance(year_data['expert_review'], str):
            errors.append("Field 'expert_review' must be a string")
        
        # Check trims
        if 'trims' not in year_data:
            errors.append("Missing required field: 'trims'")
        elif not isinstance(year_data['trims'], list):
            errors.append("Field 'trims' must be an array")
        elif len(year_data['trims']) == 0:
            errors.append("Field 'trims' must contain at least one trim")
        else:
            # Validate each trim
            for i, trim in enumerate(year_data['trims']):
                trim_errors = Validator._validate_trim(trim, i)
                errors.extend([f"Trim {i}: {err}" for err in trim_errors])
        
        return errors
    
    @staticmethod
    def _validate_trim(trim: Dict, index: int) -> List[str]:
        """
        Validate a single trim's data.
        
        Args:
            trim: Trim data
            index: Trim index (for error messages)
            
        Returns:
            List of error messages
        """
        errors = []
        
        if not isinstance(trim, dict):
            errors.append("Trim must be a dictionary")
            return errors
        
        # Check name
        if 'name' not in trim:
            errors.append("Missing required field: 'name'")
        elif not isinstance(trim['name'], str):
            errors.append("Field 'name' must be a string")
        
        # Check price (optional but must be string if present)
        if 'price' in trim and not isinstance(trim['price'], str):
            errors.append("Field 'price' must be a string")
        
        # Check specifications
        if 'specifications' not in trim:
            errors.append("Missing required field: 'specifications'")
        elif not isinstance(trim['specifications'], dict):
            errors.append("Field 'specifications' must be a dictionary")
        
        return errors
    
    @staticmethod
    def validate_images(images: List[str]) -> Tuple[bool, List[str]]:
        """
        Validate image URLs.
        
        Args:
            images: List of image URLs
            
        Returns:
            Tuple of (is_valid, list_of_warnings)
        """
        warnings = []
        
        if not isinstance(images, list):
            return False, ["Images must be a list"]
        
        valid_extensions = ['.jpg', '.jpeg', '.png', '.gif', '.webp', '.bmp']
        valid_count = 0
        
        for i, img_url in enumerate(images):
            if not isinstance(img_url, str):
                warnings.append(f"Image {i} is not a string")
                continue
            
            if not img_url.startswith(('http://', 'https://', '/')):
                warnings.append(f"Image {i} has invalid URL format: {img_url[:50]}")
                continue
            
            # Check for valid image extension (optional check)
            img_lower = img_url.lower()
            if not any(img_lower.endswith(ext) for ext in valid_extensions):
                # Not a warning, just informational - URLs might not have extensions
                pass
            
            valid_count += 1
        
        if valid_count == 0 and len(images) > 0:
            warnings.append("No valid image URLs found")
        
        is_valid = len(warnings) == 0
        return is_valid, warnings
    
    @staticmethod
    def validate_specifications(specs: Dict) -> Tuple[bool, List[str]]:
        """
        Validate specifications structure.
        
        Args:
            specs: Specifications dictionary
            
        Returns:
            Tuple of (is_valid, list_of_warnings)
        """
        warnings = []
        
        if not isinstance(specs, dict):
            return False, ["Specifications must be a dictionary"]
        
        # Check that values are lists or strings
        for category, values in specs.items():
            if not isinstance(category, str):
                warnings.append(f"Category name must be a string: {category}")
            
            if isinstance(values, list):
                # Check list items are strings
                for i, value in enumerate(values):
                    if not isinstance(value, str):
                        warnings.append(f"Category '{category}', item {i} is not a string")
            elif isinstance(values, str):
                # Single string is okay
                pass
            else:
                warnings.append(f"Category '{category}' has invalid value type: {type(values)}")
        
        is_valid = len(warnings) == 0
        return is_valid, warnings
    
    @staticmethod
    def get_validation_summary(record: Dict) -> Dict:
        """
        Get a summary of record validation status.
        
        Args:
            record: Record to summarize
            
        Returns:
            Dict with validation summary
        """
        is_valid, errors = Validator.validate_record(record)
        
        summary = {
            'is_valid': is_valid,
            'error_count': len(errors),
            'errors': errors,
            'has_make': 'make' in record and bool(record.get('make')),
            'has_model': 'model' in record and bool(record.get('model')),
            'year_count': len(record.get('years', {})),
            'total_images': 0,
            'total_trims': 0
        }
        
        # Count images and trims
        years = record.get('years', {})
        for year_data in years.values():
            summary['total_images'] += len(year_data.get('main_images', []))
            summary['total_trims'] += len(year_data.get('trims', []))
        
        return summary

