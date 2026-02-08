---
name: ydb-sql
description: >
  This skill should be used when the user asks to "write a YQL query", "optimize YDB query",
  "debug slow query", "explain query plan", "design YDB table schema", "convert SQL to YQL",
  "YDB EXPLAIN", "YDB SELECT", "YDB UPSERT", "YDB CREATE TABLE", or mentions YQL syntax,
  YDB query performance, or YDB schema design. Provides YQL/SQL query writing, optimization,
  debugging, and schema design guidance specific to YDB.
version: 0.2.0
---

# YDB SQL/YQL Assistant

Help write correct, efficient YQL/SQL queries and design optimal schemas for YDB.

## Workflow

### 1. Identify the task

Determine the type of query assistance needed:

| Task | What to do |
|------|-----------|
| **Write query** | Compose correct YQL for the described requirement |
| **Optimize** | Analyze query plan, suggest index/schema/query improvements |
| **Schema design** | Design tables with correct primary keys, partitioning, column families |
| **Convert SQL** | Translate PostgreSQL/MySQL/other SQL to valid YQL |
| **Debug** | Diagnose slow or failing queries using EXPLAIN ANALYZE |

### 2. Load references

Load reference files from `references/` based on the task:

| Task | References to load |
|------|-----------|
| Write query | `yql-syntax.md` |
| Optimize | `optimization.md`, `yql-syntax.md` |
| Schema design | `schema-design.md` |
| Convert SQL | `sql-to-yql.md`, `yql-syntax.md` |
| Debug | `yql-syntax.md`, `optimization.md` |

Also load shared schema and YQL rules from the SDK skill:
`${CLAUDE_PLUGIN_ROOT}/skills/ydb-sdk/references/common-rules.md`

### 3. Assist the user

When writing queries:
- Use parameterized queries (`DECLARE` + parameter binding) to prevent SQL injection and enable query cache
- Prefer Query Service over deprecated Table Service for new code
- Explain WHY each pattern is recommended (partitioning, TLI, MVCC, query cache implications)
- Show EXPLAIN output interpretation when optimizing

When designing schemas:
- Choose primary keys that distribute load evenly across partitions
- Avoid monotonically increasing keys (auto-increment, timestamps) as first PK column
- Consider read/write patterns when choosing column families
- Design for partition-local operations where possible

When converting SQL:
- Highlight YDB-specific differences (no JOINs across tables by default, UPSERT vs INSERT, etc.)
- Warn about features not available in YQL
- Provide equivalent YQL patterns for common SQL constructs

### 4. Format response

Present query results with:
- The query itself in a code block
- Explanation of key design decisions
- Performance considerations
- Alternative approaches when relevant

## Rules

- NEVER invent YQL syntax or features — only use patterns from reference files actually read
- Always explain WHY a pattern is recommended (partitioning, TLI, MVCC, query cache)
- When unsure about a YQL feature, state that explicitly rather than guessing
- Prefer idiomatic YQL over generic SQL that happens to work
