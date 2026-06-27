-- Migration: Add refs_visuais to leads table
-- Run this in your PostgreSQL database

-- Add the column
ALTER TABLE leads ADD COLUMN IF NOT EXISTS refs_visuais TEXT;

-- Verify
SELECT id, nome, refs_visuais FROM leads WHERE refs_visuais IS NOT NULL LIMIT 10;
