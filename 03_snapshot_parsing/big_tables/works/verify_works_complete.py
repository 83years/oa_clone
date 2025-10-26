#!/usr/bin/env python3
"""
Verify Works Table is Complete and Ready for Phase 2
"""
import psycopg2
from datetime import datetime
from config import DB_CONFIG
import json
from pathlib import Path

def verify_works_table():
    """Comprehensive verification of works table"""
    print("=" * 80)
    print("WORKS TABLE VERIFICATION - PRE-PHASE 2")
    print("=" * 80)
    print()

    conn = psycopg2.connect(**DB_CONFIG)
    cursor = conn.cursor()

    verification_results = {
        'timestamp': datetime.now().isoformat(),
        'checks': {},
        'ready_for_phase_2': True
    }

    try:
        # Check 1: Total row count
        print("[1/8] Checking total row count...")
        cursor.execute("SELECT COUNT(*) FROM works;")
        total_works = cursor.fetchone()[0]
        print(f"      Total works: {total_works:,}")
        verification_results['checks']['total_works'] = total_works

        if total_works == 0:
            print("      ❌ FAIL: No works in table")
            verification_results['ready_for_phase_2'] = False
        elif total_works < 200000000:
            print(f"      ⚠️  WARNING: Expected ~250M works, found {total_works:,}")
        else:
            print("      ✅ PASS")

        # Check 2: Duplicate work_ids
        print("\n[2/8] Checking for duplicate work_ids...")
        cursor.execute("""
            SELECT COUNT(*) FROM (
                SELECT work_id FROM works
                GROUP BY work_id
                HAVING COUNT(*) > 1
            ) duplicates;
        """)
        duplicate_count = cursor.fetchone()[0]
        print(f"      Duplicate work_ids: {duplicate_count:,}")
        verification_results['checks']['duplicates'] = duplicate_count

        if duplicate_count > 0:
            print("      ❌ FAIL: Found duplicate work_ids")
            verification_results['ready_for_phase_2'] = False

            # Show examples
            cursor.execute("""
                SELECT work_id, COUNT(*) as count
                FROM works
                GROUP BY work_id
                HAVING COUNT(*) > 1
                LIMIT 5;
            """)
            print("      Examples:")
            for row in cursor.fetchall():
                print(f"        - {row[0]}: {row[1]} occurrences")
        else:
            print("      ✅ PASS")

        # Check 3: NULL work_ids
        print("\n[3/8] Checking for NULL work_ids...")
        cursor.execute("SELECT COUNT(*) FROM works WHERE work_id IS NULL;")
        null_count = cursor.fetchone()[0]
        print(f"      NULL work_ids: {null_count:,}")
        verification_results['checks']['null_work_ids'] = null_count

        if null_count > 0:
            print("      ❌ FAIL: Found NULL work_ids")
            verification_results['ready_for_phase_2'] = False
        else:
            print("      ✅ PASS")

        # Check 4: Date ranges
        print("\n[4/8] Checking date ranges...")
        cursor.execute("""
            SELECT
                MIN(publication_year) as min_year,
                MAX(publication_year) as max_year,
                MIN(created_date) as min_created,
                MAX(created_date) as max_created,
                MIN(updated_date) as min_updated,
                MAX(updated_date) as max_updated
            FROM works;
        """)
        dates = cursor.fetchone()
        print(f"      Publication years: {dates[0]} to {dates[1]}")
        print(f"      Created dates: {dates[2]} to {dates[3]}")
        print(f"      Updated dates: {dates[4]} to {dates[5]}")

        verification_results['checks']['date_ranges'] = {
            'publication_year': {'min': dates[0], 'max': dates[1]},
            'created_date': {'min': str(dates[2]), 'max': str(dates[3])},
            'updated_date': {'min': str(dates[4]), 'max': str(dates[5])}
        }

        if dates[0] and (dates[0] < 1000 or dates[1] > 2030):
            print("      ⚠️  WARNING: Unusual publication year range")
        else:
            print("      ✅ PASS")

        # Check 5: Field completeness
        print("\n[5/8] Checking field completeness...")
        cursor.execute("""
            SELECT
                COUNT(*) as total,
                COUNT(display_name) as has_display_name,
                COUNT(doi) as has_doi,
                COUNT(publication_year) as has_pub_year,
                COUNT(cited_by_count) as has_citations,
                COUNT(type) as has_type,
                COUNT(is_paratext) as has_is_paratext,
                COUNT(fwci) as has_fwci
            FROM works;
        """)
        completeness = cursor.fetchone()
        total = completeness[0]

        print(f"      display_name: {completeness[1]:,} / {total:,} ({100*completeness[1]/total:.1f}%)")
        print(f"      doi: {completeness[2]:,} / {total:,} ({100*completeness[2]/total:.1f}%)")
        print(f"      publication_year: {completeness[3]:,} / {total:,} ({100*completeness[3]/total:.1f}%)")
        print(f"      cited_by_count: {completeness[4]:,} / {total:,} ({100*completeness[4]/total:.1f}%)")
        print(f"      type: {completeness[5]:,} / {total:,} ({100*completeness[5]/total:.1f}%)")
        print(f"      is_paratext: {completeness[6]:,} / {total:,} ({100*completeness[6]/total:.1f}%)")
        print(f"      fwci: {completeness[7]:,} / {total:,} ({100*completeness[7]/total:.1f}%)")

        verification_results['checks']['field_completeness'] = {
            'display_name_pct': 100*completeness[1]/total,
            'doi_pct': 100*completeness[2]/total,
            'publication_year_pct': 100*completeness[3]/total,
            'fwci_pct': 100*completeness[7]/total
        }

        print("      ✅ PASS")

        # Check 6: Type distribution
        print("\n[6/8] Checking work type distribution...")
        cursor.execute("""
            SELECT type, COUNT(*) as count
            FROM works
            WHERE type IS NOT NULL
            GROUP BY type
            ORDER BY count DESC
            LIMIT 10;
        """)

        print("      Top 10 work types:")
        for row in cursor.fetchall():
            print(f"        - {row[0]:30s}: {row[1]:,}")

        print("      ✅ PASS")

        # Check 7: Sample data quality
        print("\n[7/8] Sampling random works for quality check...")
        cursor.execute("""
            SELECT work_id, display_name, publication_year, cited_by_count, type
            FROM works
            ORDER BY RANDOM()
            LIMIT 5;
        """)

        print("      Sample works:")
        for row in cursor.fetchall():
            print(f"        - {row[0]}: {row[1][:50]}... ({row[2]}, {row[3]} citations, {row[4]})")

        print("      ✅ PASS")

        # Check 8: Check orchestrator state
        print("\n[8/8] Checking orchestrator state...")
        state_file = Path('orchestrator_state.json')

        if state_file.exists():
            with open(state_file, 'r') as f:
                state = json.load(f)
                completed = len(state.get('completed_files', []))
                print(f"      Completed files: {completed:,}")
                verification_results['checks']['orchestrator_completed_files'] = completed

                # Try to estimate total files
                from config import DATA_ROOT
                works_path = Path(DATA_ROOT) / 'works'
                total_files = 0
                if works_path.exists():
                    for date_dir in works_path.glob('updated_date=*'):
                        total_files += len(list(date_dir.glob('*.gz')))

                    print(f"      Total files found: {total_files:,}")
                    print(f"      Progress: {100*completed/total_files:.1f}%")
                    verification_results['checks']['orchestrator_progress_pct'] = 100*completed/total_files

                    if completed < total_files:
                        print(f"      ⚠️  WARNING: Not all files processed ({total_files - completed:,} remaining)")
                        verification_results['ready_for_phase_2'] = False
                    else:
                        print("      ✅ PASS")
                else:
                    print("      ⚠️  WARNING: Cannot verify file count (works directory not found)")
        else:
            print("      ⚠️  WARNING: Orchestrator state file not found")

        # Final verdict
        print("\n" + "=" * 80)
        if verification_results['ready_for_phase_2']:
            print("✅ VERIFICATION PASSED - READY FOR PHASE 2")
        else:
            print("❌ VERIFICATION FAILED - NOT READY FOR PHASE 2")
            print("\nPlease address the issues above before proceeding to Phase 2.")
        print("=" * 80)

        # Save verification results
        results_file = Path('verification_results.json')
        with open(results_file, 'w') as f:
            json.dump(verification_results, f, indent=2)
        print(f"\nDetailed results saved to: {results_file}")

    except Exception as e:
        print(f"\n❌ ERROR during verification: {e}")
        import traceback
        traceback.print_exc()
        verification_results['ready_for_phase_2'] = False

    finally:
        cursor.close()
        conn.close()

    return verification_results['ready_for_phase_2']

if __name__ == '__main__':
    import sys
    ready = verify_works_table()
    sys.exit(0 if ready else 1)
