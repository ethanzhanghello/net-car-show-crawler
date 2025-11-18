#!/usr/bin/env python3
"""
Test script for Day 2 components.
Tests parsing, gallery, schema mapping, and validation.
"""

import sys
import os

# Add crawler directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'crawler'))

from fetcher import Fetcher
from discovery import Discovery
from parser import Parser
from gallery import GalleryParser
from schema import SchemaMapper
from validator import Validator


def test_fetcher():
    """Test HTTP fetcher."""
    print("=" * 60)
    print("Testing HTTP Fetcher")
    print("=" * 60)
    
    fetcher = Fetcher(rate_limit=3.0)
    test_url = "https://www.netcarshow.com/"
    
    print(f"Fetching: {test_url}")
    html, status, error = fetcher.fetch_url(test_url)
    
    if html:
        print(f"✅ Success! Fetched {len(html)} characters")
        print(f"   Status code: {status}")
        return html
    else:
        print(f"❌ Failed: {error}")
        return None


def test_discovery(html=None):
    """Test discovery system."""
    print("\n" + "=" * 60)
    print("Testing Discovery System")
    print("=" * 60)
    
    discovery = Discovery()
    
    print("Discovering main categories...")
    categories = discovery.discover_main_categories()
    
    if categories:
        print(f"✅ Found {len(categories)} categories:")
        for cat in categories[:5]:  # Show first 5
            print(f"   - {cat['name']}: {cat['url']}")
        
        # Test subcategory discovery
        if categories:
            print(f"\nDiscovering subcategories for: {categories[0]['name']}")
            subcats = discovery.discover_subcategories(categories[0]['url'])
            print(f"✅ Found {len(subcats)} subcategories:")
            for subcat in subcats[:3]:  # Show first 3
                print(f"   - {subcat['name']}: {subcat['url']}")
            
            return categories[0]['url'] if subcats else None
    else:
        print("❌ No categories found")
        return None
    
    return None


def test_parser(listing_url=None):
    """Test parser on a listing page."""
    print("\n" + "=" * 60)
    print("Testing Parser - Listing Page")
    print("=" * 60)
    
    fetcher = Fetcher(rate_limit=3.0)
    parser = Parser()
    
    if not listing_url:
        listing_url = "https://www.netcarshow.com/explore/crossover-suv/premium/"
    
    print(f"Fetching listing page: {listing_url}")
    html = fetcher.fetch_url_simple(listing_url)
    
    if not html:
        print("❌ Failed to fetch listing page")
        return None
    
    print("Parsing listing page...")
    models = parser.parse_listing_page(html, category="SUV", subcategory="Premium")
    
    if models:
        print(f"✅ Found {len(models)} models:")
        for model in models[:5]:  # Show first 5
            print(f"   - {model['make']} {model['model']} ({model['year']})")
            print(f"     URL: {model['url']}")
        
        return models[0]['url'] if models else None
    else:
        print("❌ No models found")
        return None


def test_detail_parser(model_url=None):
    """Test parser on a model detail page."""
    print("\n" + "=" * 60)
    print("Testing Parser - Detail Page")
    print("=" * 60)
    
    fetcher = Fetcher(rate_limit=3.0)
    parser = Parser()
    
    if not model_url:
        # Use a known model URL pattern
        model_url = "https://www.netcarshow.com/mercedes-benz/2024-glc_coupe/"
    
    print(f"Fetching detail page: {model_url}")
    html = fetcher.fetch_url_simple(model_url)
    
    if not html:
        print("❌ Failed to fetch detail page")
        return None
    
    print("Parsing detail page...")
    data = parser.parse_model_detail_page(html, model_url)
    
    if data:
        print("✅ Parsed detail page:")
        print(f"   Make: {data.get('make', 'N/A')}")
        print(f"   Model: {data.get('model', 'N/A')}")
        print(f"   Years: {data.get('years', [])}")
        print(f"   Expert Review: {len(data.get('expert_review', ''))} chars")
        print(f"   Gallery URL: {data.get('gallery_url', 'N/A')}")
        
        # Test trim parsing
        print("\nParsing trims and specs...")
        trims = parser.parse_trims_and_specs(html)
        print(f"✅ Found {len(trims)} trims:")
        for trim in trims[:3]:
            print(f"   - {trim.get('name', 'N/A')}: {trim.get('price', 'N/A')}")
            spec_count = len(trim.get('specifications', {}))
            print(f"     Specifications: {spec_count} categories")
        
        return data
    else:
        print("❌ Failed to parse detail page")
        return None


def test_gallery_parser(gallery_url=None):
    """Test gallery parser."""
    print("\n" + "=" * 60)
    print("Testing Gallery Parser")
    print("=" * 60)
    
    fetcher = Fetcher(rate_limit=3.0)
    gallery_parser = GalleryParser()
    
    if not gallery_url:
        gallery_url = "https://www.netcarshow.com/mercedes-benz/2024-glc_coupe-wallpapers/"
    
    print(f"Fetching gallery: {gallery_url}")
    html = fetcher.fetch_url_simple(gallery_url)
    
    if not html:
        print("❌ Failed to fetch gallery page")
        return []
    
    print("Parsing gallery page...")
    images = gallery_parser.parse_gallery_page(html)
    
    if images:
        print(f"✅ Found {len(images)} images:")
        for img in images[:5]:  # Show first 5
            print(f"   - {img}")
        return images
    else:
        print("⚠️  No images found (may need to adjust parsing logic)")
        return []


def test_schema_mapping(parsed_data, images=None):
    """Test schema mapping."""
    print("\n" + "=" * 60)
    print("Testing Schema Mapping")
    print("=" * 60)
    
    if not parsed_data:
        print("❌ No parsed data to map")
        return None
    
    make = parsed_data.get('make', 'mercedes_benz')
    model = parsed_data.get('model', 'glc_coupe')
    
    print(f"Mapping data for: {make} {model}")
    schema_record = SchemaMapper.map_to_schema(parsed_data, make, model, images)
    
    if schema_record:
        print("✅ Schema mapping successful:")
        print(f"   Make: {schema_record.get('make')}")
        print(f"   Model: {schema_record.get('model')}")
        print(f"   Years: {list(schema_record.get('years', {}).keys())}")
        
        # Show first year details
        years = schema_record.get('years', {})
        if years:
            first_year = list(years.keys())[0]
            year_data = years[first_year]
            print(f"\n   Year {first_year}:")
            print(f"     Images: {len(year_data.get('main_images', []))}")
            print(f"     Review length: {len(year_data.get('expert_review', ''))}")
            print(f"     Trims: {len(year_data.get('trims', []))}")
        
        return schema_record
    else:
        print("❌ Schema mapping failed")
        return None


def test_validation(schema_record):
    """Test validator."""
    print("\n" + "=" * 60)
    print("Testing Validator")
    print("=" * 60)
    
    if not schema_record:
        print("❌ No schema record to validate")
        return False
    
    print("Validating record...")
    is_valid, errors = Validator.validate_record(schema_record)
    
    if is_valid:
        print("✅ Record is valid!")
        
        # Get summary
        summary = Validator.get_validation_summary(schema_record)
        print(f"\n   Summary:")
        print(f"     Years: {summary['year_count']}")
        print(f"     Total images: {summary['total_images']}")
        print(f"     Total trims: {summary['total_trims']}")
    else:
        print(f"❌ Record has {len(errors)} validation errors:")
        for error in errors[:5]:  # Show first 5 errors
            print(f"   - {error}")
    
    return is_valid


def main():
    """Run all tests."""
    print("\n" + "=" * 60)
    print("NetCarShow Crawler - Day 2 Component Testing")
    print("=" * 60)
    print("\nNote: This requires network access to NetCarShow.com")
    print("Some tests may fail if the site is unreachable.\n")
    
    try:
        # Test 1: Fetcher
        html = test_fetcher()
        
        # Test 2: Discovery
        listing_url = test_discovery(html)
        
        # Test 3: Parser - Listing
        model_url = test_parser(listing_url)
        
        # Test 4: Parser - Detail
        parsed_data = test_detail_parser(model_url)
        
        # Test 5: Gallery Parser
        gallery_url = parsed_data.get('gallery_url') if parsed_data else None
        images = test_gallery_parser(gallery_url)
        
        # Test 6: Schema Mapping
        schema_record = test_schema_mapping(parsed_data, images)
        
        # Test 7: Validation
        is_valid = test_validation(schema_record)
        
        # Summary
        print("\n" + "=" * 60)
        print("Test Summary")
        print("=" * 60)
        print(f"✅ Fetcher: {'Working' if html else 'Failed'}")
        print(f"✅ Discovery: {'Working' if listing_url else 'Failed'}")
        print(f"✅ Parser (Listing): {'Working' if model_url else 'Failed'}")
        print(f"✅ Parser (Detail): {'Working' if parsed_data else 'Failed'}")
        print(f"✅ Gallery Parser: {'Working' if images else 'Partial/Failed'}")
        print(f"✅ Schema Mapping: {'Working' if schema_record else 'Failed'}")
        print(f"✅ Validation: {'Passed' if is_valid else 'Failed'}")
        
        if schema_record and is_valid:
            print("\n🎉 All Day 2 components are working!")
        else:
            print("\n⚠️  Some components need adjustment based on actual HTML structure")
        
    except KeyboardInterrupt:
        print("\n\n⚠️  Test interrupted by user")
    except Exception as e:
        print(f"\n\n❌ Error during testing: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()

