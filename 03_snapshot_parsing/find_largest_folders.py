#!/usr/bin/env python3
"""Find the largest dated folder for each entity type"""
import os
import subprocess
from pathlib import Path

SNAPSHOT_DIR = Path('/Volumes/OA_snapshot/24OCT2025/data')

entities = ['topics', 'concepts', 'publishers', 'funders', 'sources', 'institutions', 'authors', 'works']

print("\n" + "="*80)
print("FINDING LARGEST FOLDERS FOR EACH ENTITY")
print("="*80 + "\n")

largest_folders = {}

for entity in entities:
    entity_dir = SNAPSHOT_DIR / entity
    if not entity_dir.exists():
        print(f"⚠️  {entity}: Directory not found")
        continue

    # Find all updated_date folders
    dated_folders = sorted(entity_dir.glob('updated_date=*'))

    if not dated_folders:
        print(f"⚠️  {entity}: No dated folders found")
        continue

    # Get size of each folder
    folder_sizes = []
    for folder in dated_folders:
        # Use du to get folder size
        result = subprocess.run(['du', '-sk', str(folder)], capture_output=True, text=True)
        if result.returncode == 0:
            size_kb = int(result.stdout.split()[0])
            folder_sizes.append((size_kb, folder))

    # Sort by size descending
    folder_sizes.sort(reverse=True)

    if folder_sizes:
        largest_size, largest_folder = folder_sizes[0]
        largest_folders[entity] = largest_folder

        # Convert size to readable format
        if largest_size > 1024*1024:
            size_str = f"{largest_size/(1024*1024):.2f} GB"
        elif largest_size > 1024:
            size_str = f"{largest_size/1024:.2f} MB"
        else:
            size_str = f"{largest_size} KB"

        print(f"✅ {entity:15s} {largest_folder.name:30s} {size_str:>12s}")

        # Show top 3
        if len(folder_sizes) > 1:
            for i, (size_kb, folder) in enumerate(folder_sizes[1:4], 2):
                if size_kb > 1024*1024:
                    size_str = f"{size_kb/(1024*1024):.2f} GB"
                elif size_kb > 1024:
                    size_str = f"{size_kb/1024:.2f} MB"
                else:
                    size_str = f"{size_kb} KB"
                print(f"   {i}. {folder.name:30s} {size_str:>12s}")
        print()

print("="*80)
print("\nConfig update needed:")
print("="*80)
print("\nGZ_DIRECTORIES = {")
for entity, folder in largest_folders.items():
    print(f"    '{entity}': '{folder}',")
print("}")
print()
