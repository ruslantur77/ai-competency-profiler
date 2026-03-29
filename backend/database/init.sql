-- =============================================================================
-- Competency System Database Initialization
-- =============================================================================

-- Create application database and user
CREATE DATABASE app;
CREATE USER app WITH PASSWORD 'app';
GRANT ALL PRIVILEGES ON DATABASE app TO app;

-- Connect to app database for schema setup
\c app;

-- Grant privileges on future tables
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO app;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON SEQUENCES TO app;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON FUNCTIONS TO app;

-- Note: Airflow database is created automatically by docker-compose
-- with POSTGRES_DB: airflow
