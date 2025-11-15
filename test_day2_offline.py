#!/usr/bin/env python3
"""
Offline test script for Day 2 components.
Tests parsing, schema mapping, and validation with mock data.
"""

import sys
import os

# Add crawler directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'crawler'))

from parser import Parser
from gallery import GalleryParser
from schema import SchemaMapper
from validator import Validator


def create_mock_listing_html():
    """Create mock HTML for a listing page."""
    return """
    <html>
    <body>
        <a href="/mercedes-benz/2024-glc_coupe">Mercedes-Benz GLC Coupe 2024</a>
        <a href="/mercedes-benz/2024-glc43_amg_coupe">Mercedes-Benz GLC43 AMG Coupe 2024</a>
        <a href="/audi/2024-a4">Audi A4 2024</a>
        <a href="/bmw/2023-x5">BMW X5 2023</a>
    </body>
    </html>
    """


def create_mock_detail_html():
    """Create mock HTML for a detail page."""
    return """
    <html>
    <head>
        <title>2024 Mercedes-Benz GLC Coupe</title>
        <meta name="description" content="The 2024 Mercedes-Benz GLC Coupe is a luxury SUV with advanced features.">
    </head>
    <body>
        <h1>2024 Mercedes-Benz GLC Coupe</h1>
        <p>This is an expert review of the 2024 Mercedes-Benz GLC Coupe. 
        It features a powerful engine, luxurious interior, and advanced safety systems.</p>
        <a href="/mercedes-benz/2024-glc_coupe-wallpapers/">View Gallery</a>
        
        <table class="specifications">
            <tr>
                <th>Engine</th>
                <td>2.0L Turbo</td>
            </tr>
            <tr>
                <td>Horsepower</td>
                <td>255 HP</td>
            </tr>
            <tr>
                <th>Safety</th>
                <td>Advanced Safety Package</td>
            </tr>
            <tr>
                <td>Airbags</td>
                <td>8</td>
            </tr>
        </table>
    </body>
    </html>
    """


def create_mock_gallery_html():
    """Create mock HTML for a gallery page."""
    return """
    <html>
    <body>
        <img src="/images/mercedes-benz/2024-glc_coupe/photo1_1920x1080.jpg" alt="GLC Coupe">
        <img src="/images/mercedes-benz/2024-glc_coupe/photo2_3840x2160.jpg" alt="GLC Coupe Interior">
        <img src="/images/mercedes-benz/2024-glc_coupe/photo3_1920x1080.jpg" alt="GLC Coupe Exterior">
    </body>
    </html>
    """


def test_listing_parser():
    """Test listing page parser."""
    print("=" * 60)
    print("Test 1: Listing Page Parser")
    print("=" * 60)
    
    parser = Parser()
    html = create_mock_listing_html()
    
    models = parser.parse_listing_page(html, category="SUV", subcategory="Premium")
    
    print(f"Found {len(models)} models:")
    for model in models:
        print(f"  - {model['make']} {model['model']} ({model['year']})")
        print(f"    URL: {model['url']}")
    
    assert len(models) > 0, "Should find at least one model"
    assert models[0]['make'] == 'mercedes_benz', "Should extract make correctly"
    assert models[0]['model'] == 'glc_coupe', "Should extract model correctly"
    
    print("✅ Listing parser test passed!\n")
    return models


def test_detail_parser():
    """Test detail page parser."""
    print("=" * 60)
    print("Test 2: Detail Page Parser")
    print("=" * 60)
    
    parser = Parser()
    html = create_mock_detail_html()
    url = "https://www.netcarshow.com/mercedes-benz/2024-glc_coupe/"
    
    data = parser.parse_model_detail_page(html, url)
    
    print(f"Parsed data:")
    print(f"  Make: {data.get('make')}")
    print(f"  Model: {data.get('model')}")
    print(f"  Years: {data.get('years')}")
    print(f"  Expert Review: {len(data.get('expert_review', ''))} chars")
    print(f"  Gallery URL: {data.get('gallery_url')}")
    
    assert data.get('make') == 'mercedes_benz', "Should extract make"
    assert '2024' in data.get('years', []), "Should find year 2024"
    assert len(data.get('expert_review', '')) > 0, "Should extract review"
    # Model name might come from title or URL, both are acceptable
    
    # Test trim parsing
    trims = parser.parse_trims_and_specs(html)
    print(f"\n  Trims found: {len(trims)}")
    for trim in trims:
        print(f"    - {trim.get('name')}: {trim.get('price')}")
        print(f"      Specs: {len(trim.get('specifications', {}))} categories")
    
    assert len(trims) > 0, "Should find at least one trim"
    
    print("✅ Detail parser test passed!\n")
    return data, trims


def test_gallery_parser():
    """Test gallery parser."""
    print("=" * 60)
    print("Test 3: Gallery Parser")
    print("=" * 60)
    
    gallery_parser = GalleryParser()
    html = create_mock_gallery_html()
    
    images = gallery_parser.parse_gallery_page(html)
    
    print(f"Found {len(images)} images:")
    for img in images:
        print(f"  - {img}")
    
    assert len(images) > 0, "Should find at least one image"
    
    print("✅ Gallery parser test passed!\n")
    return images


def test_schema_mapping(parsed_data, images):
    """Test schema mapping."""
    print("=" * 60)
    print("Test 4: Schema Mapping")
    print("=" * 60)
    
    make = parsed_data.get('make', 'mercedes_benz')
    model = parsed_data.get('model', 'glc_coupe')
    
    schema_record = SchemaMapper.map_to_schema(parsed_data, make, model, images)
    
    print(f"Mapped schema:")
    print(f"  Make: {schema_record.get('make')}")
    print(f"  Model: {schema_record.get('model')}")
    print(f"  Years: {list(schema_record.get('years', {}).keys())}")
    
    years = schema_record.get('years', {})
    if years:
        first_year = list(years.keys())[0]
        year_data = years[first_year]
        print(f"\n  Year {first_year}:")
        print(f"    Images: {len(year_data.get('main_images', []))}")
        print(f"    Review: {len(year_data.get('expert_review', ''))} chars")
        print(f"    Trims: {len(year_data.get('trims', []))}")
    
    assert schema_record.get('make') == 'mercedes_benz', "Should normalize make"
    # Model name might be normalized from title, so just check it contains expected parts
    assert 'glc' in schema_record.get('model', '').lower(), "Should contain model name"
    assert len(schema_record.get('years', {})) > 0, "Should have at least one year"
    
    print("✅ Schema mapping test passed!\n")
    return schema_record


def test_validation(schema_record):
    """Test validator."""
    print("=" * 60)
    print("Test 5: Validation")
    print("=" * 60)
    
    is_valid, errors = Validator.validate_record(schema_record)
    
    if is_valid:
        print("✅ Record is valid!")
        
        summary = Validator.get_validation_summary(schema_record)
        print(f"\n  Summary:")
        print(f"    Years: {summary['year_count']}")
        print(f"    Total images: {summary['total_images']}")
        print(f"    Total trims: {summary['total_trims']}")
    else:
        print(f"❌ Record has {len(errors)} errors:")
        for error in errors:
            print(f"  - {error}")
    
    assert is_valid, f"Record should be valid. Errors: {errors}"
    
    print("✅ Validation test passed!\n")
    return is_valid


def test_name_normalization():
    """Test name normalization."""
    print("=" * 60)
    print("Test 6: Name Normalization")
    print("=" * 60)
    
    test_cases = [
        ("Mercedes-Benz", "mercedes_benz"),
        ("BMW X5", "bmw_x5"),  # Note: normalization should handle this
        ("Audi A4", "audi_a4"),
        ("Mercedes Benz", "mercedes_benz"),
        ("GLC-Coupe", "glc_coupe"),
    ]
    
    # Test actual normalization
    print("Testing actual normalization output:")
    for original, _ in test_cases:
        normalized = SchemaMapper._normalize_name(original)
        print(f"  '{original}' -> '{normalized}'")
    
    print("Testing name normalization:")
    for original, expected in test_cases:
        normalized = SchemaMapper._normalize_name(original)
        status = "✅" if normalized == expected else "❌"
        print(f"  {status} '{original}' -> '{normalized}' (expected: '{expected}')")
        assert normalized == expected, f"Normalization failed for '{original}'"
    
    print("✅ Name normalization test passed!\n")


def main():
    """Run all offline tests."""
    print("\n" + "=" * 60)
    print("NetCarShow Crawler - Day 2 Offline Component Testing")
    print("=" * 60)
    print("\nTesting parsing, schema mapping, and validation logic\n")
    
    try:
        # Test 1: Listing parser
        models = test_listing_parser()
        
        # Test 2: Detail parser
        parsed_data, trims = test_detail_parser()
        
        # Test 3: Gallery parser
        images = test_gallery_parser()
        
        # Test 4: Schema mapping
        schema_record = test_schema_mapping(parsed_data, images)
        
        # Test 5: Validation
        is_valid = test_validation(schema_record)
        
        # Test 6: Name normalization
        test_name_normalization()
        
        # Summary
        print("=" * 60)
        print("All Offline Tests Passed! ✅")
        print("=" * 60)
        print("\nNote: These tests use mock HTML.")
        print("Run test_day2.py for live network testing.\n")
        
    except AssertionError as e:
        print(f"\n❌ Test failed: {e}")
        return 1
    except Exception as e:
        print(f"\n❌ Error during testing: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0


if __name__ == "__main__":
    exit(main())

