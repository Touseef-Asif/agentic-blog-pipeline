#!/usr/bin/env bash
# =============================================================================
# init-db.sh - PostgreSQL initialization script
# Runs automatically when the Docker container is first created.
# =============================================================================
set -euo pipefail

echo "=== Blog Pipeline DB Init ==="

# Connect as superuser and set up extensions + schema
psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" <<-EOSQL

    -- ----------------------------------------------------------------
    -- Extensions
    -- ----------------------------------------------------------------
    CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
    CREATE EXTENSION IF NOT EXISTS "pgcrypto";
    CREATE EXTENSION IF NOT EXISTS "pg_trgm";

    -- ----------------------------------------------------------------
    -- Schema
    -- ----------------------------------------------------------------
    CREATE SCHEMA IF NOT EXISTS blog;

    -- Grant privileges to the default user
    GRANT ALL PRIVILEGES ON SCHEMA blog TO $POSTGRES_USER;
    GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA blog TO $POSTGRES_USER;
    ALTER DEFAULT PRIVILEGES IN SCHEMA blog
        GRANT ALL PRIVILEGES ON TABLES TO $POSTGRES_USER;
    ALTER DEFAULT PRIVILEGES IN SCHEMA blog
        GRANT ALL PRIVILEGES ON SEQUENCES TO $POSTGRES_USER;

    -- ----------------------------------------------------------------
    -- pipeline_runs table
    -- ----------------------------------------------------------------
    CREATE TABLE IF NOT EXISTS blog.pipeline_runs (
        id               UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
        run_id           VARCHAR(64) UNIQUE NOT NULL,
        status           VARCHAR(32) NOT NULL DEFAULT 'pending',
        start_time       TIMESTAMPTZ NOT NULL DEFAULT NOW(),
        end_time         TIMESTAMPTZ,
        config           JSONB       NOT NULL DEFAULT '{}',
        metrics          JSONB       NOT NULL DEFAULT '{}',
        error_message    TEXT,
        error_traceback  TEXT,
        created_at       TIMESTAMPTZ NOT NULL DEFAULT NOW(),
        updated_at       TIMESTAMPTZ NOT NULL DEFAULT NOW()
    );

    CREATE INDEX IF NOT EXISTS idx_pipeline_runs_run_id
        ON blog.pipeline_runs (run_id);
    CREATE INDEX IF NOT EXISTS idx_pipeline_runs_status
        ON blog.pipeline_runs (status);
    CREATE INDEX IF NOT EXISTS idx_pipeline_runs_start_time
        ON blog.pipeline_runs (start_time DESC);

    -- ----------------------------------------------------------------
    -- blog_posts table
    -- ----------------------------------------------------------------
    CREATE TABLE IF NOT EXISTS blog.blog_posts (
        id               UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
        run_id           VARCHAR(64) NOT NULL
                             REFERENCES blog.pipeline_runs(run_id)
                             ON DELETE CASCADE,
        title            TEXT        NOT NULL,
        subtitle         TEXT,
        content          TEXT        NOT NULL,
        introduction     TEXT,
        conclusion       TEXT,
        sections         JSONB       NOT NULL DEFAULT '[]',
        keywords         JSONB       NOT NULL DEFAULT '[]',
        meta_description TEXT,
        reading_time     INTEGER     DEFAULT 0,
        tone             VARCHAR(64) DEFAULT 'professional',
        sources          JSONB       NOT NULL DEFAULT '[]',
        status           VARCHAR(32) NOT NULL DEFAULT 'draft',
        score            NUMERIC(5,2) DEFAULT 0,
        created_at       TIMESTAMPTZ NOT NULL DEFAULT NOW(),
        updated_at       TIMESTAMPTZ NOT NULL DEFAULT NOW()
    );

    CREATE INDEX IF NOT EXISTS idx_blog_posts_run_id
        ON blog.blog_posts (run_id);
    CREATE INDEX IF NOT EXISTS idx_blog_posts_status
        ON blog.blog_posts (status);
    CREATE INDEX IF NOT EXISTS idx_blog_posts_score
        ON blog.blog_posts (score DESC);
    CREATE INDEX IF NOT EXISTS idx_blog_posts_created_at
        ON blog.blog_posts (created_at DESC);
    CREATE INDEX IF NOT EXISTS idx_blog_posts_title_trgm
        ON blog.blog_posts USING gin (title gin_trgm_ops);

    -- ----------------------------------------------------------------
    -- updated_at trigger function
    -- ----------------------------------------------------------------
    CREATE OR REPLACE FUNCTION blog.set_updated_at()
    RETURNS TRIGGER AS \$\$
    BEGIN
        NEW.updated_at = NOW();
        RETURN NEW;
    END;
    \$\$ LANGUAGE plpgsql;

    CREATE OR REPLACE TRIGGER trg_pipeline_runs_updated_at
        BEFORE UPDATE ON blog.pipeline_runs
        FOR EACH ROW EXECUTE FUNCTION blog.set_updated_at();

    CREATE OR REPLACE TRIGGER trg_blog_posts_updated_at
        BEFORE UPDATE ON blog.blog_posts
        FOR EACH ROW EXECUTE FUNCTION blog.set_updated_at();

EOSQL

echo "=== Blog Pipeline DB Init Complete ==="
