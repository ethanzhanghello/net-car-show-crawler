# NetCarShow Site Structure Exploration

## Main Categories (Type-Based)
From homepage `/`:
- `/explore/coupe/` - Coupes
- `/explore/sedan/` - Sedans
- `/explore/pickup/` - Pickups
- `/explore/cabrio/` - Cabriolets
- `/explore/estate-wagon/` - Wagons
- `/explore/crossover-suv/` - SUVs
- `/explore/concept/` - Concepts
- `/explore/hatchback/` - Hatchbacks
- `/explore/mpv/` - MPVs

## Subcategories Pattern
Example: `/explore/crossover-suv/` has subcategories:
- `/explore/crossover-suv/premium/` - Premium SUV
- `/explore/crossover-suv/midsize/` - Midsize SUV
- `/explore/crossover-suv/compact/` - Compact SUV
- `/explore/crossover-suv/small/` - Small SUV

## Model URL Pattern
- Format: `/{make}/{year}-{model}/`
- Example: `/mercedes-benz/2024-glc_coupe/`
- Gallery: `/{make}/{year}-{model}-wallpapers/`

## Listing Page Structure
- Multiple models grouped by base model
- Each model has: year, name, description, link
- Pagination: "SHOW MORE" links or next page indicators

## Detail Page Structure
- Model name, year, description
- Gallery link
- May have multiple years on same page
- Trim information (if available)


