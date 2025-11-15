"""
File saving and organization for crawled vehicle data.
"""

import json
import os
from pathlib import Path
from typing import Dict, Optional
from .schema import SchemaMapper


class Saver:
    """Handles saving records to disk with proper directory structure."""
    
    def __init__(self, output_dir: str = "data"):
        """
        Initialize saver with output directory.
        
        Args:
            output_dir: Base output directory for saved files
        """
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)
    
    def save_record(self, record: Dict, category: str, subcategory: str, 
                   make: Optional[str] = None, model: Optional[str] = None) -> str:
        """
        Save a record to disk with proper directory structure.
        
        Directory structure: data/type={category}/subtype={subcategory}/{make}/{model}.json
        
        Args:
            record: Schema-formatted record to save
            category: Category name (e.g., "SUV")
            subcategory: Subcategory name (e.g., "Premium")
            make: Make name (if not in record)
            model: Model name (if not in record)
            
        Returns:
            Path to saved file
        """
        # Get make and model from record or parameters
        make = make or record.get('make', 'unknown')
        model = model or record.get('model', 'unknown')
        
        # Normalize category and subcategory names
        category = SchemaMapper.normalize_category_name(category)
        subcategory = SchemaMapper.normalize_subcategory_name(subcategory)
        
        # Create directory structure
        # Format: data/type={category}/subtype={subcategory}/{make}/
        dir_path = os.path.join(
            self.output_dir,
            f"type={category}",
            f"subtype={subcategory}",
            make
        )
        os.makedirs(dir_path, exist_ok=True)
        
        # Normalize model name for filename
        model_filename = model.replace('/', '_').replace('\\', '_')
        file_path = os.path.join(dir_path, f"{model_filename}.json")
        
        # Check if file exists and merge years if needed
        if os.path.exists(file_path):
            existing_record = self._load_existing_record(file_path)
            if existing_record:
                record = SchemaMapper.merge_years(existing_record, record)
        
        # Validate record before saving
        from .validator import Validator
        is_valid, errors = Validator.validate_record(record)
        
        if not is_valid:
            raise ValueError(f"Record validation failed: {errors}")
        
        # Save to file
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(record, f, indent=2, ensure_ascii=False)
            return file_path
        except IOError as e:
            raise IOError(f"Failed to save record to {file_path}: {e}")
    
    def _load_existing_record(self, file_path: str) -> Optional[Dict]:
        """
        Load existing record from file.
        
        Args:
            file_path: Path to JSON file
            
        Returns:
            Existing record or None if file doesn't exist or is invalid
        """
        if not os.path.exists(file_path):
            return None
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            return None
    
    def merge_years(self, existing_record: Dict, new_record: Dict) -> Dict:
        """
        Merge years from new_record into existing_record.
        
        This is a convenience method that delegates to SchemaMapper.
        
        Args:
            existing_record: Existing record
            new_record: New record to merge
            
        Returns:
            Merged record
        """
        return SchemaMapper.merge_years(existing_record, new_record)
    
    def get_output_path(self, category: str, subcategory: str, make: str, model: str) -> str:
        """
        Get the output path for a record without saving it.
        
        Args:
            category: Category name
            subcategory: Subcategory name
            make: Make name
            model: Model name
            
        Returns:
            Full path where the record would be saved
        """
        category = SchemaMapper.normalize_category_name(category)
        subcategory = SchemaMapper.normalize_subcategory_name(subcategory)
        
        model_filename = model.replace('/', '_').replace('\\', '_')
        
        return os.path.join(
            self.output_dir,
            f"type={category}",
            f"subtype={subcategory}",
            make,
            f"{model_filename}.json"
        )

