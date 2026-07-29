#!/bin/bash
# Runs once on first initialization (empty data directory).
# Creates the IAM database and user alongside the default filenest database.
set -e

psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" <<-EOSQL
    CREATE USER iam_user WITH PASSWORD '${IAM_POSTGRES_PASSWORD:-iam_password}';
    CREATE DATABASE iam_db OWNER iam_user;
EOSQL

psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "iam_db" <<-EOSQL
    GRANT ALL ON SCHEMA public TO iam_user;
EOSQL
