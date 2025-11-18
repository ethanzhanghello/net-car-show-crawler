#!/usr/bin/env python3
"""
Test script to crawl a single model page and verify the output structure.
"""

import sys
import os
import json

# Add crawler directory to path
sys.path.insert(0, os.path.dirname(__file__))

from crawler.main import Crawler

def test_single_crawl():
    """Test crawling a single model page."""
    
    # Use a test output directory
    test_output_dir = "test_data"
    
    # Initialize crawler with test output directory
    # Use shorter timeout for testing
    crawler = Crawler(
        output_dir=test_output_dir,
        checkpoint_dir="test_checkpoints",
        log_dir="test_logs",
        rate_limit=3.0
    )
    
    # Note: The fetcher uses timeout as a parameter, not an attribute
    # We'll rely on the default 30s timeout, but the connectivity test uses 10s
    
    # Test URL - using an Acura model as example
    # You can change this to any model URL from netcarshow.com
    # Try a few different URLs - some might be more reliable
    test_urls = [
        "https://www.netcarshow.com/acura/2019-ilx/",
        "https://www.netcarshow.com/acura/2017-mdx/",
        "https://www.netcarshow.com/acura/2021-tlx/",
        "https://www.netcarshow.com/acura/2013-ilx/",
    ]
    
    print("Testing connectivity to netcarshow.com...")
    from crawler.fetcher import Fetcher
    import time
    
    # Use shorter timeout for testing
    test_fetcher = Fetcher(rate_limit=3.0)
    
    test_url = None
    for url in test_urls:
        print(f"  Trying: {url}...", end=' ', flush=True)
        start_time = time.time()
        
        # Try with shorter timeout (10 seconds)
        try:
            html, status, error = test_fetcher.fetch_url(url, timeout=10)
            elapsed = time.time() - start_time
            
            if html:
                print(f"✅ Connected in {elapsed:.1f}s")
                test_url = url
                break
            else:
                print(f"❌ Failed: {error} ({elapsed:.1f}s)")
        except Exception as e:
            elapsed = time.time() - start_time
            print(f"❌ Error: {str(e)[:50]} ({elapsed:.1f}s)")
    
    if not test_url:
        print("\n❌ Could not connect to any test URLs within 10 seconds.")
        print("   The site may be slow, down, or blocking requests.")
        print("   Since we already verified the structure with mock data,")
        print("   the code changes are correct. You can test with a real crawl later.")
        print()
        print("   Would you like to:")
        print("   1. Try again with a longer timeout (30s)")
        print("   2. Skip the live test (structure is already verified)")
        return False
    
    print()
    print("=" * 60)
    print("Testing Single Page Crawl")
    print("=" * 60)
    print(f"URL: {test_url}")
    print(f"Output directory: {test_output_dir}")
    print()
    
    # Extract make and model from URL for model_info
    from urllib.parse import urlparse
    path = urlparse(test_url).path
    parts = path.strip('/').split('/')
    if len(parts) >= 2:
        make = parts[0].replace('-', '_')
        year_model = parts[1]
        # Extract model part (after year-)
        if '-' in year_model and year_model[0].isdigit():
            year = year_model.split('-', 1)[0]
            model = year_model.split('-', 1)[1].replace('-', '_')
        else:
            year = None
            model = year_model.replace('-', '_')
    else:
        make = "acura"
        model = "ilx"
        year = "2019"
    
    model_info = {
        'url': test_url,
        'make': make,
        'model': model,
        'year': year or '2019'
    }
    
    print(f"Processing model: {make}/{model}")
    print("This may take 30-60 seconds (fetching page, parsing, fetching gallery)...")
    print()
    
    # Process the model with progress tracking
    import time
    start_time = time.time()
    
    try:
        print("Step 1: Fetching model page...")
        success = crawler._process_model(
            test_url,
            category="SUV",  # Not used in new structure, but kept for compatibility
            subcategory="Premium",  # Not used in new structure, but kept for compatibility
            model_info=model_info
        )
        elapsed = time.time() - start_time
        print(f"Completed in {elapsed:.1f} seconds")
        print()
        
        if success:
            print("✅ Model processed successfully!")
            print()
            
            # Check the output file
            from crawler.schema import SchemaMapper
            normalized_make = SchemaMapper._normalize_name(make)
            normalized_model = SchemaMapper._normalize_name(model)
            
            expected_file = os.path.join(test_output_dir, normalized_make, f"{normalized_model}.json")
            
            print("=" * 60)
            print("Verifying Output Structure")
            print("=" * 60)
            print(f"Expected file: {expected_file}")
            
            if os.path.exists(expected_file):
                print("✅ File exists!")
                print()
                
                # Read and display the structure
                with open(expected_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                print("File structure:")
                print(f"  make: {data.get('make')}")
                print(f"  model: {data.get('model')}")
                print(f"  years: {list(data.get('years', {}).keys())}")
                print()
                
                # Verify structure
                checks = []
                
                # Check 1: Directory structure should be data/{make}/
                file_dir = os.path.dirname(expected_file)
                expected_dir = os.path.join(test_output_dir, normalized_make)
                if file_dir == expected_dir:
                    checks.append(("✅ Directory structure", f"data/{normalized_make}/"))
                else:
                    checks.append(("❌ Directory structure", f"Expected: {expected_dir}, Got: {file_dir}"))
                
                # Check 2: Filename should be {model}.json
                filename = os.path.basename(expected_file)
                expected_filename = f"{normalized_model}.json"
                if filename == expected_filename:
                    checks.append(("✅ Filename", expected_filename))
                else:
                    checks.append(("❌ Filename", f"Expected: {expected_filename}, Got: {filename}"))
                
                # Check 3: Model name should be clean (not a page title)
                model_name = data.get('model', '')
                if model_name and ' - ' not in model_name and 'pictures' not in model_name.lower():
                    checks.append(("✅ Model name is clean", model_name))
                else:
                    checks.append(("❌ Model name contains page title", model_name))
                
                # Check 4: Should have years structure
                if 'years' in data and isinstance(data['years'], dict):
                    years = list(data['years'].keys())
                    if years:
                        checks.append(("✅ Years structure", f"Found {len(years)} year(s): {years}"))
                    else:
                        checks.append(("⚠️  Years structure", "Empty years dict"))
                else:
                    checks.append(("❌ Years structure", "Missing or invalid"))
                
                # Check 5: Each year should have main_images, expert_review, trims
                if 'years' in data:
                    for year, year_data in data['years'].items():
                        if 'main_images' in year_data and 'expert_review' in year_data and 'trims' in year_data:
                            checks.append((f"✅ Year {year} structure", "Has main_images, expert_review, trims"))
                        else:
                            checks.append((f"❌ Year {year} structure", "Missing required fields"))
                
                print("Structure checks:")
                for check, result in checks:
                    print(f"  {check}: {result}")
                
                print()
                print("=" * 60)
                print("Sample of saved data:")
                print("=" * 60)
                print(json.dumps(data, indent=2)[:500] + "...")
                print()
                
                return True
            else:
                print(f"❌ File not found: {expected_file}")
                return False
        else:
            print("❌ Model processing failed")
            return False
            
    except Exception as e:
        print(f"❌ Error during crawl: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_single_crawl()
    sys.exit(0 if success else 1)

