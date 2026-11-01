-- Runs once when the Postgres container is first created.
-- Creates separate databases for Langfuse, Bifrost and ContextForge, which share this
-- Postgres server. The app database itself is created by POSTGRES_DB.
CREATE DATABASE langfuse;
CREATE DATABASE bifrost;
CREATE DATABASE mcpgw;

-- Keycloak stores its tables in a dedicated schema inside the app DB.
\connect returnguard
CREATE SCHEMA IF NOT EXISTS keycloak;

-- Extensions for the app database (pgvector is not used on purpose: Qdrant is the vector store).
\connect returnguard
CREATE EXTENSION IF NOT EXISTS "pgcrypto";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";
