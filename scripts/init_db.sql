-- Initialize YouTube Intelligence & Automation OS database
-- Runs on first PostgreSQL startup

-- Enable pgvector extension
CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS pg_trgm;
CREATE EXTENSION IF NOT EXISTS unaccent;

-- Create langfuse database if using monitoring profile
CREATE DATABASE langfuse_db;

-- Grant permissions
GRANT ALL PRIVILEGES ON DATABASE ytautos_db TO ytautos;
GRANT ALL PRIVILEGES ON DATABASE langfuse_db TO ytautos;
