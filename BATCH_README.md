# Batch Generation

Generate soul maps and monthly updates for multiple people at once.

## Quick Start

1. **Create a CSV file** with your batch data:
   ```csv
   Name,Date,Time,City,Country
   Aaron Joseph Thomas,1988-09-24,05:55,Akron,US
   Kevin Andrew Tippel,1987-03-23,,Columbus,US
   Tupac Amaru Shakur,1971-06-16,01:30,Los Angeles,US
   ```

2. **Run the batch generator:**
   ```bash
   python soul_map_generator.py --batch people.csv
   ```

3. **Files generated in current directory** (or use `--batch-output path/`)

## CSV Format

| Column | Required | Format | Example |
|--------|----------|--------|---------|
| **Name** | Yes | Full name | Aaron Joseph Thomas |
| **Date** | Yes | YYYY-MM-DD | 1988-09-24 |
| **Time** | No | HH:MM (24h) | 05:55 |
| **City** | No | City name | Akron |
| **Country** | No | Country code | US (default) |

## Command Options

```bash
# Generate both soul maps + monthly updates (default)
python soul_map_generator.py --batch people.csv

# Generate only soul maps
python soul_map_generator.py --batch people.csv --batch-mode soul-map

# Generate only monthly updates
python soul_map_generator.py --batch people.csv --batch-mode monthly

# Save to specific output directory
python soul_map_generator.py --batch people.csv --batch-output ./output/

# Don't auto-deploy to GitHub (just save locally)
python soul_map_generator.py --batch people.csv --no-deploy
```

## Output Files

For each person in the CSV:
- **Soul Map:** `soul-map-{name-slug}.html`
  - Example: `soul-map-aaron-joseph-thomas.html`
- **Monthly Update (current month):** `{INITIALS}{BIRTH_MONTH}{BIRTH_YEAR}-{YYYYMM}.html`
  - Example: `AJT91988-202604.html` (Aaron Joseph Thomas, April 2026)

## Example: See batch_example.csv

The repo includes `batch_example.csv` with 13 example soul maps ready to generate.

```bash
python soul_map_generator.py --batch batch_example.csv
```

Generates 26 files (13 soul maps + 13 monthly updates).

## Notes

- Leave Time, City, or Country blank if unknown — the generator handles it gracefully
- If no birth time is provided, the soul map will show "Birth time needed for full chart" for Moon/Rising/planets
- All files are generated locally first, then auto-deployed to GitHub Pages (unless `--no-deploy` is used)
- Deploy requires `GITHUB_PAT` environment variable to be set
