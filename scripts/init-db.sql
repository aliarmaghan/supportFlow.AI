-- Create schema for support system
CREATE SCHEMA IF NOT EXISTS support;

-- Grant permissions
GRANT ALL ON SCHEMA support TO support_user;

-- Set search path so tables are created in support schema by default
ALTER DATABASE support_db SET search_path TO support, public;