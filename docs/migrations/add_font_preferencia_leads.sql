-- Migration: Add font_preferencia to leads table
-- Run this in your PostgreSQL database

-- Add the column
ALTER TABLE leads ADD COLUMN IF NOT EXISTS font_preferencia VARCHAR(50);

-- Verify
SELECT id, nome, font_preferencia FROM leads WHERE font_preferencia IS NOT NULL LIMIT 10;