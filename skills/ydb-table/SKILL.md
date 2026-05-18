---
name: ydb-table
description: Writing and auditing code that runs YQL against YDB tables. Use when the user writes a query, designs a table or primary key, reads an `EXPLAIN`, or asks to review Java (ydb-java-sdk, ydb-jdbc-driver, Hibernate, Spring Data JPA) or Go (`ydb-go-sdk/v3`) application code that talks to YDB. Triggers on YQL keywords (`UPSERT`, `SELECT`, `DECLARE`, `AS_TABLE`, `VIEW <index>`, `CREATE TABLE`, `ALTER TABLE`, `EXPLAIN`), on the `BulkUpsert` SDK API, on JDBC / Hibernate / Spring symbols (`JpaRepository`, `findAllById`, `saveAll`, `deleteAllByIdInBatch`, `hibernate.jdbc.batch_size`, `@Version`, `@Retryable`, `SQLRecoverableException`, `SQLTransientException`), on `ydb-go-sdk/v3` symbols (`ydb.Open`, `db.Query().Do`, `db.Query().DoTx`, `db.Table().Do`, `query.WithIdempotent`, `query.WithCommit`, `ydb.WithLazyTx`, `ydb.ParamsBuilder`, `s.BeginTransaction`, `table.WithTxControl`, `BulkUpsertDataRows`, `balancers.PreferLocalDC`, `balancers.PreferNearestDC`), on YDB transaction-mode names (`SerializableRW`, `SnapshotRO`), and on PostgreSQL / MySQL → YDB conversion prompts. For other SDKs (Python, C++, C#) this skill covers only the YQL / schema / transaction-mode side; SDK-specific guidance for those languages is not in this skill yet — say so and point at upstream docs.
---

# YDB Table

Writing YQL against YDB tables, designing schemas to back those queries, and auditing application code that runs them.

## Workflow

1. **Classify the task.** Write a new query or schema, audit existing code, convert from another SQL dialect, or read an `EXPLAIN`.
2. **Load sources** per the table below.
3. **Do the work.** When auditing, cite the rule ID for any anti-pattern flagged — `RULE-JV-NN` for Java, `RULE-GO-NN` for Go. When the topic isn't covered by the loaded sources, say so and link to upstream YDB docs rather than guessing.

## Load sources

| Task                                                | Files to consult                                                                          |
| --------------------------------------------------- | ----------------------------------------------------------------------------------------- |
| Reads, writes, transaction modes, batch vs bulk     | `references/working-with-data.md`                                                         |
| Writing Java application code against YDB           | `references/embed/java.md`                                                                |
| Auditing Java application code against YDB          | `rules/embed/java.md`                                                                     |
| Writing Go application code against YDB             | `references/embed/go.md`                                                                  |
| Auditing Go application code against YDB            | `rules/embed/go.md`                                                                       |
| Schema design — primary key shape, partitioning     | `../ydb-core/SKILL.md#schema-basics`                                                      |
| YQL syntax, built-in functions, pragmas             | <https://ydb.tech/docs/en/yql/reference/> — do not reproduce the spec from memory         |

## Content rules

- Always parameterize: `DECLARE` the parameters and bind values. Plan-cache reuse depends on it; concatenated literals miss the cache.
- Prefer the Query Service over the deprecated Table Service for new code.
- When converting from another SQL dialect, surface where YDB diverges — primary keys are partition keys, no `SERIAL` / `AUTO_INCREMENT`, JOIN behavior and built-in function names differ — rather than producing code that happens to parse.
- Don't fabricate YQL syntax, built-in names, or SDK symbols. If the loaded sources don't cover the question, link the relevant page under <https://ydb.tech/docs/en/yql/reference/> and state the uncertainty.
