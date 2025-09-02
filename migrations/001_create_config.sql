-- Create configuration table
-- Revision ID: 001_create_config
-- Create Date: 2025-09-01

CREATE TABLE IF NOT EXISTS configuration (
    id SERIAL PRIMARY KEY,
    key VARCHAR(50) NOT NULL UNIQUE,
    value VARCHAR(500),
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
