# Testing Guide for NetCarShow Crawler

## Overview

You can test the Day 1 and Day 2 components in two ways:
1. **Offline Testing** - Tests parsing logic with mock HTML (no network required)
2. **Live Testing** - Tests with actual NetCarShow.com website (requires network access)

## Quick Test Commands

### Offline Testing (Recommended First)

Tests all parsing, schema mapping, and validation logic without needing network access:

```bash
cd /Users/ethanzhang/Desktop/NetCarShow/NetCarShow-webscraper
python3 test_day2_offline.py
```

**What it tests:**
- ✅ Listing page parser (extracts model URLs)
- ✅ Detail page parser (extracts make, model, years, review)
- ✅ Trim and specification parser
- ✅ Gallery parser (extracts image URLs)
- ✅ Schema mapping (transforms to reference format)
- ✅ Validation (ensures records match schema)
- ✅ Name normalization

**Expected Result:** All tests should pass ✅

### Live Network Testing

Tests with actual NetCarShow.com website (requires internet connection):

```bash
cd /Users/ethanzhang/Desktop/NetCarShow/NetCarShow-webscraper
python3 test_day2.py
```

**What it tests:**
- HTTP fetcher (fetches homepage)
- Discovery system (finds categories and subcategories)
- Listing page parsing (with real HTML)
- Detail page parsing (with real HTML)
- Gallery parsing (with real HTML)
- Full end-to-end workflow

**Note:** This may fail if:
- Site is unreachable
- Site structure has changed
- Rate limiting blocks requests

### Day 1 Component Testing

Test the foundation components:

```bash
cd /Users/ethanzhang/Desktop/NetCarShow/NetCarShow-webscraper
./test_day1.sh
```

## Test Results Summary

### ✅ Offline Tests (All Passing)

All Day 2 parsing components work correctly with mock data:

1. **Listing Parser** - Successfully extracts 4 models from mock HTML
2. **Detail Parser** - Successfully extracts make, model, years, review, gallery URL
3. **Trim Parser** - Successfully extracts 2 trim categories with specifications
4. **Gallery Parser** - Successfully extracts 3 images, sorted by resolution
5. **Schema Mapping** - Successfully transforms data to reference schema format
6. **Validation** - Successfully validates records meet schema requirements
7. **Name Normalization** - Successfully normalizes all test cases

### ⚠️ Live Network Tests

Live tests require:
- Network connectivity to NetCarShow.com
- Site to be accessible and responsive
- HTML structure to match expected patterns

**Status:** Ready to test, but may need adjustments based on actual HTML structure.

## What's Working

### Day 1 Components ✅
- HTTP Fetcher with rate limiting
- Discovery system for categories/subcategories
- Checkpoint system for resume capability

### Day 2 Components ✅
- **Parser** (`parser.py`)
  - Listing page parsing with pagination support
  - Detail page parsing with year extraction
  - Trim and specification parsing
  - Handles missing data gracefully

- **Gallery Parser** (`gallery.py`)
  - Image URL extraction
  - High-resolution image filtering
  - Gallery pagination support

- **Schema Mapper** (`schema.py`)
  - Transforms parsed data to reference schema
  - Name normalization (make/model)
  - Year merging for multiple crawls

- **Validator** (`validator.py`)
  - Validates records against schema requirements
  - Checks required fields
  - Provides detailed validation summaries

## What's Not Yet Implemented

### Day 3 Components (Still TODO)
- File saving (`saver.py`)
- Main crawler orchestration (`main.py`)
- CLI interface (`crawl.py`)
- Resume from checkpoint functionality
- Structured logging

## Next Steps

1. **Test with real website** - Run `test_day2.py` when you have network access
2. **Adjust parsers** - Fine-tune HTML parsing based on actual site structure
3. **Implement Day 3** - Add file saving and main orchestration
4. **End-to-end testing** - Test full crawl workflow

## Troubleshooting

### Offline tests fail
- Check Python version (3.8+)
- Ensure all dependencies installed: `pip install -r requirements.txt`
- Check for syntax errors in parser files

### Live tests fail
- Check network connectivity
- Verify site is accessible: `curl https://www.netcarshow.com/`
- Site may have changed HTML structure (parsers may need adjustment)
- Rate limiting may be blocking requests (wait and retry)

### Parsers not extracting data
- HTML structure may differ from expected
- Check actual HTML with browser dev tools
- Adjust parser selectors in `parser.py` and `gallery.py`

