#!/usr/bin/env python3
"""
Test script to verify the data structure without network access.
Uses mock data to test the save structure.
"""

import sys
import os
import json
import shutil

# Add crawler directory to path
sys.path.insert(0, os.path.dirname(__file__))

from crawler.saver import Saver
from crawler.schema import SchemaMapper

def test_structure():
    """Test the save structure with mock data."""
    
    # Use a test output directory
    test_output_dir = "test_data_structure"
    
    # Clean up if exists
    if os.path.exists(test_output_dir):
        shutil.rmtree(test_output_dir)
    
    # Initialize saver
    saver = Saver(output_dir=test_output_dir)
    
    print("=" * 60)
    print("Testing Data Structure")
    print("=" * 60)
    print(f"Output directory: {test_output_dir}")
    print()
    
    # Create mock record (simulating what would come from the crawler)
    mock_record_1 = {
        "make": "acura",
        "model": "ilx",
        "years": {
            "2019": {
                "main_images": ["https://example.com/image1.jpg"],
                "expert_review": "Test review for 2019 ILX",
                "trims": [
                    {
                        "name": "Base",
                        "price": "$25000",
                        "specifications": {}
                    }
                ]
            }
        }
    }
    
    mock_record_2 = {
        "make": "acura",
        "model": "ilx",
        "years": {
            "2016": {
                "main_images": ["https://example.com/image2.jpg"],
                "expert_review": "Test review for 2016 ILX",
                "trims": [
                    {
                        "name": "Base",
                        "price": "$23000",
                        "specifications": {}
                    }
                ]
            }
        }
    }
    
    print("Test 1: Saving first record (2019 ILX)")
    print("-" * 60)
    file_path_1 = saver.save_record(
        mock_record_1,
        category="SUV",  # Should be ignored
        subcategory="Premium",  # Should be ignored
        make="acura",
        model="ilx"
    )
    print(f"✅ Saved to: {file_path_1}")
    print()
    
    print("Test 2: Saving second record (2016 ILX) - should merge into same file")
    print("-" * 60)
    file_path_2 = saver.save_record(
        mock_record_2,
        category="SUV",
        subcategory="Premium",
        make="acura",
        model="ilx"
    )
    print(f"✅ Saved to: {file_path_2}")
    print()
    
    # Verify structure
    print("=" * 60)
    print("Verifying Structure")
    print("=" * 60)
    
    expected_file = os.path.join(test_output_dir, "acura", "ilx.json")
    
    checks = []
    
    # Check 1: Files should be the same (merged)
    if file_path_1 == file_path_2:
        checks.append(("✅ Files merged", "Both records saved to same file"))
    else:
        checks.append(("❌ Files not merged", f"File 1: {file_path_1}, File 2: {file_path_2}"))
    
    # Check 2: Directory structure should be data/{make}/
    file_dir = os.path.dirname(expected_file)
    expected_dir = os.path.join(test_output_dir, "acura")
    if file_dir == expected_dir:
        checks.append(("✅ Directory structure", f"data/acura/"))
    else:
        checks.append(("❌ Directory structure", f"Expected: {expected_dir}, Got: {file_dir}"))
    
    # Check 3: Filename should be {model}.json
    filename = os.path.basename(expected_file)
    if filename == "ilx.json":
        checks.append(("✅ Filename", "ilx.json"))
    else:
        checks.append(("❌ Filename", f"Expected: ilx.json, Got: {filename}"))
    
    # Check 4: File should exist
    if os.path.exists(expected_file):
        checks.append(("✅ File exists", expected_file))
        
        # Read and verify content
        with open(expected_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # Check 5: Model name should be clean
        model_name = data.get('model', '')
        if model_name == "ilx":
            checks.append(("✅ Model name is clean", model_name))
        else:
            checks.append(("❌ Model name", f"Expected: ilx, Got: {model_name}"))
        
        # Check 6: Should have both years
        years = list(data.get('years', {}).keys())
        if '2019' in years and '2016' in years:
            checks.append(("✅ Multiple years merged", f"Found years: {years}"))
        else:
            checks.append(("❌ Years missing", f"Expected: ['2016', '2019'], Got: {years}"))
        
        # Check 7: Each year should have correct structure
        for year in ['2016', '2019']:
            if year in data['years']:
                year_data = data['years'][year]
                if 'main_images' in year_data and 'expert_review' in year_data and 'trims' in year_data:
                    checks.append((f"✅ Year {year} structure", "Has all required fields"))
                else:
                    checks.append((f"❌ Year {year} structure", "Missing required fields"))
        
        print("Structure checks:")
        for check, result in checks:
            print(f"  {check}: {result}")
        
        print()
        print("=" * 60)
        print("Final Data Structure:")
        print("=" * 60)
        print(json.dumps(data, indent=2))
        print()
        
        # Summary
        all_passed = all("✅" in check[0] for check in checks)
        if all_passed:
            print("=" * 60)
            print("✅ ALL CHECKS PASSED!")
            print("=" * 60)
            print(f"Structure is correct: {test_output_dir}/acura/ilx.json")
            print("Multiple years are merged into a single file.")
            return True
        else:
            print("=" * 60)
            print("❌ SOME CHECKS FAILED")
            print("=" * 60)
            return False
    else:
        checks.append(("❌ File not found", expected_file))
        print("Structure checks:")
        for check, result in checks:
            print(f"  {check}: {result}")
        return False

if __name__ == "__main__":
    success = test_structure()
    sys.exit(0 if success else 1)

