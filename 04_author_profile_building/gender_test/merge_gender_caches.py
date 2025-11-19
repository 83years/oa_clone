#!/usr/bin/env python3
"""
Merge two gender cache files into one unified cache

Input files:
1. genderize_cache_converted.json - 133,537 predictions from genderize.io (no country codes)
2. gender_cache_converted.json - 154,470 predictions from genderit (88% with country codes)

Output:
- merged_gender_cache.json - Combined, deduplicated cache

Strategy:
- Merge on name (lowercase)
- For duplicates: prioritize higher probability, then genderize.io (known to be more accurate)
- Keep country codes where available
- Track which source(s) contributed to each prediction
"""

import json
import os
from collections import defaultdict

# Paths
cache_dir = '/Users/lucas/Documents/openalex_database/python/OA_clone/04_author_profile_building/gender_test'
genderize_file = os.path.join(cache_dir, 'genderize_cache.json')
genderit_file = os.path.join(cache_dir, 'genderit_cache.json')
output_file = os.path.join(cache_dir, 'merged_gender_cache.json')

print("="*80)
print("MERGING GENDER CACHES")
print("="*80)

# Load both files
print("\nLoading genderize.io cache...")
with open(genderize_file, 'r', encoding='utf-8') as f:
    genderize_data = json.load(f)
print(f"Loaded {len(genderize_data):,} records from genderize.io")

print("\nLoading genderit cache...")
with open(genderit_file, 'r', encoding='utf-8') as f:
    genderit_data = json.load(f)
print(f"Loaded {len(genderit_data):,} records from genderit")

# Create lookup dictionaries
# Key: (name, country_code) for records with country
# Key: (name, None) for records without country

print("\n" + "="*80)
print("INDEXING RECORDS")
print("="*80)

# Index by name-country pairs
genderize_index = {}
genderit_index = {}

# Genderize records (no country codes)
for record in genderize_data:
    name = record['name'].lower()
    country = record.get('country_code')
    key = (name, country)
    genderize_index[key] = record

print(f"\nGenderize.io indexed: {len(genderize_index):,} unique name-country pairs")

# Genderit records (with country codes)
for record in genderit_data:
    name = record['name'].lower()
    country = record.get('country_code')
    key = (name, country)
    genderit_index[key] = record

print(f"Genderit indexed: {len(genderit_index):,} unique name-country pairs")

# Merge strategy
print("\n" + "="*80)
print("MERGING STRATEGY")
print("="*80)

merged = {}
stats = {
    'genderize_only': 0,
    'genderit_only': 0,
    'both_agree': 0,
    'both_disagree': 0,
    'genderize_preferred': 0,
    'genderit_preferred': 0,
}

# Get all unique keys
all_keys = set(genderize_index.keys()) | set(genderit_index.keys())
print(f"\nTotal unique name-country combinations: {len(all_keys):,}")

# Merge
for key in all_keys:
    name, country = key

    genderize_record = genderize_index.get(key)
    genderit_record = genderit_index.get(key)

    if genderize_record and not genderit_record:
        # Only in genderize
        merged[key] = genderize_record.copy()
        stats['genderize_only'] += 1

    elif genderit_record and not genderize_record:
        # Only in genderit
        merged[key] = genderit_record.copy()
        stats['genderit_only'] += 1

    else:
        # Both sources have this name-country pair
        gender_g = genderize_record['gender']
        gender_i = genderit_record['gender']
        prob_g = genderize_record.get('probability', 0)
        prob_i = genderit_record.get('probability', 0)

        if gender_g == gender_i:
            # Agree on gender - take higher probability
            stats['both_agree'] += 1

            if prob_g >= prob_i:
                merged[key] = genderize_record.copy()
                # Add genderit as secondary source
                merged[key]['sources'] = ['genderize.io', 'genderit']
                merged[key]['agreement'] = True
            else:
                merged[key] = genderit_record.copy()
                merged[key]['sources'] = ['genderit', 'genderize.io']
                merged[key]['agreement'] = True

        else:
            # Disagree on gender
            stats['both_disagree'] += 1

            # Prefer higher probability
            if prob_g > prob_i:
                merged[key] = genderize_record.copy()
                merged[key]['sources'] = ['genderize.io', 'genderit']
                merged[key]['agreement'] = False
                merged[key]['conflict'] = {
                    'genderize': gender_g,
                    'genderit': gender_i
                }
                stats['genderize_preferred'] += 1
            elif prob_i > prob_g:
                merged[key] = genderit_record.copy()
                merged[key]['sources'] = ['genderit', 'genderize.io']
                merged[key]['agreement'] = False
                merged[key]['conflict'] = {
                    'genderize': gender_g,
                    'genderit': gender_i
                }
                stats['genderit_preferred'] += 1
            else:
                # Same probability - prefer genderize.io (known to be more accurate)
                merged[key] = genderize_record.copy()
                merged[key]['sources'] = ['genderize.io', 'genderit']
                merged[key]['agreement'] = False
                merged[key]['conflict'] = {
                    'genderize': gender_g,
                    'genderit': gender_i
                }
                stats['genderize_preferred'] += 1

print("\nMerge statistics:")
print(f"  Only in genderize.io: {stats['genderize_only']:,}")
print(f"  Only in genderit: {stats['genderit_only']:,}")
print(f"  Both sources agree: {stats['both_agree']:,}")
print(f"  Both sources disagree: {stats['both_disagree']:,}")
print(f"    -> Genderize.io preferred: {stats['genderize_preferred']:,}")
print(f"    -> Genderit preferred: {stats['genderit_preferred']:,}")

# Also merge by name only (without country) to catch cross-source matches
print("\n" + "="*80)
print("CHECKING FOR NAME-ONLY DUPLICATES")
print("="*80)

# Group by name only
by_name = defaultdict(list)
for key, record in merged.items():
    name = key[0]
    by_name[name].append(record)

# Find names with multiple country entries
multi_country = {name: records for name, records in by_name.items() if len(records) > 1}
print(f"\nNames with multiple country entries: {len(multi_country):,}")

# Sample
if multi_country:
    print("\nSample names with multiple countries (first 10):")
    for i, (name, records) in enumerate(list(multi_country.items())[:10], 1):
        countries = [r.get('country_code', 'None') for r in records]
        genders = [r['gender'] for r in records]
        print(f"  {i}. {name}: {len(records)} entries - countries: {countries}, genders: {genders}")

# Convert to list for JSON output
merged_list = list(merged.values())

print("\n" + "="*80)
print("SAVING MERGED CACHE")
print("="*80)

with open(output_file, 'w', encoding='utf-8') as f:
    json.dump(merged_list, f, indent=2, ensure_ascii=False)

file_size = os.path.getsize(output_file)
print(f"\nSaved {len(merged_list):,} records to:")
print(f"  {output_file}")
print(f"  Size: {file_size / 1024 / 1024:.2f} MB")

# Final statistics
print("\n" + "="*80)
print("FINAL STATISTICS")
print("="*80)

from collections import Counter

# Gender distribution
gender_dist = Counter(r['gender'] for r in merged_list)
print("\nGender distribution:")
for gender, count in sorted(gender_dist.items()):
    pct = count / len(merged_list) * 100
    print(f"  {gender}: {count:,} ({pct:.2f}%)")

# Country coverage
with_country = sum(1 for r in merged_list if r.get('country_code'))
without_country = len(merged_list) - with_country
print(f"\nCountry coverage:")
print(f"  With country code: {with_country:,} ({with_country/len(merged_list)*100:.2f}%)")
print(f"  Without country code: {without_country:,} ({without_country/len(merged_list)*100:.2f}%)")

# Top countries
country_counts = Counter(r['country_code'] for r in merged_list if r.get('country_code'))
print("\nTop 20 countries:")
for country, count in country_counts.most_common(20):
    pct = count / len(merged_list) * 100
    print(f"  {country}: {count:,} ({pct:.2f}%)")

# Source distribution
source_dist = Counter()
for r in merged_list:
    if 'sources' in r:
        source_dist['multiple sources'] += 1
    else:
        source_dist[r['source']] += 1

print("\nSource distribution:")
for source, count in sorted(source_dist.items()):
    pct = count / len(merged_list) * 100
    print(f"  {source}: {count:,} ({pct:.2f}%)")

# Agreement rate
agreements = sum(1 for r in merged_list if r.get('agreement') == True)
conflicts = sum(1 for r in merged_list if r.get('agreement') == False)
if agreements + conflicts > 0:
    print(f"\nMulti-source predictions:")
    print(f"  Agreements: {agreements:,} ({agreements/(agreements+conflicts)*100:.2f}%)")
    print(f"  Conflicts: {conflicts:,} ({conflicts/(agreements+conflicts)*100:.2f}%)")

# Probability distribution
probs = [r['probability'] for r in merged_list if r.get('probability') is not None]
if probs:
    import statistics
    print("\nProbability statistics:")
    print(f"  Min: {min(probs):.2f}")
    print(f"  Mean: {statistics.mean(probs):.2f}")
    print(f"  Median: {statistics.median(probs):.2f}")
    print(f"  Max: {max(probs):.2f}")

# Show sample conflicts
conflicts_list = [r for r in merged_list if r.get('conflict')]
if conflicts_list:
    print(f"\nSample conflicts (first 10 of {len(conflicts_list):,}):")
    for i, r in enumerate(conflicts_list[:10], 1):
        conflict = r['conflict']
        print(f"  {i}. {r['name']} ({r.get('country_code', 'None')}): "
              f"genderize={conflict['genderize']}, genderit={conflict['genderit']} "
              f"-> chose {r['gender']} (prob: {r['probability']})")

print("\n" + "="*80)
print("✅ MERGE COMPLETE!")
print("="*80)
print(f"\nTotal unique predictions: {len(merged_list):,}")
print(f"Original genderize.io: {len(genderize_data):,}")
print(f"Original genderit: {len(genderit_data):,}")
print(f"Overlap: {len(genderize_data) + len(genderit_data) - len(merged_list):,}")
