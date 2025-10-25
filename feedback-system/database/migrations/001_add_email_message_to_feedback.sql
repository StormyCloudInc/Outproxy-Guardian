-- Migration: Add email and message columns to document_feedback table
-- Date: 2025-10-23

ALTER TABLE document_feedback ADD COLUMN email VARCHAR(255);
ALTER TABLE document_feedback ADD COLUMN message TEXT;
