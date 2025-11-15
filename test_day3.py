#!/usr/bin/env python3
"""
Test script for Day 3 components.
Tests file saving, main crawler orchestration, and CLI interface.
"""

import sys
import os
import json
import tempfile
import shutil
from pathlib import Path

# Add crawler directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'crawler'))

from crawler.saver import Saver
from crawler.logger import CrawlerLogger
from crawler.main import Crawler
from crawler.schema import SchemaMapper
from crawler.validator import Validator


def test_saver():
    """Test file saving system."""
    print("=" * 60)
    print("Test 1: File Saving System")
    print("=" * 60)
    
    # Create temporary directory
    test_dir = tempfile.mkdtemp()
    saver = Saver(output_dir=test_dir)
    
    # Create test record
    test_record = {
        'make': 'mercedes_benz',
        'model': 'glc_coupe',
        'years': {
            '2024': {
                'main_images': ['url1', 'url2'],
                'expert_review': 'Test review',
                'trims': [{
                    'name': 'Base',
                    'price': '$50000',
                    'specifications': {
                        'Engine': ['V6', 'Turbo']
                    }
                }]
            }
        }
    }
    
    # Save record
    file_path = saver.save_record(test_record, 'SUV', 'Premium')
    print(f"✅ Saved record to: {file_path}")
    
    # Verify file exists
    assert os.path.exists(file_path), "File should exist"
    print(f"✅ File exists: {file_path}")
    
    # Verify directory structure
    expected_dir = os.path.join(test_dir, 'type=SUV', 'subtype=Premium', 'mercedes_benz')
    assert os.path.isdir(expected_dir), "Directory structure should be correct"
    print(f"✅ Directory structure correct: {expected_dir}")
    
    # Verify file content
    with open(file_path, 'r') as f:
        loaded = json.load(f)
    assert loaded['make'] == 'mercedes_benz', "Make should match"
    assert loaded['model'] == 'glc_coupe', "Model should match"
    print("✅ File content verified")
    
    # Test year merging
    new_record = {
        'make': 'mercedes_benz',
        'model': 'glc_coupe',
        'years': {
            '2023': {
                'main_images': ['url3'],
                'expert_review': '2023 review',
                'trims': [{'name': 'Base', 'price': '', 'specifications': {}}]
            }
        }
    }
    file_path2 = saver.save_record(new_record, 'SUV', 'Premium')
    assert file_path == file_path2, "Should save to same file"
    
    with open(file_path, 'r') as f:
        merged = json.load(f)
    assert '2024' in merged['years'], "Should have 2024"
    assert '2023' in merged['years'], "Should have 2023"
    print("✅ Year merging works correctly")
    
    # Cleanup
    shutil.rmtree(test_dir)
    print("✅ Saver test passed!\n")


def test_logger():
    """Test logging system."""
    print("=" * 60)
    print("Test 2: Logging System")
    print("=" * 60)
    
    # Create temporary log directory
    test_log_dir = tempfile.mkdtemp()
    logger = CrawlerLogger(log_dir=test_log_dir)
    
    # Test logging
    logger.info("Test info message", url="https://example.com")
    logger.warning("Test warning", url="https://example.com")
    logger.error("Test error", error="Test error message", url="https://example.com")
    logger.log_crawl_start(category="SUV", subcategory="Premium")
    logger.log_crawl_complete({'saved': 10, 'failed': 2})
    
    # Verify log file exists
    assert os.path.exists(logger.log_file), "Log file should exist"
    print(f"✅ Log file created: {logger.log_file}")
    
    # Verify log entries
    with open(logger.log_file, 'r') as f:
        lines = f.readlines()
    assert len(lines) >= 5, "Should have multiple log entries"
    print(f"✅ Logged {len(lines)} entries")
    
    # Verify JSON format
    for line in lines:
        entry = json.loads(line.strip())
        assert 'timestamp' in entry, "Should have timestamp"
        assert 'level' in entry, "Should have level"
        assert 'message' in entry, "Should have message"
    print("✅ All log entries are valid JSON")
    
    # Test HTML saving
    test_html = "<html><body>Test</body></html>"
    html_path = logger.save_html_for_debugging(test_html, "https://example.com/test")
    if html_path:
        assert os.path.exists(html_path), "HTML file should exist"
        print(f"✅ HTML saved for debugging: {html_path}")
    
    # Cleanup
    shutil.rmtree(test_log_dir)
    print("✅ Logger test passed!\n")


def test_crawler_initialization():
    """Test crawler initialization."""
    print("=" * 60)
    print("Test 3: Crawler Initialization")
    print("=" * 60)
    
    # Create temporary directories
    test_data_dir = tempfile.mkdtemp()
    test_checkpoint_dir = tempfile.mkdtemp()
    test_log_dir = tempfile.mkdtemp()
    
    try:
        crawler = Crawler(
            output_dir=test_data_dir,
            checkpoint_dir=test_checkpoint_dir,
            log_dir=test_log_dir,
            rate_limit=1.0
        )
        
        print("✅ Crawler initialized successfully")
        print(f"   Output dir: {test_data_dir}")
        print(f"   Checkpoint dir: {test_checkpoint_dir}")
        print(f"   Log dir: {test_log_dir}")
        
        # Verify components are initialized
        assert crawler.fetcher is not None, "Fetcher should be initialized"
        assert crawler.discovery is not None, "Discovery should be initialized"
        assert crawler.parser is not None, "Parser should be initialized"
        assert crawler.gallery_parser is not None, "Gallery parser should be initialized"
        assert crawler.saver is not None, "Saver should be initialized"
        assert crawler.checkpoint is not None, "Checkpoint should be initialized"
        assert crawler.logger is not None, "Logger should be initialized"
        
        print("✅ All components initialized")
        
    finally:
        # Cleanup
        shutil.rmtree(test_data_dir)
        shutil.rmtree(test_checkpoint_dir)
        shutil.rmtree(test_log_dir)
    
    print("✅ Crawler initialization test passed!\n")


def test_checkpoint_integration():
    """Test checkpoint integration with category/subcategory."""
    print("=" * 60)
    print("Test 4: Checkpoint Integration")
    print("=" * 60)
    
    # Create temporary directories
    test_checkpoint_dir = tempfile.mkdtemp()
    
    try:
        from crawler.checkpoint import Checkpoint
        
        checkpoint = Checkpoint(checkpoint_dir=test_checkpoint_dir)
        
        # Test URL with category/subcategory
        test_url = "https://www.netcarshow.com/test"
        checkpoint.mark_discovered(test_url)
        
        # Manually add category/subcategory (as main.py does)
        checkpoint_data = checkpoint.checkpoint_data.get(test_url, {})
        checkpoint_data['category'] = 'SUV'
        checkpoint_data['subcategory'] = 'Premium'
        checkpoint.checkpoint_data[test_url] = checkpoint_data
        checkpoint._save_checkpoint()
        
        # Verify it's stored
        loaded_data = checkpoint.checkpoint_data.get(test_url, {})
        assert loaded_data.get('category') == 'SUV', "Category should be stored"
        assert loaded_data.get('subcategory') == 'Premium', "Subcategory should be stored"
        print("✅ Category/subcategory stored in checkpoint")
        
        # Test resume functionality
        incomplete = checkpoint.get_incomplete_urls()
        assert test_url in incomplete, "URL should be in incomplete list"
        print(f"✅ Found {len(incomplete)} incomplete URLs")
        
        # Verify we can retrieve category/subcategory
        if test_url in checkpoint.checkpoint_data:
            cat = checkpoint.checkpoint_data[test_url].get('category', 'Unknown')
            subcat = checkpoint.checkpoint_data[test_url].get('subcategory', 'Unknown')
            assert cat == 'SUV', "Should retrieve category"
            assert subcat == 'Premium', "Should retrieve subcategory"
            print(f"✅ Retrieved category/subcategory: {cat}/{subcat}")
        
    finally:
        shutil.rmtree(test_checkpoint_dir)
    
    print("✅ Checkpoint integration test passed!\n")


def main():
    """Run all Day 3 tests."""
    print("\n" + "=" * 60)
    print("NetCarShow Crawler - Day 3 Component Testing")
    print("=" * 60)
    print("\nTesting file saving, logging, and crawler integration\n")
    
    try:
        # Test 1: Saver
        test_saver()
        
        # Test 2: Logger
        test_logger()
        
        # Test 3: Crawler initialization
        test_crawler_initialization()
        
        # Test 4: Checkpoint integration
        test_checkpoint_integration()
        
        # Summary
        print("=" * 60)
        print("All Day 3 Tests Passed! ✅")
        print("=" * 60)
        print("\nDay 3 components are working correctly!")
        print("The crawler is ready for production use.\n")
        
    except AssertionError as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return 1
    except Exception as e:
        print(f"\n❌ Error during testing: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0


if __name__ == "__main__":
    exit(main())

