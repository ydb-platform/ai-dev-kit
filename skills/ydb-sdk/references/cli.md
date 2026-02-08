# YDB CLI Anti-Patterns

## Detection
Look for `ydb` commands in shell scripts (`.sh`, `.bash`, `Makefile`, `Dockerfile`, CI configs).

---

## RULE-CLI01: Repeating connection params in every command

**Severity**: Low

**What to look for**: `-e grpcs://...` and `-d /ru/...` repeated in multiple `ydb` commands.

**Problem**: Verbose, error-prone, credentials may leak into shell history.

**Fix**: Create and use CLI profiles.

```bash
# BAD
ydb -e grpcs://ydb.example.com:2135 -d /ru-central1/b1g8sk/etn02q scheme ls
ydb -e grpcs://ydb.example.com:2135 -d /ru-central1/b1g8sk/etn02q sql -s "SELECT 1"
ydb -e grpcs://ydb.example.com:2135 -d /ru-central1/b1g8sk/etn02q discovery list

# GOOD: create profile once
ydb config profile create mydb
# or
ydb init

# then use it
ydb -p mydb scheme ls
ydb -p mydb sql -s "SELECT 1"

# or activate as default
ydb config profile activate mydb
ydb scheme ls
ydb sql -s "SELECT 1"
```

---

## RULE-CLI02: Using deprecated `ydb yql` command

**Severity**: Low

**What to look for**: `ydb yql` or `ydb scripting yql` in scripts.

**Problem**: `ydb yql` uses deprecated Scripting Service. `ydb sql` uses modern Query Service with streaming, no row limit, and better DDL semantics.

**Fix**: Replace with `ydb sql`.

```bash
# BAD
ydb yql -s "SELECT * FROM large_table"
ydb scripting yql -s "SELECT * FROM large_table"

# GOOD
ydb sql -s "SELECT * FROM large_table"
```
