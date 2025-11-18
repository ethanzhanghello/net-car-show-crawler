#!/usr/bin/env python3
"""
Script to crawl a single model page.
Usage: python3 crawl_one_page.py <url> [category] [subcategory]
"""

import sys
import os

# Add crawler directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'crawler'))

from crawler.main import Crawler


def main():
    if len(sys.argv) < 2:
        print("Usage: python3 crawl_one_page.py <url> [category] [subcategory]")
        print()
        print("Example:")
        print('  python3 crawl_one_page.py "https://www.netcarshow.com/volvo/2006-xc90/" "SUV" "Premium"')
        sys.exit(1)
    
    url = sys.argv[1]
    category = sys.argv[2] if len(sys.argv) > 2 else "Unknown"
    subcategory = sys.argv[3] if len(sys.argv) > 3 else "Unknown"
    
    print(f"Crawling single page: {url}")
    print(f"Category: {category} / Subcategory: {subcategory}")
    print()
    
    # Initialize crawler
    crawler = Crawler(output_dir="data", rate_limit=3.0)
    
    # Process the single model URL
    # Extract model info from URL if possible
    from crawler.parser import Parser
    from urllib.parse import urlparse
    parser = Parser()
    path = urlparse(url).path
    make, year, model = parser._parse_model_url(path)
    
    model_info = {
        'url': url,
        'make': make or 'unknown',
        'model': model or 'unknown',
        'year': year,
        'category': category,
        'subcategory': subcategory
    }
    
    # Process the model
    success = crawler._process_model(url, category, subcategory, model_info)
    
    if success:
        print("✅ Successfully crawled and saved!")
    else:
        print("❌ Failed to crawl page. Check logs for details.")
        sys.exit(1)


if __name__ == "__main__":
    main()

