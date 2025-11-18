#!/usr/bin/env python3
"""Test crawl on a different brand and car type."""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from crawler.main import Crawler
import json

def test_different_model():
    """Test crawling a different brand and car type."""
    
    # Test with BMW X5 (SUV) - different brand and type
    test_url = "https://www.netcarshow.com/bmw/2024-x5/"
    test_output_dir = "test_data"
    
    print("=" * 60)
    print("Testing Different Brand and Car Type")
    print("=" * 60)
    print(f"URL: {test_url}")
    print(f"Brand: BMW")
    print(f"Model: X5 (SUV)")
    print(f"Output directory: {test_output_dir}")
    print()
    
    # Initialize crawler
    crawler = Crawler(
        output_dir=test_output_dir,
        checkpoint_dir="test_checkpoints",
        log_dir="test_logs",
        rate_limit=3.0
    )
    
    print("Processing model...")
    print("This may take 30-60 seconds (fetching page, parsing, fetching gallery)...")
    print()
    
    try:
        # Extract model info from URL
        from crawler.parser import Parser
        from urllib.parse import urlparse
        parser = Parser()
        path = urlparse(test_url).path
        make, year, model = parser._parse_model_url(path)
        
        model_info = {
            'url': test_url,
            'make': make or 'unknown',
            'model': model or 'unknown',
            'year': year,
            'category': 'SUV',  # X5 is an SUV
            'subcategory': 'Premium'
        }
        
        # Process the model
        result = crawler._process_model(test_url, 'SUV', 'Premium', model_info)
        
        if result:
            print("✅ Model processed successfully!")
            print()
            
            # Verify output
            print("=" * 60)
            print("Verifying Output")
            print("=" * 60)
            
            # Expected file path
            expected_file = os.path.join(test_output_dir, "bmw", "x5.json")
            
            if os.path.exists(expected_file):
                print(f"✅ File exists: {expected_file}")
                
                # Load and display structure
                with open(expected_file, 'r') as f:
                    data = json.load(f)
                
                print(f"\nFile structure:")
                print(f"  make: {data.get('make')}")
                print(f"  model: {data.get('model')}")
                print(f"  years: {list(data.get('years', {}).keys())[:5]}... (showing first 5)")
                
                # Check a specific year
                years = data.get('years', {})
                if years:
                    first_year = list(years.keys())[0]
                    year_data = years[first_year]
                    
                    print(f"\nYear {first_year} structure:")
                    print(f"  ✅ Has main_images: {len(year_data.get('main_images', []))} images")
                    print(f"  ✅ Has expert_review: {bool(year_data.get('expert_review'))}")
                    print(f"  ✅ Has trims: {len(year_data.get('trims', []))} trim(s)")
                    
                    # Show specifications
                    if year_data.get('trims'):
                        trim = year_data['trims'][0]
                        specs = trim.get('specifications', {})
                        print(f"\nSpecifications categories: {list(specs.keys())}")
                        print(f"\nSample specifications:")
                        for category, items in list(specs.items())[:3]:
                            print(f"  {category}: {len(items)} items")
                            if items:
                                print(f"    - {items[0][:80]}...")
                
                print(f"\n✅ Test completed successfully!")
                print(f"Output file: {expected_file}")
                
            else:
                print(f"❌ Expected file not found: {expected_file}")
                
        else:
            print("❌ Failed to process model")
            
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    test_different_model()

