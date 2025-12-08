#!/usr/bin/env python3
"""
Analyze publication_date and publication_year columns from works table
Extracts 20,000 rows and compares the two columns
"""

import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))

import psycopg2
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from datetime import datetime
import logging
from config import DB_CONFIG

# Setup logging
log_dir = Path(__file__).parent / 'logs'
log_dir.mkdir(exist_ok=True)

log_file = log_dir / f'{Path(__file__).stem}_{datetime.now():%Y%m%d_%H%M%S}.log'

logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] [%(levelname)s] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
    handlers=[
        logging.FileHandler(log_file),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)
logger.info(f"Starting {Path(__file__).name}")
logger.info(f"Log file: {log_file}")


def connect_db():
    """Connect to PostgreSQL database"""
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        logger.info("Successfully connected to database")
        return conn
    except Exception as e:
        logger.error(f"Failed to connect to database: {e}")
        raise


def analyze_date_formats(conn):
    """Analyze the format of publication_date column"""
    logger.info("Analyzing publication_date formats...")

    query = """
    SELECT
        publication_date,
        publication_year,
        COUNT(*) as count
    FROM works
    WHERE publication_date IS NOT NULL
    GROUP BY publication_date, publication_year
    LIMIT 100
    """

    df_sample = pd.read_sql(query, conn)
    logger.info(f"Sample of date formats (first 10):")
    for idx, row in df_sample.head(10).iterrows():
        logger.info(f"  Date: {row['publication_date']}, Year: {row['publication_year']}, Count: {row['count']}")

    return df_sample


def extract_data(conn, n_rows=20000):
    """Extract n_rows from works table with publication info"""
    logger.info(f"Extracting {n_rows:,} rows from works table...")

    # Use TABLESAMPLE for faster sampling on large tables
    # TABLESAMPLE SYSTEM samples random pages, much faster than ORDER BY RANDOM()
    query = f"""
    SELECT
        work_id,
        publication_date,
        publication_year
    FROM works TABLESAMPLE SYSTEM (1)
    WHERE publication_date IS NOT NULL
        AND publication_year IS NOT NULL
    LIMIT {n_rows}
    """

    df = pd.read_sql(query, conn)
    logger.info(f"Extracted {len(df):,} rows")
    logger.info(f"Columns: {df.columns.tolist()}")
    logger.info(f"\nFirst few rows:\n{df.head()}")

    return df


def parse_dates(df):
    """Parse publication_date and extract year from it"""
    logger.info("Parsing publication dates...")

    # Check the format of publication_date
    logger.info(f"Publication_date dtype: {df['publication_date'].dtype}")
    logger.info(f"Sample values:\n{df['publication_date'].head(20)}")

    # Count different date format patterns
    date_lengths = df['publication_date'].astype(str).str.len().value_counts()
    logger.info(f"\nDate string lengths distribution:\n{date_lengths}")

    # Try to identify the format
    sample_dates = df['publication_date'].head(100)
    logger.info(f"\nChecking date formats in first 100 rows:")

    format_counts = {}
    for date_val in sample_dates:
        date_str = str(date_val)
        format_key = f"length_{len(date_str)}"
        format_counts[format_key] = format_counts.get(format_key, 0) + 1

    logger.info(f"Format distribution: {format_counts}")

    # Parse the date and extract year
    df['date_str'] = df['publication_date'].astype(str)
    df['date_length'] = df['date_str'].str.len()

    # Try to extract year from the date string
    # Assuming format is YYYY-MM-DD or just YYYY
    def extract_year_from_date(date_str):
        try:
            # If it's already a date object
            if isinstance(date_str, (pd.Timestamp, datetime)):
                return date_str.year

            # Convert to string
            date_str = str(date_str)

            # Try to parse as date
            if len(date_str) == 10 and '-' in date_str:  # YYYY-MM-DD
                return int(date_str[:4])
            elif len(date_str) == 4:  # Just YYYY
                return int(date_str)
            elif len(date_str) > 4:  # Try to extract first 4 characters
                return int(date_str[:4])
            else:
                return None
        except:
            return None

    df['year_from_date'] = df['publication_date'].apply(extract_year_from_date)

    # Check for mismatches
    df['year_match'] = df['year_from_date'] == df['publication_year']

    logger.info(f"\nYear extraction results:")
    logger.info(f"  Successfully extracted: {df['year_from_date'].notna().sum():,} / {len(df):,}")
    logger.info(f"  Years match: {df['year_match'].sum():,} / {df['year_from_date'].notna().sum():,}")
    logger.info(f"  Years don't match: {(~df['year_match']).sum():,}")

    # Show some mismatches
    mismatches = df[~df['year_match']].head(20)
    if len(mismatches) > 0:
        logger.info(f"\nSample mismatches:")
        for idx, row in mismatches.iterrows():
            logger.info(f"  Date: {row['publication_date']}, Year from date: {row['year_from_date']}, Publication year: {row['publication_year']}")

    return df


def create_visualizations(df):
    """Create visualizations comparing date and year columns"""
    logger.info("Creating visualizations...")

    # Set up the plotting style
    sns.set_style("whitegrid")
    plt.rcParams['figure.figsize'] = (15, 10)

    # Create a figure with multiple subplots
    fig, axes = plt.subplots(2, 2, figsize=(15, 12))

    # 1. Scatter plot: year_from_date vs publication_year
    ax1 = axes[0, 0]
    valid_data = df[df['year_from_date'].notna()].copy()
    ax1.scatter(valid_data['publication_year'], valid_data['year_from_date'],
                alpha=0.3, s=10)
    ax1.plot([valid_data['publication_year'].min(), valid_data['publication_year'].max()],
             [valid_data['publication_year'].min(), valid_data['publication_year'].max()],
             'r--', label='Perfect match')
    ax1.set_xlabel('Publication Year (from column)')
    ax1.set_ylabel('Year (extracted from date)')
    ax1.set_title('Comparison: Publication Year vs Year from Date')
    ax1.legend()
    ax1.grid(True, alpha=0.3)

    # 2. Distribution of differences
    ax2 = axes[0, 1]
    df['year_difference'] = df['year_from_date'] - df['publication_year']
    df['year_difference'].dropna().hist(bins=50, ax=ax2, edgecolor='black')
    ax2.set_xlabel('Difference (Year from Date - Publication Year)')
    ax2.set_ylabel('Frequency')
    ax2.set_title('Distribution of Year Differences')
    ax2.axvline(x=0, color='r', linestyle='--', label='No difference')
    ax2.legend()

    # 3. Publication year distribution
    ax3 = axes[1, 0]
    df['publication_year'].hist(bins=50, ax=ax3, edgecolor='black', alpha=0.7, label='Publication Year')
    ax3.set_xlabel('Year')
    ax3.set_ylabel('Frequency')
    ax3.set_title('Distribution of Publication Years')
    ax3.legend()

    # 4. Date format length distribution
    ax4 = axes[1, 1]
    df['date_length'].value_counts().sort_index().plot(kind='bar', ax=ax4)
    ax4.set_xlabel('Date String Length')
    ax4.set_ylabel('Frequency')
    ax4.set_title('Distribution of Date Format Lengths')
    ax4.tick_params(axis='x', rotation=0)

    plt.tight_layout()

    # Save figure
    output_file = Path(__file__).parent / 'publication_date_analysis.png'
    plt.savefig(output_file, dpi=300, bbox_inches='tight')
    logger.info(f"Visualization saved to: {output_file}")

    # Show plot
    plt.show()

    return output_file


def main():
    """Main execution"""
    try:
        # Connect to database
        conn = connect_db()

        # First, analyze date formats
        analyze_date_formats(conn)

        # Extract data
        df = extract_data(conn, n_rows=20000)

        # Parse dates and compare
        df = parse_dates(df)

        # Create visualizations
        output_file = create_visualizations(df)

        # Summary statistics
        logger.info("\n" + "="*60)
        logger.info("SUMMARY STATISTICS")
        logger.info("="*60)
        logger.info(f"Total rows analyzed: {len(df):,}")
        logger.info(f"Rows with valid dates: {df['year_from_date'].notna().sum():,}")
        logger.info(f"Rows where years match: {df['year_match'].sum():,}")
        logger.info(f"Match rate: {df['year_match'].sum() / df['year_from_date'].notna().sum() * 100:.2f}%")
        logger.info(f"\nPublication year range: {df['publication_year'].min()} - {df['publication_year'].max()}")
        logger.info(f"Year from date range: {df['year_from_date'].min()} - {df['year_from_date'].max()}")

        # Close connection
        conn.close()
        logger.info("\nAnalysis complete!")

    except Exception as e:
        logger.error(f"Error in main execution: {e}", exc_info=True)
        raise


if __name__ == "__main__":
    main()
