#!/bin/bash
set -e

# Create the prefect database if it doesn't exist
psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" <<-EOSQL
    SELECT 'CREATE DATABASE prefect'
    WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'prefect')\gexec
EOSQL
