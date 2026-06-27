-- Migration: Add paleta_cores to leads table
-- Run this in your PostgreSQL database

-- Add the column
ALTER TABLE leads ADD COLUMN IF NOT EXISTS paleta_cores JSON;

-- Update existing leads with sites to have default palette
UPDATE leads
SET paleta_cores = '{"primary": "#374151", "secondary": "#f9fafb", "accent": "#6366f1"}'
WHERE site_url IS NOT NULL
  AND site_url != ''
  AND paleta_cores IS NULL;

-- Verify
SELECT id, nome, site_url, paleta_cores
FROM leads
WHERE site_url IS NOT NULL
LIMIT 10;
