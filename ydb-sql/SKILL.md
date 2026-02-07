---
name: ydb-sql
description: >
  Help write, optimize, and debug YQL/SQL queries for YDB.
  Use when the user asks to write a query, optimize a slow query, explain a query plan,
  design a table schema, or convert SQL from other databases to YQL.
  Triggers on: YQL help, write query, optimize query, query plan, EXPLAIN,
  slow query, convert to YQL, YDB schema design, table design.
---

# YDB Query Assistant

Help users write correct, efficient YQL queries and design optimal table schemas for YDB.

## Workflow

### 1. Understand the task

Determine what the user needs:
- **Write query**: translate natural language or pseudocode into YQL
- **Optimize query**: analyze a slow query, check its plan, suggest improvements
- **Schema design**: design tables, indexes, partitioning for a given workload
- **Convert**: translate SQL from PostgreSQL/MySQL/etc. to YQL syntax
- **Debug**: explain errors, fix broken queries

### 2. Load relevant references

- **YQL syntax and features**: [references/yql-syntax.md](references/yql-syntax.md)
- **Query optimization**: [references/optimization.md](references/optimization.md)
- **Schema design patterns**: [references/schema-design.md](references/schema-design.md)
- **SQL dialect differences**: [references/sql-to-yql.md](references/sql-to-yql.md)

### 3. Generate / optimize

When writing queries:
- Always use parametrized queries (`$paramName`)
- Prefer `UPSERT` over `INSERT` for tables without sync indexes
- Use `VIEW index_name` when querying by indexed columns
- Use `StartsWith()` instead of `LIKE 'prefix%'`
- Add `ORDER BY` when result order matters
- Use `AS_TABLE($list)` for batch operations
- Consider partition layout when designing queries

When optimizing:
- Ask user to run `EXPLAIN` or `EXPLAIN ANALYZE`
- Look for `TableFullScan` — suggest indexes
- Look for missing `VIEW` hints
- Check if parametrized queries are used (plan caching)
- Check transaction scope — minimize reads in RW transactions

### 4. Explain

Always explain WHY a query pattern is recommended, referencing YDB-specific behavior (partitioning, TLI, MVCC, query cache).
