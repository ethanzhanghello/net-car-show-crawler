"""
Main crawler orchestration - ties all components together.
"""

import os
import sys
from typing import List, Dict, Optional

# Handle both package import and direct import
try:
    from .fetcher import Fetcher
    from .discovery import Discovery
    from .parser import Parser
    from .gallery import GalleryParser
    from .schema import SchemaMapper
    from .validator import Validator
    from .saver import Saver
    from .checkpoint import Checkpoint
    from .logger import CrawlerLogger
except ImportError:
    # If running as script, add parent directory to path
    sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
    from crawler.fetcher import Fetcher
    from crawler.discovery import Discovery
    from crawler.parser import Parser
    from crawler.gallery import GalleryParser
    from crawler.schema import SchemaMapper
    from crawler.validator import Validator
    from crawler.saver import Saver
    from crawler.checkpoint import Checkpoint
    from crawler.logger import CrawlerLogger


class Crawler:
    """Main crawler that orchestrates all components."""
    
    def __init__(self, output_dir: str = "data", checkpoint_dir: str = "checkpoints", 
                 log_dir: str = "logs", rate_limit: float = 3.0):
        """
        Initialize crawler.
        
        Args:
            output_dir: Directory for saved JSON files
            checkpoint_dir: Directory for checkpoint files
            log_dir: Directory for log files
            rate_limit: Seconds between requests
        """
        self.fetcher = Fetcher(rate_limit=rate_limit)
        self.discovery = Discovery(fetcher=self.fetcher)
        self.parser = Parser()
        self.gallery_parser = GalleryParser()
        self.saver = Saver(output_dir=output_dir)
        self.checkpoint = Checkpoint(checkpoint_dir=checkpoint_dir)
        self.logger = CrawlerLogger(log_dir=log_dir)
        
        self.output_dir = output_dir
    
    def crawl_category(self, category: str, subcategory: str) -> Dict[str, int]:
        """
        Crawl a specific category and subcategory.
        
        Args:
            category: Category name (e.g., "SUV")
            subcategory: Subcategory name (e.g., "Premium")
            
        Returns:
            Dictionary with statistics (discovered, parsed, saved, failed)
        """
        self.logger.log_crawl_start(category=category, subcategory=subcategory)
        
        stats = {
            'discovered': 0,
            'parsed': 0,
            'saved': 0,
            'failed': 0,
            'skipped': 0
        }
        
        try:
            # Discover subcategory URL
            categories = self.discovery.discover_main_categories()
            category_url = None
            
            for cat in categories:
                cat_name = cat.get('name', '').lower()
                cat_type = cat.get('type', '').lower()
                if cat_name == category.lower() or cat_type == category.lower() or category.lower() in cat_name or category.lower() in cat_type:
                    subcats = self.discovery.discover_subcategories(cat['url'])
                    for subcat in subcats:
                        subcat_name = subcat.get('name', '').lower()
                        subcat_type = subcat.get('subtype', '').lower()
                        if (subcat_name == subcategory.lower() or 
                            subcat_type == subcategory.lower() or
                            subcategory.lower() in subcat_name or 
                            subcategory.lower() in subcat_type):
                            category_url = subcat['url']
                            break
                    if category_url:
                        break
            
            if not category_url:
                self.logger.error(f"Could not find category/subcategory: {category}/{subcategory}")
                return stats
            
            # Discover all listing pages (handle pagination)
            listing_urls = self._discover_all_listing_pages(category_url)
            self.logger.info(f"Found {len(listing_urls)} listing pages", url=category_url)
            
            # Process each listing page
            for listing_url in listing_urls:
                models = self._process_listing_page(listing_url, category, subcategory)
                stats['discovered'] += len(models)
                
                print(f"\n🚗 Found {len(models)} total models. Processing...")
                
                # Process each model
                for idx, model_info in enumerate(models, 1):
                    model_url = model_info['url']
                    make_model = f"{model_info.get('make', 'unknown')}/{model_info.get('model', 'unknown')}"
                    
                    # Check checkpoint
                    if self.checkpoint.is_completed(model_url):
                        stats['skipped'] += 1
                        if idx % 10 == 0 or idx == len(models):
                            print(f"  [{idx}/{len(models)}] Skipped (already completed)")
                        self.logger.debug(f"Skipping already completed URL", url=model_url)
                        continue
                    
                    # Show progress every 10 models or on last one
                    if idx % 10 == 0 or idx == len(models):
                        print(f"  [{idx}/{len(models)}] Processing {make_model}...")
                    
                    # Mark as discovered (store category/subcategory context)
                    self.checkpoint.mark_discovered(model_url)
                    # Store category/subcategory in checkpoint for resume
                    checkpoint_data = self.checkpoint.checkpoint_data.get(model_url, {})
                    checkpoint_data['category'] = category
                    checkpoint_data['subcategory'] = subcategory
                    self.checkpoint.checkpoint_data[model_url] = checkpoint_data
                    self.checkpoint._save_checkpoint()
                    
                    try:
                        # Process model
                        success = self._process_model(model_url, category, subcategory, model_info)
                        
                        if success:
                            stats['saved'] += 1
                            self.checkpoint.mark_saved(model_url)
                        else:
                            stats['failed'] += 1
                            self.checkpoint.mark_failed(model_url, "Processing failed")
                    
                    except Exception as e:
                        stats['failed'] += 1
                        self.checkpoint.mark_failed(model_url, str(e))
                        self.logger.log_parse_error(model_url, str(e))
        
        except Exception as e:
            self.logger.error("Crawl category failed", error=str(e), 
                            category=category, subcategory=subcategory)
        
        stats['parsed'] = stats['saved'] + stats['failed']  # All processed URLs
        
        # Log completeness statistics
        completeness_pct = (stats['saved'] / stats['discovered'] * 100) if stats['discovered'] > 0 else 0
        self.logger.info(f"Completeness: {stats['saved']}/{stats['discovered']} models saved ({completeness_pct:.1f}%)",
                        category=category, subcategory=subcategory)
        
        self.logger.log_crawl_complete(stats)
        
        return stats
    
    def _discover_all_listing_pages(self, initial_url: str) -> List[str]:
        """
        Discover all listing pages including pagination.
        
        Args:
            initial_url: Initial listing page URL
            
        Returns:
            List of all listing page URLs
        """
        listing_urls = [initial_url]
        current_url = initial_url
        seen = {initial_url}
        max_pages = 100  # Safety limit
        
        for _ in range(max_pages):
            html = self.fetcher.fetch_url_simple(current_url)
            if not html:
                break
            
            # Get next page URL
            next_url = self.parser.get_next_page_url(html, current_url)
            
            if not next_url or next_url in seen:
                break
            
            seen.add(next_url)
            listing_urls.append(next_url)
            current_url = next_url
        
        return listing_urls
    
    def _process_listing_page(self, listing_url: str, category: str, subcategory: str) -> List[Dict]:
        """
        Process a listing page to extract all model URLs.
        
        The listing page shows make links (like /bmw/, /mercedes-benz/), so we need to:
        1. Extract all make links from the listing page
        2. For each make, fetch the make page and extract model URLs
        
        Args:
            listing_url: URL of listing page
            category: Category name
            subcategory: Subcategory name
            
        Returns:
            List of model info dicts
        """
        html = self.fetcher.fetch_url_simple(listing_url)
        if not html:
            self.logger.warning("Failed to fetch listing page", url=listing_url)
            return []
        
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(html, 'lxml')
        all_models = []
        
        # First, try to find model URLs directly on the listing page
        direct_models = self.parser.parse_listing_page(html, category, subcategory)
        if direct_models:
            all_models.extend(direct_models)
            self.logger.info(f"Found {len(direct_models)} models directly on listing page", url=listing_url)
        
        # Also extract make links and navigate through them
        # Make links are like /bmw/, /mercedes-benz/ (2 path segments, ends with /)
        make_links = []
        for link in soup.find_all('a', href=True):
            href = link.get('href', '')
            # Make links: /make/ (not /explore/, not model URLs)
            if (href.startswith('/') and 
                href.count('/') == 2 and 
                href.endswith('/') and 
                not href.startswith('/explore') and
                not self.parser._is_model_url(href)):
                full_make_url = f"https://www.netcarshow.com{href}"
                if full_make_url not in make_links:
                    make_links.append(full_make_url)
        
        self.logger.info(f"Found {len(make_links)} make links on listing page", url=listing_url)
        print(f"📋 Processing {len(make_links)} make pages... (this may take a few minutes)")
        
        # For each make, fetch the make page and extract models
        for idx, make_url in enumerate(make_links, 1):
            try:
                print(f"  [{idx}/{len(make_links)}] Fetching {make_url.split('/')[-2]}...", end=' ', flush=True)
                make_html = self.fetcher.fetch_url_simple(make_url)
                if make_html:
                    make_models = self.parser.parse_listing_page(make_html, category, subcategory)
                    if make_models:
                        all_models.extend(make_models)
                        print(f"✅ Found {len(make_models)} models")
                        self.logger.debug(f"Found {len(make_models)} models from {make_url}")
                    else:
                        print("✅ (no models)")
                else:
                    print("⚠️  (failed)")
            except Exception as e:
                print(f"⚠️  (error: {str(e)[:50]})")
                self.logger.warning(f"Failed to process make page {make_url}", error=str(e))
        
        # Remove duplicates based on URL
        seen_urls = set()
        unique_models = []
        for model in all_models:
            url = model.get('url', '')
            if url and url not in seen_urls:
                seen_urls.add(url)
                unique_models.append(model)
        
        self.logger.info(f"Extracted {len(unique_models)} unique models from listing page", 
                        url=listing_url, 
                        total_found=len(all_models),
                        unique_models=len(unique_models))
        
        return unique_models
    
    def _process_model(self, model_url: str, category: str, subcategory: str, 
                      model_info: Optional[Dict] = None) -> bool:
        """
        Process a single model URL through the full pipeline.
        
        Args:
            model_url: URL of model detail page
            category: Category name
            subcategory: Subcategory name
            model_info: Optional model info from listing page
            
        Returns:
            True if successfully saved, False otherwise
        """
        html = None
        try:
            # Fetch detail page
            html = self.fetcher.fetch_url_simple(model_url)
            if not html:
                self.logger.error("Failed to fetch model page", url=model_url)
                return False
            
            # Parse detail page
            parsed_data = self.parser.parse_model_detail_page(html, model_url)
            if not parsed_data or not parsed_data.get('make') or not parsed_data.get('model'):
                self.logger.error("Failed to parse model page or missing required fields", url=model_url)
                # Save HTML for debugging
                if html:
                    html_path = self.logger.save_html_for_debugging(html, model_url)
                    if html_path:
                        self.logger.debug(f"Saved HTML for debugging: {html_path}", url=model_url)
                return False
            
            self.checkpoint.mark_parsed(model_url)
            self.logger.log_url_parsed(model_url, 
                                     make=parsed_data.get('make'),
                                     model=parsed_data.get('model'))
            
            # Parse trims and specs
            trims = self.parser.parse_trims_and_specs(html)
            parsed_data['trims'] = trims
            
            # Determine normalized identifiers for gallery filtering
            make_for_filter = parsed_data.get('make') or (model_info.get('make') if model_info else None)
            model_for_filter = (model_info.get('model') if model_info else None) or parsed_data.get('model')
            year_for_filter = None
            if model_info and model_info.get('year'):
                year_for_filter = str(model_info.get('year'))
            elif parsed_data.get('years') and len(parsed_data.get('years', [])) > 0:
                year_for_filter = str(parsed_data.get('years')[0])
            
            if make_for_filter and model_for_filter:
                from .schema import SchemaMapper
                make_for_filter = SchemaMapper._normalize_name(make_for_filter)
                model_for_filter = SchemaMapper._normalize_name(model_for_filter)
            
            detail_gallery_images = self.gallery_parser.extract_images_from_detail(
                html,
                page_url=model_url,
                fetcher=self.fetcher,
                year=year_for_filter
            )
            
            # Fetch and parse gallery
            gallery_url = parsed_data.get('gallery_url')
            images = []
            
            if gallery_url:
                gallery_html = self.fetcher.fetch_url_simple(gallery_url)
                if gallery_html:
                    images = self.gallery_parser.parse_all_gallery_pages(
                        gallery_html, gallery_url, self.fetcher,
                        make=make_for_filter, model=model_for_filter, year=year_for_filter
                    )
                    self.logger.debug(
                        f"Extracted {len(images)} images (filtered for {make_for_filter}/{model_for_filter}/{year_for_filter})",
                        url=gallery_url
                    )
            
            if images:
                if detail_gallery_images:
                    for img_url in detail_gallery_images:
                        if img_url not in images:
                            images.append(img_url)
            else:
                images = detail_gallery_images
            
            # Map to schema
            # Prefer model from URL parsing (model_info) over parsed_data
            # This ensures we get clean model names like "xc90" not "Volvo XC90 (2006) - pictures..."
            make = parsed_data.get('make') or (model_info.get('make') if model_info else None)
            # Use model from URL parsing if available (cleaner), otherwise from parsed_data
            model = (model_info.get('model') if model_info else None) or parsed_data.get('model')
            
            # Get source URL from parsed_data or model_url
            source_url = parsed_data.get('url') or model_url
            
            schema_record = SchemaMapper.map_to_schema(
                parsed_data, 
                make, 
                model, 
                images,
                category=category,
                subcategory=subcategory,
                source_url=source_url
            )
            
            # Validate
            is_valid, errors = Validator.validate_record(schema_record)
            if not is_valid:
                self.logger.error("Record validation failed", 
                                error=str(errors), url=model_url)
                return False
            
            # Save
            file_path = self.saver.save_record(schema_record, category, subcategory, make, model)
            self.logger.log_url_saved(model_url, file_path=file_path)
            
            return True
        
        except Exception as e:
            self.logger.log_parse_error(model_url, str(e))
            # Save HTML for debugging (use fetched HTML if available, otherwise fetch)
            try:
                html_for_debug = html if html else self.fetcher.fetch_url_simple(model_url)
                if html_for_debug:
                    html_path = self.logger.save_html_for_debugging(html_for_debug, model_url)
                    if html_path:
                        self.logger.debug(f"Saved HTML for debugging: {html_path}", url=model_url)
            except Exception as save_error:
                self.logger.warning(f"Failed to save HTML for debugging: {save_error}", url=model_url)
            return False
    
    def crawl_all(self) -> Dict[str, int]:
        """
        Crawl all categories and subcategories.
        
        Returns:
            Dictionary with overall statistics
        """
        self.logger.log_crawl_start()
        
        overall_stats = {
            'discovered': 0,
            'parsed': 0,
            'saved': 0,
            'failed': 0,
            'skipped': 0
        }
        
        # Discover all categories
        categories = self.discovery.discover_main_categories()
        self.logger.info(f"Found {len(categories)} main categories")
        
        for category_info in categories:
            category = category_info.get('name', category_info.get('type', ''))
            category_url = category_info['url']
            
            # Discover subcategories
            subcategories = self.discovery.discover_subcategories(category_url)
            self.logger.info(f"Found {len(subcategories)} subcategories for {category}")
            
            for subcat_info in subcategories:
                subcategory = subcat_info.get('name', subcat_info.get('subtype', ''))
                
                # Crawl this category/subcategory
                stats = self.crawl_category(category, subcategory)
                
                # Accumulate stats
                for key in overall_stats:
                    overall_stats[key] += stats.get(key, 0)
        
        # Log overall completeness statistics
        overall_completeness = (overall_stats['saved'] / overall_stats['discovered'] * 100) if overall_stats['discovered'] > 0 else 0
        self.logger.info(f"Overall completeness: {overall_stats['saved']}/{overall_stats['discovered']} models saved ({overall_completeness:.1f}%)")
        
        self.logger.log_crawl_complete(overall_stats)
        
        return overall_stats
    
    def resume_crawl(self) -> Dict[str, int]:
        """
        Resume crawl from checkpoint.
        
        Returns:
            Dictionary with statistics
        """
        self.logger.info("Resuming crawl from checkpoint")
        
        stats = {
            'discovered': 0,
            'parsed': 0,
            'saved': 0,
            'failed': 0,
            'skipped': 0
        }
        
        # Get incomplete URLs
        incomplete_urls = self.checkpoint.get_incomplete_urls()
        self.logger.info(f"Found {len(incomplete_urls)} incomplete URLs")
        
        for url in incomplete_urls:
            status = self.checkpoint.get_status(url)
            
            if status == 'saved':
                stats['skipped'] += 1
                continue
            
            try:
                # Get category/subcategory from checkpoint if stored
                checkpoint_data = self.checkpoint.checkpoint_data.get(url, {})
                category = checkpoint_data.get('category', 'Unknown')
                subcategory = checkpoint_data.get('subcategory', 'Unknown')
                
                # Process the URL
                success = self._process_model(url, category, subcategory)
                
                if success:
                    stats['saved'] += 1
                    self.checkpoint.mark_saved(url)
                else:
                    stats['failed'] += 1
            
            except Exception as e:
                stats['failed'] += 1
                self.checkpoint.mark_failed(url, str(e))
                self.logger.log_parse_error(url, str(e))
        
        stats['parsed'] = stats['saved'] + stats['failed']
        self.logger.log_crawl_complete(stats)
        
        return stats

