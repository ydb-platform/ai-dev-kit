# YDB skills: finalize `ydb-core` and seed first Java SDK rules

Status: draft for review.

## Goal

Two parallel deliverables in one iteration:

1. **Prune `skills/ydb-core/SKILL.md`** so it carries zero `TODO(author)` markers and no unverified content. Less is fine; placeholders are not.
2. **Seed first Java content** under `skills/ydb-table/` — six anti-patterns and a positive-pattern reference — using the existing draft rule set as starting material. Add the two cross-cutting YDB-level references those Java rules need (`bulk-write.md`, `transactions.md`).

Both pieces respect the project rule: no claim ships without a grounded source. Items flagged below as "verify" must be confirmed against upstream SDK / docs / driver source before the corresponding file lands in `main`.

## Non-goals

- No content for Go / Python / .NET / C++. The Java seed is the first SDK pass; others follow on later iterations.
- No `ydb-ops` skill changes. Tracked separately in `TODO.md`.
- No rewrite of `ydb-table/SKILL.md` Gotchas section. Out of scope here.

## Deliverables

### 1. `skills/ydb-core/SKILL.md` — pruning

Concrete edits:

| Line(s) (pre-edit) | Action |
|---|---|
| 33 | Remove `TODO(author): LTS / cadence policy.`; keep `Server: CalVer. Current stable at https://github.com/ydb-platform/ydb/releases.` |
| 57 | Delete C++ row from the packages table entirely. |
| 58 | Delete .NET row from the packages table entirely. |
| 91 | Delete the full CLI-profile line (`CLI profile = endpoint + database + auth bundle saved under ~/.ydb/. Precedence …`). |
| 115 | Remove ` Alembic / Django backend — TODO(author).` from the Python integrations bullet; the rest of the bullet stays. |
| 117 | Remove `— TODO(author): per-module coordinates` from the JVM bullet; the rest of the bullet stays. |

Acceptance: `grep -c 'TODO(author)' skills/ydb-core/SKILL.md` returns `0`.

### 2. `docs/authoring.md` — register first prefix

Replace the placeholder row in the prefix registry with:

```
| JV | Java SDK / JDBC / Hibernate / Spring Data anti-patterns | skills/ydb-table/rules/embed/java.md |
```

### 3. `skills/ydb-table/rules/embed/java.md` — first six rules

Format per `docs/templates/rule.md.tmpl`. Six rules, prefix `JV`. Each rule self-contained (no cross-references to other skills).

#### RULE-JV-01: `findById` in a loop instead of `findAllById`

- **Severity**: Medium
- **What to look for**: `findById(` inside `for` / `forEach` / stream loops; sequential `findById` calls over a collection of ids.
- **Problem**: each `findById` is a separate `SELECT` round trip; reading N keys ⇒ N statements.
- **Fix**: `repository.findAllById(ids)` — one statement.
- **Source**: Spring Data JPA, `CrudRepository#findAllById`.
- **Verify before write**: standard Spring Data. Low effort — link to current Spring Data JPA docs.

#### RULE-JV-02: JDBC batching not configured

- **Severity**: High
- **What to look for**: `application.properties` / `application.yml` without `spring.jpa.properties.hibernate.jdbc.batch_size`; or Hibernate config without `hibernate.jdbc.batch_size`.
- **Problem**: Hibernate default is no batching ⇒ each `INSERT`/`UPDATE`/`DELETE` is a separate statement.
- **Fix**: set `spring.jpa.properties.hibernate.jdbc.batch_size` to ≥1000; enable `spring.jpa.properties.hibernate.order_inserts=true` and `…order_updates=true` so batches actually form.
- **Source**: Hibernate user guide (link to current major version); `ydb-jdbc-driver` examples README (link).
- **Verify before write**: confirm the "≥1000" floor recommendation against `ydb-jdbc-driver` documentation or `ydb-java-dialects` README; if not present there, drop the specific number and say "set explicitly to a value > 1; refer to driver examples for tuning."

#### RULE-JV-03: Spring Repository `save()` in a loop

- **Severity**: High
- **What to look for**: `repository.save(` inside a `for` / `forEach` / stream.
- **Problem**: cancels batching even when `hibernate.jdbc.batch_size` is set, and is a per-entity persist round trip when it isn't. Multiplicative cost with RULE-JV-02.
- **Fix**: collect to `List`, call `repository.saveAll(list)`.
- **Source**: Spring Data JPA, `CrudRepository#saveAll`.
- **Verify before write**: low effort.

#### RULE-JV-04: Spring Repository `delete()` / `deleteAllById()` for bulk paths

- **Severity**: High
- **What to look for**: `repository.delete(` or `repository.deleteAllById(` in bulk-delete paths (loops, batch services).
- **Problem**: Spring Data JPA's `deleteAllById` issues a `findById` per id before `DELETE` (to satisfy lifecycle callbacks) ⇒ N `SELECT` + N `DELETE`. Strictly worse than naive `delete()`-in-loop.
- **Fix**: `repository.deleteAllByIdInBatch(ids)` — single `DELETE … WHERE id IN (?, ?, …)`.
- **Source**: Spring Data JPA, `JpaRepository#deleteAllByIdInBatch`.
- **Verify before write**: confirm the SELECT-first behavior in the current Spring Data JPA `SimpleJpaRepository` implementation, and confirm `deleteAllByIdInBatch` is not overridden in the YDB Hibernate dialect to something different.

#### RULE-JV-05: JPA `@Version` (optimistic locking) over YDB

- **Severity**: High
- **What to look for**: `@Version` annotation on JPA entity fields.
- **Problem**: YDB Query Service runs SerializableRW by default — conflicting transactions are detected by the server and surface as a retryable `ABORTED`. `@Version` adds `WHERE … AND version = ?` to every `UPDATE`; with non-PK `version`, this can force a full-table scan on each update, and the optimistic-locking semantics it provides are redundant under server-side serializability.
- **Fix**: remove `@Version`. Let conflicts surface from the server and handle them via the retry classification described in RULE-JV-06.
- **Source**: link to YDB transactions doc; concrete `EXPLAIN` of an `UPDATE` with `@Version`-style predicate on a real table.
- **Verify before write**: critical. The "full-table scan" claim is plan-dependent. Confirm via `EXPLAIN` on a real schema, or with a concrete reference in `ydb-java-dialects` issues/docs. If not confirmable as "FullScan", reword to "non-index-friendly predicate that adds work to every UPDATE" and keep severity at High based on the redundancy + extra-work argument; if even that can't be grounded, drop the rule and revisit later.

#### RULE-JV-06: Ignoring retryable JDBC exceptions

- **Severity**: Critical
- **What to look for**: bare `catch (SQLException …)` that logs and continues, or that retries unconditionally without inspecting the subtype; absence of `@YdbRetryable` (or an equivalent manual classifying retry loop) around transactional methods.
- **Problem**: the JDBC exception hierarchy classifies failures. `SQLRecoverableException` (e.g. `ABORTED` from TLI) is fully retryable for any operation. `SQLTransientConnectionException` (connection drop) is retryable only for idempotent operations — the server may have committed before the connection died, and re-issuing a non-idempotent statement risks double effect. Not retrying loses work; over-retrying corrupts data.
- **Fix**: classify the exception. In Spring code, annotate transactional methods with `@YdbRetryable` (from the ydb-java-dialects Spring module). In plain JDBC, catch and switch on the subtype:
    - `SQLRecoverableException` ⇒ retry.
    - `SQLTransientConnectionException` ⇒ retry only when the caller has marked the operation idempotent (UPSERT, idempotency key, read-only).
- **Source**: `java.sql.SQLRecoverableException` / `SQLTransientConnectionException` JavaDoc; `ydb-jdbc-driver` source for which exception subtype is thrown per YDB status; `ydb-java-dialects` Spring module source for `@YdbRetryable`.
- **Verify before write**: critical. Need:
    1. The exact module path / package / annotation FQN for `@YdbRetryable` in `ydb-java-dialects`.
    2. The mapping in `ydb-jdbc-driver` from YDB status codes to JDBC exception subtypes — specifically, that `ABORTED` surfaces as `SQLRecoverableException` and connection drops as `SQLTransientConnectionException`. If the mapping differs, restate the rule using the actual subtypes thrown.

### 4. `skills/ydb-table/references/embed/java.md` — positive patterns

Five sections, each scaled to its content (template: `docs/templates/reference.md.tmpl`).

1. **Stack** — 3–5 lines. SDK → JDBC → Hibernate → Spring (JPA). Pointer to `ydb-jdbc-driver` examples for connection / configuration. No reproduction of connection-string format (that's `ydb-core`).
2. **Bulk operations** — canonical Spring/Hibernate snippet combining `findAllById` + `saveAll` + `deleteAllByIdInBatch` with `hibernate.jdbc.batch_size` and `order_inserts/order_updates` configured. 2–3 lines under it on why (one statement, one round trip; batching forms only when statements are ordered). Pointer line: "for the YDB-level mechanisms (`AS_TABLE`, `BulkUpsert`), see `../bulk-write.md`." No reproduction of YDB mechanisms here.
3. **Retries** — canonical pattern for the JDBC-exception-classifying retry. Two minimal snippets:
    - Spring: a method using `@YdbRetryable` + `@Transactional` doing the `saveAll` path.
    - Plain JDBC: try/catch over `SQLRecoverableException` (retry) vs `SQLTransientConnectionException` (retry iff idempotent).
4. **Transactions** — 3–4 lines. State that YDB Query Service defaults to SerializableRW and conflicts surface as retryable exceptions. Pointer line: "for YDB isolation levels and the consequence for application-level optimistic locking, see `../transactions.md`." No reproduction of isolation table here.
5. **Connection** — one line: `see ../ydb-core/SKILL.md#connecting`. No connection-string reproduction.

### 5. `skills/ydb-table/references/bulk-write.md` — YDB-level bulk write

Strictly YDB-level. No Java / JDBC / Hibernate / Spring references — those live in `embed/java.md`.

1. **What this is** — 2–3 lines. Two mechanisms:
    - `UPSERT INTO t SELECT … FROM AS_TABLE($list)` — YQL, through Query Service, transactional. For batches inside business operations.
    - `BulkUpsert` API — separate SDK method (not YQL). Non-transactional. Fastest path for ingest / migrations; parallelizes writes across partitions server-side.
   
   Source links: `https://ydb.tech/docs/en/yql/reference/syntax/upsert_into`, `https://ydb.tech/docs/en/dev/batch-upload`.
2. **Canonical pattern: `AS_TABLE`** — YQL snippet with `DECLARE $items AS List<Struct<…>>`. 2–3 lines on why: one plan, one transaction, one round trip, parameterized ⇒ plan cache hits.
3. **When to use which** — one prose sentence: `AS_TABLE` for transactional batches inside business operations; `BulkUpsert` for ingest / migrations where transactionality isn't needed and throughput is.
4. **Related** — `../ydb-core/SKILL.md#schema-basics` (partitioning shape affects batch ingest efficiency).

**Verify before write**:
- That `BulkUpsert` is the official name of the SDK method across SDKs. If naming diverges per language, state "the SDK exposes a bulk-upsert method (exact name varies by SDK; see SDK docs)" and link the language-agnostic concept page only.
- That `AS_TABLE` upserts route through Query Service and are transactional in current YDB.
- Batch-size limits: only mention if found in upstream docs. No invented numbers.

### 6. `skills/ydb-table/references/transactions.md` — YDB-level isolation

Strictly YDB-level. No JPA / `@Version` / Hibernate references.

1. **What this is** — 3–4 lines. Isolation levels in YDB Query Service: `SerializableRW` (default, RW), `SnapshotRO`, `StaleRO`, `OnlineRO`. SerializableRW: server-side serializability; conflicting transactions surface as a retryable `ABORTED` (TLI). Source: `https://ydb.tech/docs/en/concepts/transactions`.
2. **Implication: application-level optimistic locking is redundant** — 2–3 lines. The Postgres / Read-Committed pattern of carrying a `version` column and `WHERE … AND version = ?` on UPDATE is unnecessary under SerializableRW; the server already detects the conflict. The extra predicate adds work to each UPDATE.
3. **Read-only loads** — one sentence. `SnapshotRO` reduces coordination cost with writers for read-only workloads.
4. **Related** — `../ydb-core/SKILL.md#schema-basics`.

**Verify before write**:
- Exact set of isolation levels and their canonical names in current YDB Query Service. If `OnlineRO` / `StaleRO` are deprecated or renamed, list only what's current.
- That SerializableRW is the Query Service default (it is for Query Service; Table Service had different defaults).

## File layout, post-change

```
skills/ydb-core/SKILL.md                              (pruned, 0 TODOs)
skills/ydb-table/
  rules/embed/java.md                                 (new — 6 rules, prefix JV)
  references/embed/java.md                            (new — positive patterns)
  references/bulk-write.md                            (new — YDB-level)
  references/transactions.md                          (new — YDB-level)
docs/authoring.md                                     (prefix registry: JV row)
```

`rules/embed/` and `references/embed/` directories will be created as part of writing the Java files.

## Verification protocol (before any file lands on `main`)

For each item tagged "verify before write":

1. Fetch the canonical upstream source named in the rule's `Source` field — SDK source on GitHub, current YDB docs page, JDK JavaDoc, Spring Data JPA reference.
2. Confirm the specific claim (symbol exists, annotation exists with that name, exception subtype matches, default behavior matches). If the claim does not survive verification, either rephrase the rule using verified material or drop the rule for now. Do not ship a softened rule that pretends to be grounded but isn't.
3. Cite the verified source in the `Source:` field with a direct link.

The high-risk items, ranked:

1. **`@YdbRetryable` FQN and module** (RULE-JV-06). Hard prerequisite — the rule's Fix calls it by name.
2. **JDBC exception subtype mapping in `ydb-jdbc-driver`** (RULE-JV-06). The whole rule pivots on which exceptions the driver actually throws.
3. **`@Version` plan claim** (RULE-JV-05). The "FullScan" formulation is the most likely to need softening.
4. **`deleteAllByIdInBatch` semantics in YDB Hibernate dialect** (RULE-JV-04). Spring's behavior is standard; the YDB dialect might override.
5. **`AS_TABLE` transactionality + `BulkUpsert` naming** (`bulk-write.md`).
6. **Current set of isolation levels** (`transactions.md`).

## Out-of-spec but flagged

- `ydb-table/SKILL.md` Gotchas section still has `TODO(author)` placeholders. Not addressed here. Worth pulling in once we have ≥3 real audit cases.
- Reference files for Go / Python / .NET / C++ are not created at the same time — the templates exist (`embed/<lang>.md` suggested in `references/README.md`), but content for those languages is deferred until they have the same kind of seed material as Java does now.

## Acceptance

- `grep -rn 'TODO(author)' skills/ydb-core` ⇒ no matches.
- `docs/authoring.md` prefix registry has the `JV` row.
- Six `RULE-JV-NN` entries exist under `skills/ydb-table/rules/embed/java.md`, every one with a non-placeholder `Source:` link.
- Four reference files (`embed/java.md`, `bulk-write.md`, `transactions.md`, plus the registry entry) — no `TODO(author)`, no `<>` placeholders, every linked URL resolves.
- `skills/ydb-table/references/bulk-write.md` and `transactions.md` contain no Java / JDBC / Hibernate / Spring tokens (verified by grep).
- `skills/ydb-table/references/embed/java.md` does not duplicate the YDB-level material in `bulk-write.md` or `transactions.md` — it links to them.
