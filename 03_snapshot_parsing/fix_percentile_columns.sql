-- Fix cited_by_percentile_year columns from INTEGER to DECIMAL
-- Run this script to fix the data type mismatch error

-- Change cited_by_percentile_year_min from INTEGER to DECIMAL
ALTER TABLE works
ALTER COLUMN cited_by_percentile_year_min TYPE DECIMAL(5,2);

-- Change cited_by_percentile_year_max from INTEGER to DECIMAL
ALTER TABLE works
ALTER COLUMN cited_by_percentile_year_max TYPE DECIMAL(5,2);

-- Verify the changes
SELECT
    column_name,
    data_type,
    numeric_precision,
    numeric_scale
FROM information_schema.columns
WHERE table_name = 'works'
    AND column_name IN ('cited_by_percentile_year_min', 'cited_by_percentile_year_max');
