# NetCarShow Vehicle Crawler

A production-ready web crawler for extracting vehicle data from [NetCarShow.com](https://www.netcarshow.com/).

## Features

- **Type-based organization**: Crawls vehicles organized by type (SUV, Sedan, etc.) and subcategories
- **Complete data extraction**: Extracts model information, years, images, reviews, trims, and specifications
- **Resume capability**: Can resume from interruptions using checkpoint system
- **Schema validation**: Ensures all records match the reference schema format
- **Multi-model detection**: Captures all model variants (including submodels) from listing pages

## Installation

1. Install Python 3.8 or higher
2. Install dependencies:
```bash
pip install -r requirements.txt
```

## Usage

### Start a fresh crawl (all categories)
```bash
python crawl.py --mode type
```

### Resume from checkpoint
```bash
python crawl.py --resume
```

### Crawl specific category
```bash
python crawl.py --category SUV --subcategory Premium
```

### Additional Options
```bash
# Custom output directory
python crawl.py --mode type --output data/custom

# Custom rate limit (seconds between requests)
python crawl.py --mode type --rate-limit 2.0

# Custom checkpoint and log directories
python crawl.py --mode type --checkpoint-dir my_checkpoints --log-dir my_logs
```

## Output Structure

Data is organized in the following structure:
```
data/
  type=SUV/
    subtype=Premium/
      mercedes_benz/
        glc_coupe.json
        glc43_amg_coupe.json
    subtype=Midsize/
      ...
  type=Sedan/
    ...
```

## Schema Format

Each model file contains:
```json
{
  "make": "mercedes_benz",
  "model": "glc_coupe",
  "years": {
    "2024": {
      "main_images": ["url1", "url2", ...],
      "expert_review": "review text or empty string",
      "trims": [
        {
          "name": "Base",
          "price": "$50000",
          "specifications": {
            "Engine": [...],
            "Safety": [...]
          }
        }
      ]
    }
  }
}
```

## Checkpointing

The crawler maintains checkpoints in `checkpoints/checkpoint.json` and `checkpoints/completed_urls.txt` to enable resume functionality. If a crawl is interrupted, you can resume from where it left off using `--resume`.

## Rate Limiting

The crawler respects the target site by limiting requests to 1-2 queries per second (default: 1.5 seconds between requests). You can adjust this with the `--rate-limit` option.

## Logging

The crawler creates structured JSON logs in `logs/crawl_YYYYMMDD.log` with timestamps, URLs, status, and errors. Failed parse attempts save HTML to `logs/errors/` for debugging.

## Error Handling

- Transient errors (timeouts, 5xx) are retried automatically
- Permanent errors (4xx) are logged and skipped
- Parse failures save raw HTML for debugging
- All errors are logged with full context

## License

Internal use only.


