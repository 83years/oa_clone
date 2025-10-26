#!/usr/bin/env python3
"""
Verify Entity Tables are Complete and Ready for Phase 2
Checks: authors, topics, concepts, sources, funders, institutions
"""
import psycopg2
from datetime import datetime
from config import DB_CONFIG
import json

# Expected approximate counts (from OpenAlex documentation)
EXPECTED_COUNTS = {
    'authors': 100_000_000,
    'topics': 4_500,
    'concepts': 65_000,
    'sources': 250_000,
    'funders': 30_000,
    'institutions': 110_000
}

def verify_entity_tables():
    """Verify all entity tables are complete"""
    print("=" * 80)
    print("ENTITY TABLES VERIFICATION - PRE-PHASE 2")
    print("=" * 80)
    print()

    conn = psycopg2.connect(**DB_CONFIG)
    cursor = conn.cursor()

    all_ready = True
    results = {
        'timestamp': datetime.now().isoformat(),
        'entities': {},
        'ready_for_phase_2': True
    }

    entities = ['authors', 'topics', 'concepts', 'sources', 'funders', 'institutions']

    for i, entity in enumerate(entities, 1):
        print(f"[{i}/{len(entities)}] Verifying {entity} table...")

        entity_results = {}

        try:
            # Check table exists
            cursor.execute("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables
                    WHERE table_name = %s
                );
            """, (entity,))

            if not cursor.fetchone()[0]:
                print(f"      ❌ FAIL: Table does not exist")
                entity_results['exists'] = False
                entity_results['ready'] = False
                all_ready = False
                results['entities'][entity] = entity_results
                continue

            entity_results['exists'] = True

            # Get row count
            cursor.execute(f"SELECT COUNT(*) FROM {entity};")
            count = cursor.fetchone()[0]
            entity_results['count'] = count

            expected = EXPECTED_COUNTS[entity]
            pct_of_expected = 100 * count / expected

            print(f"      Row count: {count:,}")
            print(f"      Expected: ~{expected:,} ({pct_of_expected:.1f}%)")

            # Validate count
            if count == 0:
                print(f"      ❌ FAIL: Table is empty")
                entity_results['ready'] = False
                all_ready = False
            elif pct_of_expected < 50:
                print(f"      ⚠️  WARNING: Count is much lower than expected")
                entity_results['ready'] = True  # Still proceed but warn
            else:
                print(f"      ✅ PASS")
                entity_results['ready'] = True

            # Check for NULL primary keys
            pk_field = f"{entity[:-1]}_id" if entity != 'authors' else 'author_id'
            cursor.execute(f"SELECT COUNT(*) FROM {entity} WHERE {pk_field} IS NULL;")
            null_count = cursor.fetchone()[0]

            if null_count > 0:
                print(f"      ❌ FAIL: Found {null_count:,} NULL {pk_field} values")
                entity_results['ready'] = False
                all_ready = False
            else:
                entity_results['null_pks'] = 0

            # Check for duplicates
            cursor.execute(f"""
                SELECT COUNT(*) FROM (
                    SELECT {pk_field} FROM {entity}
                    GROUP BY {pk_field}
                    HAVING COUNT(*) > 1
                ) duplicates;
            """)
            dup_count = cursor.fetchone()[0]

            if dup_count > 0:
                print(f"      ❌ FAIL: Found {dup_count:,} duplicate {pk_field} values")
                entity_results['ready'] = False
                all_ready = False
            else:
                entity_results['duplicates'] = 0

            # Sample data
            cursor.execute(f"SELECT * FROM {entity} LIMIT 3;")
            samples = cursor.fetchall()
            print(f"      Sample records: {len(samples)}")

        except Exception as e:
            print(f"      ❌ ERROR: {e}")
            entity_results['error'] = str(e)
            entity_results['ready'] = False
            all_ready = False

        results['entities'][entity] = entity_results
        print()

    # Summary
    print("=" * 80)
    print("SUMMARY")
    print("=" * 80)

    for entity in entities:
        status = results['entities'].get(entity, {})
        if status.get('ready', False):
            print(f"  ✅ {entity:15s}: {status.get('count', 0):,} records")
        else:
            print(f"  ❌ {entity:15s}: NOT READY")

    print("\n" + "=" * 80)
    results['ready_for_phase_2'] = all_ready

    if all_ready:
        print("✅ ALL ENTITY TABLES READY FOR PHASE 2")
    else:
        print("❌ SOME ENTITY TABLES NOT READY")
        print("\nPlease ensure all entity tables are populated before Phase 2.")
    print("=" * 80)

    # Save results
    with open('entity_verification_results.json', 'w') as f:
        json.dump(results, f, indent=2)
    print("\nDetailed results saved to: entity_verification_results.json")

    cursor.close()
    conn.close()

    return all_ready

if __name__ == '__main__':
    import sys
    ready = verify_entity_tables()
    sys.exit(0 if ready else 1)
