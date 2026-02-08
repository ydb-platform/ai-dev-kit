#!/bin/bash
set -e

ENDPOINT="grpcs://ydb.production.example.com:2135"
DATABASE="/ru-central1/b1g8skpblkos03m2lu8m/etn02q4l3bov9v7k5g4k"
TOKEN_FILE="~/.ydb/token"

echo "Running database migrations..."

ydb -e $ENDPOINT -d $DATABASE --yc-token-file $TOKEN_FILE yql -s "
    CREATE TABLE IF NOT EXISTS migrations (
        id Uint64,
        name Utf8,
        applied_at Timestamp,
        PRIMARY KEY (id)
    );
"

echo "Checking current schema..."
ydb -e $ENDPOINT -d $DATABASE --yc-token-file $TOKEN_FILE scheme ls

echo "Running data migration..."
ydb -e $ENDPOINT -d $DATABASE --yc-token-file $TOKEN_FILE yql -s "
    UPSERT INTO migrations (id, name, applied_at)
    VALUES (1, 'initial_schema', CurrentUtcTimestamp());
"

echo "Verifying migration..."
ydb -e $ENDPOINT -d $DATABASE --yc-token-file $TOKEN_FILE yql -s "
    SELECT * FROM migrations ORDER BY id;
"

echo "Exporting user stats..."
ydb -e $ENDPOINT -d $DATABASE --yc-token-file $TOKEN_FILE yql -s "
    SELECT status, COUNT(*) as cnt
    FROM users
    GROUP BY status;
"

echo "Done!"
