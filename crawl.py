#!/usr/bin/env python3
"""
CLI interface for NetCarShow crawler.
Main entry point for running crawls.
"""

import argparse
import sys
import os

# Add crawler directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'crawler'))

from crawler.main import Crawler


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description='NetCarShow Vehicle Crawler',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Start fresh crawl of all categories
  python crawl.py --mode type

  # Resume from checkpoint
  python crawl.py --resume

  # Crawl specific category
  python crawl.py --category SUV --subcategory Premium

  # Custom output directory
  python crawl.py --mode type --output data/custom
        """
    )
    
    # Mode selection (mutually exclusive, but not required if category/subcategory provided)
    mode_group = parser.add_mutually_exclusive_group(required=False)
    mode_group.add_argument(
        '--mode',
        choices=['type'],
        help='Crawl mode: "type" crawls all type-based categories'
    )
    mode_group.add_argument(
        '--resume',
        action='store_true',
        help='Resume crawl from checkpoint'
    )
    
    # Category options
    parser.add_argument(
        '--category',
        type=str,
        help='Specific category to crawl (e.g., "SUV", "Sedan")'
    )
    parser.add_argument(
        '--subcategory',
        type=str,
        help='Specific subcategory to crawl (e.g., "Premium", "Midsize")'
    )
    
    # Options
    parser.add_argument(
        '--output',
        type=str,
        default='data',
        help='Output directory for JSON files (default: data)'
    )
    parser.add_argument(
        '--checkpoint-dir',
        type=str,
        default='checkpoints',
        help='Checkpoint directory (default: checkpoints)'
    )
    parser.add_argument(
        '--log-dir',
        type=str,
        default='logs',
        help='Log directory (default: logs)'
    )
    parser.add_argument(
        '--rate-limit',
        type=float,
        default=1.5,
        help='Rate limit in seconds between requests (default: 1.5)'
    )
    
    args = parser.parse_args()
    
    # Validate arguments
    if args.category and not args.subcategory:
        parser.error("--category requires --subcategory")
    if args.subcategory and not args.category:
        parser.error("--subcategory requires --category")
    
    # Ensure at least one mode is specified
    if not args.resume and not args.mode and not (args.category and args.subcategory):
        parser.error("Must specify one of: --mode type, --resume, or --category/--subcategory")
    
    # Initialize crawler
    try:
        crawler = Crawler(
            output_dir=args.output,
            checkpoint_dir=args.checkpoint_dir,
            log_dir=args.log_dir,
            rate_limit=args.rate_limit
        )
    except Exception as e:
        print(f"❌ Failed to initialize crawler: {e}", file=sys.stderr)
        sys.exit(1)
    
    # Run crawl based on mode
    try:
        if args.resume:
            print("🔄 Resuming crawl from checkpoint...")
            stats = crawler.resume_crawl()
        
        elif args.category and args.subcategory:
            print(f"🚗 Crawling category: {args.category} / {args.subcategory}")
            stats = crawler.crawl_category(args.category, args.subcategory)
        
        elif args.mode == 'type':
            print("🚗 Starting full crawl of all categories...")
            stats = crawler.crawl_all()
        
        else:
            parser.error("Invalid mode or missing required arguments")
        
        # Print summary
        print("\n" + "=" * 60)
        print("Crawl Complete!")
        print("=" * 60)
        print(f"Discovered: {stats.get('discovered', 0)}")
        print(f"Parsed: {stats.get('parsed', 0)}")
        print(f"Saved: {stats.get('saved', 0)}")
        print(f"Failed: {stats.get('failed', 0)}")
        print(f"Skipped: {stats.get('skipped', 0)}")
        print("=" * 60)
        
        if stats.get('failed', 0) > 0:
            print(f"\n⚠️  {stats.get('failed', 0)} URLs failed. Check logs for details.")
            sys.exit(1)
        else:
            print("\n✅ All URLs processed successfully!")
            sys.exit(0)
    
    except KeyboardInterrupt:
        print("\n\n⚠️  Crawl interrupted by user")
        print("💾 Progress saved to checkpoint. Use --resume to continue.")
        sys.exit(130)
    
    except Exception as e:
        print(f"\n❌ Crawl failed: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()

