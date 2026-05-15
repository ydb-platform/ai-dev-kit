# YDB skills: `ydb-core` pruning + first Java SDK rules — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Strip remaining `TODO(author)` markers from `skills/ydb-core/SKILL.md` (no replacement content for unverified items) and seed six anti-pattern rules + a positive-pattern reference for the Java / JDBC / Hibernate / Spring stack under `skills/ydb-table/`, with two cross-cutting YDB-level references those Java rules link to.

**Architecture:** Markdown content delivery in this skill repo. Per-file responsibility is single-surface (`ydb-core` is router/orientation; `ydb-table/references/bulk-write.md` and `transactions.md` are YDB-level; `embed/java.md` files are language-specific). "Tests" here are static grep/link checks, not unit tests. Every claim about external APIs must be verified against upstream source (`ydb-jdbc-driver`, `ydb-java-dialects`, YDB docs) before the corresponding file lands.

**Tech Stack:** Markdown. Verification via `gh api`, WebFetch against github.com / ydb.tech, and Bash for repo-local grep/link checks.

**Spec:** `docs/superpowers/specs/2026-05-15-ydb-core-prune-and-java-rules-seed-design.md`.

---

## File map

| File | Action | Owner section |
|---|---|---|
| `skills/ydb-core/SKILL.md` | modify (delete-only) | Task 1 |
| `docs/authoring.md` | modify (registry row) | Task 2 |
| `skills/ydb-table/references/bulk-write.md` | create | Task 3 |
| `skills/ydb-table/references/transactions.md` | create | Task 4 |
| `skills/ydb-table/references/embed/java.md` | create | Task 5 |
| `skills/ydb-table/rules/embed/java.md` | create | Tasks 6 – 11 |

`rules/embed/` and `references/embed/` directories will be created as a side effect of writing the first file inside them.

## Verification protocol — when to use it

Some rules carry claims that must be confirmed against upstream before they ship. Each task that needs verification has an explicit **"Verify"** step with the exact command / URL / search pattern to run, and a **"Resolution"** step that says what to do depending on what the verification turns up. If verification can't ground a claim, the rule's wording is softened (or dropped) per the spec — never shipped on faith.

For verification fetches against GitHub, prefer `gh api repos/<org>/<repo>/contents/<path>` (returns content directly) or `gh search code` over WebFetch — they auth correctly and avoid HTML scraping. Examples:

```bash
gh api repos/ydb-platform/ydb-jdbc-driver/contents/README.md \
  --jq '.content' | base64 -d | grep -i 'batch'
gh search code --repo ydb-platform/ydb-java-dialects 'YdbRetryable'
```

For YDB docs, WebFetch against `https://ydb.tech/docs/...` is fine.

---

## Task 1: Prune `ydb-core/SKILL.md`

**Files:**
- Modify: `skills/ydb-core/SKILL.md`

- [ ] **Step 1: Confirm starting state**

```bash
grep -c 'TODO(author)' skills/ydb-core/SKILL.md
```
Expected: `6`.

- [ ] **Step 2: Remove server LTS TODO from line 33**

Edit the line that reads:

```
- Server: CalVer. Current stable at https://github.com/ydb-platform/ydb/releases. TODO(author): LTS / cadence policy.
```

to:

```
- Server: CalVer. Current stable at https://github.com/ydb-platform/ydb/releases.
```

- [ ] **Step 3: Delete C++ row (line 57) and .NET row (line 58) from the packages table**

Remove these two lines outright. Do not replace with em-dashes — the user wants the rows gone.

Old:
```
| C++ | ydb-cpp-sdk | build from source, CMake presets | ✅ | TODO(author) | TODO(author) |
| .NET | ydb-dotnet-sdk | NuGet `Ydb.Sdk` | ✅ | TODO(author) | TODO(author) |
```

After removal, the table goes Java → JS/TS without a gap row.

- [ ] **Step 4: Delete the CLI-profile line (line 91)**

Remove the entire line:

```
CLI profile = endpoint + database + auth bundle saved under `~/.ydb/`. Precedence when resolving connection settings: explicit CLI flags > `-p <profile>` > env vars > activated profile. (TODO(author): exact file path.)
```

The preceding blank line and the following section header remain.

- [ ] **Step 5: Remove Alembic/Django TODO from the Python integrations bullet (line 115)**

Old:
```
- **Python**: SQLAlchemy dialect `ydb-sqlalchemy` (PyPI). URL scheme: `yql+ydb://localhost:2136/local`. Alembic / Django backend — TODO(author).
```

New:
```
- **Python**: SQLAlchemy dialect `ydb-sqlalchemy` (PyPI). URL scheme: `yql+ydb://localhost:2136/local`.
```

- [ ] **Step 6: Remove the per-module-coordinates TODO from the JVM integrations bullet (line 117)**

Old:
```
- **JVM**: JDBC driver (see packages) is the gateway. `ydb-java-dialects` monorepo contains Hibernate 5/6, Spring Data JDBC, JOOQ, Liquibase, Flyway modules — TODO(author): per-module coordinates. Native ORM `yoj-project` for immutable entities.
```

New:
```
- **JVM**: JDBC driver (see packages) is the gateway. `ydb-java-dialects` monorepo contains Hibernate 5/6, Spring Data JDBC, JOOQ, Liquibase, Flyway modules. Native ORM `yoj-project` for immutable entities.
```

- [ ] **Step 7: Verify TODOs are gone**

```bash
grep -c 'TODO(author)' skills/ydb-core/SKILL.md
```
Expected: `0`.

```bash
grep -n 'TODO' skills/ydb-core/SKILL.md
```
Expected: no output.

- [ ] **Step 8: Commit**

```bash
git add skills/ydb-core/SKILL.md
git commit -m "ydb-core: prune unverified content and drop all TODO(author) markers

Removed: server LTS cadence note, C++ and .NET rows from the packages
table, CLI-profile section, Alembic/Django Python integrations stub,
JVM per-module-coordinates stub. Each was a placeholder for content
that wasn't grounded; per the project policy 'less but no TODOs', the
content is dropped rather than guessed at and can be added back when
verified against upstream."
```

---

## Task 2: Register `JV` prefix in `docs/authoring.md`

**Files:**
- Modify: `docs/authoring.md`

- [ ] **Step 1: Locate the placeholder row**

```bash
grep -n '_(none yet)_' docs/authoring.md
```
Expected: one match in the prefix registry table.

- [ ] **Step 2: Replace the placeholder row**

Old:
```
| _(none yet)_ | | |
```

New:
```
| JV | Java SDK / JDBC / Hibernate / Spring Data anti-patterns | skills/ydb-table/rules/embed/java.md |
```

- [ ] **Step 3: Verify**

```bash
grep -n 'JV' docs/authoring.md
```
Expected: at least one match in the registry table row.

- [ ] **Step 4: Commit**

```bash
git add docs/authoring.md
git commit -m "authoring: register JV prefix for Java SDK rules

First entry in the rule-prefix registry. Claimed for
skills/ydb-table/rules/embed/java.md."
```

---

## Task 3: Create `skills/ydb-table/references/bulk-write.md`

**Files:**
- Create: `skills/ydb-table/references/bulk-write.md`

- [ ] **Step 1: Verify — `AS_TABLE` transactionality and current page**

```bash
# YQL UPSERT reference
```

WebFetch `https://ydb.tech/docs/en/yql/reference/syntax/upsert_into` with prompt: "Does the page describe UPSERT … SELECT FROM AS_TABLE($list), and is this stated to run within a Query Service transaction? Quote the relevant lines."

Expected: page mentions `AS_TABLE` and confirms it's a regular YQL statement (therefore runs inside the surrounding transaction). If the page no longer mentions `AS_TABLE`, search for an alternative canonical doc page:

```bash
gh search code --repo ydb-platform/ydb 'AS_TABLE' --filename='*.md' | head -20
```

- [ ] **Step 2: Verify — `BulkUpsert` SDK method naming**

WebFetch `https://ydb.tech/docs/en/dev/batch-upload` with prompt: "What is the canonical name of the bulk-upload API across SDKs? Quote method names if listed per SDK."

Expected: page describes a `BulkUpsert` (or similarly named) API. If the naming varies per SDK, capture the variants — the reference will then say "the SDK exposes a bulk-upsert API (exact symbol varies; see SDK docs)" instead of locking in one name.

- [ ] **Step 3: Write the file**

Create `skills/ydb-table/references/bulk-write.md` with:

````markdown
# Bulk write into YDB tables

## What this is

Two YDB-level mechanisms for writing many rows at once:

- **`UPSERT INTO t SELECT … FROM AS_TABLE($list)`** — YQL, runs through the Query Service inside the surrounding transaction. Use for batches inside business operations.
- **`BulkUpsert`** — a separate SDK API (not YQL), non-transactional, parallelizes writes across partitions server-side. Use for ingest / migrations where throughput matters and transactionality does not.

Source: <https://ydb.tech/docs/en/yql/reference/syntax/upsert_into>, <https://ydb.tech/docs/en/dev/batch-upload>.

## Canonical pattern: `AS_TABLE`

```yql
DECLARE $items AS List<Struct<id: Uint64, value: Utf8>>;

UPSERT INTO t
SELECT id, value FROM AS_TABLE($items);
```

One query plan, one transaction, one round trip; because the query is parameterized, the server's plan cache reuses the same plan across calls.

## When to use which

`AS_TABLE` for transactional batches inside a business operation. `BulkUpsert` for ingest or migrations, where transactionality isn't required and throughput is.

## Related

- [`../../ydb-core/SKILL.md#schema-basics`](../../ydb-core/SKILL.md#schema-basics) — primary-key shape and partitioning determine batch-ingest efficiency.
````

If Step 2 turned up SDK-specific names, change the `BulkUpsert` bullet to use the language-agnostic phrasing ("an SDK bulk-upsert API; exact symbol varies per SDK — see SDK docs"). Adjust the doc link if Step 1 found a different canonical page.

- [ ] **Step 4: Verify the file is YDB-level only (no language tokens)**

```bash
grep -iE 'jdbc|hibernate|spring|java|jpa|python|golang|\.net|dotnet|csharp' \
  skills/ydb-table/references/bulk-write.md
```
Expected: no matches.

- [ ] **Step 5: Verify no `TODO(author)`**

```bash
grep -n 'TODO' skills/ydb-table/references/bulk-write.md
```
Expected: no output.

- [ ] **Step 6: Commit**

```bash
git add skills/ydb-table/references/bulk-write.md
git commit -m "ydb-table refs: add YDB-level bulk-write reference

AS_TABLE (transactional, inside business ops) vs BulkUpsert
(non-transactional, ingest/migrations). Language-agnostic;
per-language guidance lives in references/embed/<lang>.md."
```

---

## Task 4: Create `skills/ydb-table/references/transactions.md`

**Files:**
- Create: `skills/ydb-table/references/transactions.md`

- [ ] **Step 1: Verify — current set of isolation levels and Query Service default**

WebFetch `https://ydb.tech/docs/en/concepts/transactions` with prompt: "List the transaction modes supported by YDB Query Service, including the default. Distinguish read-only and read-write modes. Quote the exact mode names (e.g. SerializableRW, SnapshotRO, StaleRO, OnlineRO) and which are read-only."

Expected: confirmation of the four modes (`SerializableRW`, `SnapshotRO`, `StaleRO`, `OnlineRO`) and that `SerializableRW` is the default for the Query Service. If any of these have been deprecated or renamed, capture the current list and use that instead.

- [ ] **Step 2: Write the file**

Create `skills/ydb-table/references/transactions.md` with:

````markdown
# YDB transaction modes

## What this is

The Query Service supports four transaction modes:

- **`SerializableRW`** — the default. Read-write, server-side serializable. Conflicting transactions are detected by the server and surface as a retryable `ABORTED` (TLI — transaction locks invalidation).
- **`SnapshotRO`** — read-only, sees a consistent snapshot. Does not coordinate with concurrent writers.
- **`StaleRO`** — read-only, reads from any replica; may return stale data.
- **`OnlineRO`** — read-only, reads from the leader.

Source: <https://ydb.tech/docs/en/concepts/transactions>.

## Implication: application-level optimistic locking is redundant

The Postgres / Read-Committed pattern of carrying a `version` column and emitting `UPDATE … WHERE … AND version = ?` to catch lost updates is unnecessary under `SerializableRW`: the server already detects the conflict and surfaces it as a retryable failure. The extra predicate adds work on every UPDATE and provides no additional safety.

## Read-only loads

For purely read workloads, `SnapshotRO` is the right default — it reduces coordination cost with writers while still seeing a consistent view.

## Related

- [`../../ydb-core/SKILL.md#schema-basics`](../../ydb-core/SKILL.md#schema-basics) — schema choices interact with transaction cost (partition locality).
````

Adjust the mode list and default if Step 1 found different current names.

- [ ] **Step 3: Verify the file is YDB-level only (no language tokens)**

```bash
grep -iE 'jdbc|hibernate|spring|java|jpa|@version|python|golang|\.net|dotnet|csharp' \
  skills/ydb-table/references/transactions.md
```
Expected: no matches.

- [ ] **Step 4: Verify no `TODO(author)`**

```bash
grep -n 'TODO' skills/ydb-table/references/transactions.md
```
Expected: no output.

- [ ] **Step 5: Commit**

```bash
git add skills/ydb-table/references/transactions.md
git commit -m "ydb-table refs: add YDB-level transactions reference

Lists the four Query Service modes (SerializableRW default,
SnapshotRO, StaleRO, OnlineRO) and explains why app-level
optimistic locking is redundant under SerializableRW.
Language-agnostic; @Version-specific guidance lives in
rules/embed/java.md."
```

---

## Task 5: Create `skills/ydb-table/references/embed/java.md`

**Files:**
- Create: `skills/ydb-table/references/embed/java.md`

- [ ] **Step 1: Find a real `@YdbRetryable` usage example**

```bash
gh search code --repo ydb-platform/ydb-java-dialects 'YdbRetryable' --limit 20
```

Capture: (a) the FQN of the annotation, (b) which dialects module it lives in, (c) a real method-level usage example. If `gh search` returns nothing, fall back to:

```bash
gh api repos/ydb-platform/ydb-java-dialects/contents/ \
  --jq '.[] | select(.type == "dir") | .name'
```

then poke individual module READMEs.

If no usage can be located, do NOT invent the annotation. Mark Task 11 (RULE-JV-06) as blocked on this verification.

- [ ] **Step 2: Find the `ydb-jdbc-driver` examples README link**

```bash
gh api repos/ydb-platform/ydb-jdbc-driver/contents/README.md \
  --jq '.content' | base64 -d | head -80
```

Capture the README URL and any "examples" subdirectory link. This becomes the "see examples here" pointer in the Stack section.

- [ ] **Step 3: Write the file**

Create `skills/ydb-table/references/embed/java.md` with (replace each `__CAPTURED_*__` placeholder with the value found in Step 1 / Step 2 before saving):

````markdown
# Embedding YDB in Java applications

## Stack

YDB Java app code typically layers as: **ydb-java-sdk** → **ydb-jdbc-driver** → **Hibernate** → **Spring Data JPA**. Most application code uses the JDBC driver as the entry point. Connection-string format and authentication environment variables: see [`../../ydb-core/SKILL.md#connecting`](../../ydb-core/SKILL.md#connecting). Setup and connection examples: <__CAPTURED_JDBC_EXAMPLES_URL__>.

## Bulk operations

Canonical pattern for reading, inserting, and deleting batches via Spring Data JPA + Hibernate over YDB:

```java
@Service
public class TokenService {
    private final TokenRepository repository;

    @Transactional
    public List<Token> readMany(List<Long> ids) {
        return repository.findAllById(ids);
    }

    @Transactional
    public void writeMany(List<Token> tokens) {
        repository.saveAll(tokens);
    }

    @Transactional
    public void deleteMany(List<Long> ids) {
        repository.deleteAllByIdInBatch(ids);
    }
}
```

`application.properties`:

```properties
spring.jpa.properties.hibernate.jdbc.batch_size=1000
spring.jpa.properties.hibernate.order_inserts=true
spring.jpa.properties.hibernate.order_updates=true
```

Why: each method issues one statement instead of N. Batches form only when `batch_size` is set *and* statements are ordered — without `order_inserts` / `order_updates`, the session can't group like statements together. `deleteAllByIdInBatch` is the only delete variant that emits a single `DELETE … WHERE id IN (?, ?, …)`; `deleteAllById` does a SELECT per id before deleting.

For the underlying YDB-level mechanisms (`AS_TABLE`, `BulkUpsert`), see [`../bulk-write.md`](../bulk-write.md).

## Retries

The JDBC exception hierarchy classifies retryability. `SQLRecoverableException` (e.g. YDB `ABORTED`) is fully retryable for any operation. `SQLTransientConnectionException` (e.g. connection drop) is retryable only for idempotent operations — the server may have committed before the connection died, and re-issuing a non-idempotent statement risks double effect.

Spring path — use the annotation provided by ydb-java-dialects on the transactional method:

```java
@__CAPTURED_RETRYABLE_FQN__
@Transactional
public void insertBatch(List<Token> batch) {
    repository.saveAll(batch);
}
```

Plain JDBC path — classify the exception and retry accordingly:

```java
void runWithRetry(Connection c, boolean idempotent, JdbcOp op) throws SQLException {
    for (int attempt = 0; ; attempt++) {
        try {
            op.run(c);
            return;
        } catch (SQLRecoverableException e) {
            if (attempt >= MAX_RETRIES) throw e;
        } catch (SQLTransientConnectionException e) {
            if (!idempotent || attempt >= MAX_RETRIES) throw e;
        }
    }
}
```

## Transactions

YDB Query Service defaults to `SerializableRW`. Conflicting transactions are detected by the server and surface as retryable `SQLRecoverableException` (`ABORTED`). For the full mode list and the consequence for application-level optimistic locking, see [`../transactions.md`](../transactions.md).

## Connection

See [`../../ydb-core/SKILL.md#connecting`](../../ydb-core/SKILL.md#connecting).
````

Replace `__CAPTURED_JDBC_EXAMPLES_URL__` with the README URL from Step 2 and `__CAPTURED_RETRYABLE_FQN__` with the annotation discovered in Step 1 (drop the leading `@` since the line already starts with `@`).

If Step 1 could not locate `@YdbRetryable`, replace the Spring snippet with a one-line note: "Spring integration: ydb-java-dialects provides a Spring module with a retry annotation; see its README for the current annotation FQN." Do not invent a name.

- [ ] **Step 4: Verify no YDB-mechanism duplication**

```bash
grep -E '\bAS_TABLE\b|\bBulkUpsert\b|SerializableRW|SnapshotRO|StaleRO|OnlineRO' \
  skills/ydb-table/references/embed/java.md
```
Expected: only the references already present (`AS_TABLE` is mentioned once in the "see bulk-write" line; `SerializableRW` appears once in the Transactions section that pivots toward `transactions.md`). Anything beyond pointers means we're duplicating the YDB-level files.

- [ ] **Step 5: Verify no `TODO(author)` and no placeholders**

```bash
grep -nE 'TODO|__CAPTURED_' skills/ydb-table/references/embed/java.md
```
Expected: no output.

- [ ] **Step 6: Verify intra-skill links resolve**

```bash
for link in \
  skills/ydb-table/references/bulk-write.md \
  skills/ydb-table/references/transactions.md \
  skills/ydb-core/SKILL.md ; do
  test -f "$link" && echo "OK $link" || echo "MISSING $link"
done
```
Expected: three `OK` lines.

- [ ] **Step 7: Commit**

```bash
git add skills/ydb-table/references/embed/java.md
git commit -m "ydb-table refs: add Java embedding reference

Stack overview, bulk-operations canonical snippet (saveAll/
findAllById/deleteAllByIdInBatch with batch_size + order_inserts/
order_updates), retry classification, transaction note. Links to
bulk-write.md and transactions.md for YDB-level material; no
duplication."
```

---

## Task 6: Create `rules/embed/java.md` skeleton + RULE-JV-01

**Files:**
- Create: `skills/ydb-table/rules/embed/java.md`

- [ ] **Step 1: Write the file with header and RULE-JV-01**

Create `skills/ydb-table/rules/embed/java.md` with:

````markdown
# Java SDK / JDBC / Hibernate / Spring Data — anti-patterns

Audit rules for application code talking to YDB via the Java stack. Each rule is self-contained: the surface skill must produce correct audit output on its own. For positive patterns, see [`../../references/embed/java.md`](../../references/embed/java.md).

### RULE-JV-01: `findById` in a loop instead of `findAllById`

**Severity**: Medium

**What to look for**: calls to `findById(` inside `for` / `while` / `forEach` / `stream` blocks, or repeated `findById` calls against the same repository with different ids.

**Problem**: each `findById` is a separate `SELECT … WHERE id = ?` round trip; reading N keys this way costs N statements where one would do.

**Fix**:

```java
List<Token> tokens = repository.findAllById(ids);
```

**Source**: Spring Data JPA — `CrudRepository#findAllById(Iterable<ID>)` (returns the entities for the given ids in a single query). <https://docs.spring.io/spring-data/jpa/reference/repositories/crud-strategies.html>.
````

- [ ] **Step 2: Verify**

```bash
grep -n 'RULE-JV-' skills/ydb-table/rules/embed/java.md
```
Expected: exactly one match (`RULE-JV-01`).

```bash
grep -n 'TODO' skills/ydb-table/rules/embed/java.md
```
Expected: no output.

- [ ] **Step 3: Commit**

```bash
git add skills/ydb-table/rules/embed/java.md
git commit -m "ydb-table rules: seed Java anti-pattern catalog with RULE-JV-01

findById in a loop -> findAllById. First entry under the JV prefix
registered in docs/authoring.md."
```

---

## Task 7: Append RULE-JV-02 (JDBC batching not configured)

**Files:**
- Modify: `skills/ydb-table/rules/embed/java.md`

- [ ] **Step 1: Verify the recommended `batch_size` floor**

```bash
gh api repos/ydb-platform/ydb-jdbc-driver/contents/README.md \
  --jq '.content' | base64 -d | grep -i 'batch_size\|batch size\|batching'
gh search code --repo ydb-platform/ydb-java-dialects 'batch_size' --limit 10
```

If the upstream README or examples recommend a specific floor (e.g. ≥1000), use that number. If neither source recommends a specific number, drop the "≥1000" recommendation from the Fix and reword to: "Set explicitly to a value greater than 1; see `ydb-jdbc-driver` examples for tuning guidance."

- [ ] **Step 2: Append the rule**

Append to `skills/ydb-table/rules/embed/java.md`:

````markdown

### RULE-JV-02: JDBC batching not configured

**Severity**: High

**What to look for**: `application.properties` / `application.yml` files without `spring.jpa.properties.hibernate.jdbc.batch_size`, or Hibernate `persistence.xml` / `hibernate.cfg.xml` without `hibernate.jdbc.batch_size`. Also missing `hibernate.order_inserts` / `hibernate.order_updates`.

**Problem**: Hibernate's default JDBC batch size is 1 — every `INSERT` / `UPDATE` / `DELETE` is a separate statement and a separate network round trip. On write-heavy paths this multiplies cost.

**Fix**:

```properties
spring.jpa.properties.hibernate.jdbc.batch_size=__CAPTURED_BATCH_SIZE_VALUE__
spring.jpa.properties.hibernate.order_inserts=true
spring.jpa.properties.hibernate.order_updates=true
```

Batches form only when both batch size and ordering are enabled — without `order_inserts` / `order_updates`, the session can't group like statements together.

**Source**: Hibernate user guide — JDBC batching configuration. <https://docs.jboss.org/hibernate/orm/current/userguide/html_single/Hibernate_User_Guide.html#batch>. YDB JDBC driver examples: <https://github.com/ydb-platform/ydb-jdbc-driver>.
````

Replace `__CAPTURED_BATCH_SIZE_VALUE__` with the verified floor from Step 1 (e.g. `1000`) or rewrite the snippet to use a placeholder line and the explanation from Step 1's fallback.

- [ ] **Step 3: Verify**

```bash
grep -nE 'TODO|__CAPTURED_' skills/ydb-table/rules/embed/java.md
```
Expected: no output.

- [ ] **Step 4: Commit**

```bash
git add skills/ydb-table/rules/embed/java.md
git commit -m "ydb-table rules: add RULE-JV-02 (JDBC batching not configured)

Default hibernate.jdbc.batch_size is 1; without batch_size +
order_inserts/order_updates, writes degenerate to one round trip
per row."
```

---

## Task 8: Append RULE-JV-03 (save in a loop) and RULE-JV-04 (delete in a loop)

**Files:**
- Modify: `skills/ydb-table/rules/embed/java.md`

- [ ] **Step 1: Verify `deleteAllByIdInBatch` semantics**

WebFetch `https://docs.spring.io/spring-data/jpa/reference/jpa/repositories.html` with prompt: "How does Spring Data JPA's `JpaRepository#deleteAllByIdInBatch(Iterable<ID>)` differ from `CrudRepository#deleteAllById(Iterable<ID>)`? Quote the contract for each, especially whether the latter loads entities before deleting."

Expected: confirmation that `deleteAllById` (or `deleteAllInIterable`) issues per-entity loads to fulfill lifecycle callbacks, while `deleteAllByIdInBatch` emits a single bulk `DELETE`. If the contract has changed in a current Spring Data version, capture the actual behavior and reword the rule.

Also check that the YDB Hibernate dialect doesn't override the in-batch variant to do something weird:

```bash
gh search code --repo ydb-platform/ydb-java-dialects 'deleteAllByIdInBatch' --limit 10
```

If the dialect overrides this method to do per-entity work, soften the rule's Fix to: "use `deleteAllByIdInBatch` *if your dialect implements it as a single DELETE* — verify via SQL logging."

- [ ] **Step 2: Append RULE-JV-03**

Append:

````markdown

### RULE-JV-03: Spring `save()` in a loop

**Severity**: High

**What to look for**: `repository.save(` (or `entityManager.persist(`) inside `for` / `while` / `forEach` / `stream` blocks.

**Problem**: per-entity save defeats batching even when `hibernate.jdbc.batch_size` is set. Multiplicative cost with RULE-JV-02.

**Fix**:

```java
List<Token> batch = new ArrayList<>();
for (long id = firstId; id < lastId; id++) {
    batch.add(new Token("user_" + id));
}
repository.saveAll(batch);
```

**Source**: Spring Data JPA — `CrudRepository#saveAll(Iterable<S>)`. <https://docs.spring.io/spring-data/jpa/reference/repositories/crud-strategies.html>.
````

- [ ] **Step 3: Append RULE-JV-04**

Append:

````markdown

### RULE-JV-04: Spring `delete()` / `deleteAllById()` for bulk paths

**Severity**: High

**What to look for**: `repository.delete(` or `repository.deleteAllById(` in bulk-delete paths (loops, batch services). Anywhere a list of ids is being removed.

**Problem**: Spring Data JPA's `deleteAllById(Iterable<ID>)` issues a `findById` per id before each `DELETE` (to satisfy entity lifecycle callbacks) — N `SELECT` + N `DELETE`. Strictly worse than naive `delete()`-in-loop.

**Fix**:

```java
repository.deleteAllByIdInBatch(ids);
```

Emits a single `DELETE … WHERE id IN (?, ?, …)`.

**Source**: Spring Data JPA — `JpaRepository#deleteAllByIdInBatch(Iterable<ID>)`. <https://docs.spring.io/spring-data/jpa/reference/jpa/repositories.html>.
````

If Step 1 found that the YDB dialect overrides the in-batch variant, adjust this rule's Fix and Source accordingly before saving.

- [ ] **Step 4: Verify**

```bash
grep -c 'RULE-JV-' skills/ydb-table/rules/embed/java.md
```
Expected: `4`.

```bash
grep -nE 'TODO|__CAPTURED_' skills/ydb-table/rules/embed/java.md
```
Expected: no output.

- [ ] **Step 5: Commit**

```bash
git add skills/ydb-table/rules/embed/java.md
git commit -m "ydb-table rules: add RULE-JV-03 and RULE-JV-04

save() / deleteAllById() in a loop — use saveAll and
deleteAllByIdInBatch respectively. deleteAllById issues a
findById per id before each DELETE."
```

---

## Task 9: Append RULE-JV-05 (`@Version` over YDB)

**Files:**
- Modify: `skills/ydb-table/rules/embed/java.md`

- [ ] **Step 1: Verify the `EXPLAIN` claim**

This is the most claim-dense rule. The "non-index-friendly predicate / full table scan" claim is plan-dependent. Try, in order:

1. Search for existing analysis in upstream:

   ```bash
   gh search code --repo ydb-platform/ydb-java-dialects 'Version' --extension java --limit 30
   gh api search/issues -X GET \
     -f q='repo:ydb-platform/ydb-java-dialects @Version' \
     --jq '.items[] | {title: .title, url: .html_url}'
   ```

2. If a local YDB is available, run an `EXPLAIN` on the equivalent of `UPDATE t SET version = version + 1, payload = ? WHERE id = ? AND version = ?` against a table where `id` is the PK and `version` is a non-indexed column. Capture the plan.

**Resolution**:
- If a FullScan-equivalent plan is confirmed, keep the rule wording sharp ("forces a full scan").
- If the plan only shows an additional predicate without a scan (likely with `id` as PK), soften the wording to "adds a non-index-friendly predicate to every UPDATE" and keep Severity at High based on the redundancy + extra-work argument.
- If neither verification path produces evidence, drop the rule for this iteration and add a follow-up TODO to the spec (do not ship an unsubstantiated claim).

- [ ] **Step 2: Append the rule**

Append (assume the "softened" wording — adjust upward if Step 1 confirmed FullScan):

````markdown

### RULE-JV-05: JPA `@Version` (optimistic locking) over YDB

**Severity**: High

**What to look for**: `@Version` annotations on JPA entity fields.

**Problem**: YDB Query Service runs `SerializableRW` by default — conflicting transactions are detected by the server and surface as a retryable `ABORTED`. `@Version` adds `WHERE … AND version = ?` to every `UPDATE`; the predicate is on a non-key column, adds work to every update, and provides no additional safety because server-side serializability already prevents lost updates.

**Fix**: remove `@Version` from the entity. Let conflicts surface from the server and handle them via the retry classification in RULE-JV-06.

```java
@Entity
public class Token {
    @Id private Long id;
    private String payload;
    // no @Version field
}
```

**Source**: YDB transaction modes — <https://ydb.tech/docs/en/concepts/transactions>. JPA `@Version` semantics — <https://jakarta.ee/specifications/persistence/3.1/jakarta-persistence-spec-3.1.html#a2058>.
````

If Step 1 confirmed FullScan, change "adds work to every update" to "forces a full table scan on every UPDATE."

- [ ] **Step 3: Verify**

```bash
grep -c 'RULE-JV-' skills/ydb-table/rules/embed/java.md
```
Expected: `5`.

- [ ] **Step 4: Commit**

```bash
git add skills/ydb-table/rules/embed/java.md
git commit -m "ydb-table rules: add RULE-JV-05 (JPA @Version over YDB)

@Version is redundant under SerializableRW (server detects conflicts)
and adds a non-index-friendly predicate to every UPDATE."
```

---

## Task 10: Append RULE-JV-06 (ignoring retryable JDBC exceptions)

**Files:**
- Modify: `skills/ydb-table/rules/embed/java.md`

- [ ] **Step 1: Verify the JDBC exception mapping in `ydb-jdbc-driver`**

```bash
gh search code --repo ydb-platform/ydb-jdbc-driver 'SQLRecoverableException' --extension java --limit 30
gh search code --repo ydb-platform/ydb-jdbc-driver 'SQLTransientConnectionException' --extension java --limit 30
gh search code --repo ydb-platform/ydb-jdbc-driver 'ABORTED' --extension java --limit 30
```

Expected to find: code paths where YDB `ABORTED` (and related TLI statuses) are translated into `SQLRecoverableException`, and connection-failure statuses into `SQLTransientConnectionException` (or a subtype).

**Resolution**:
- If the mapping matches the rule as written, keep the rule.
- If the driver uses different `SQLException` subtypes (e.g. `SQLTransientException` directly instead of `SQLTransientConnectionException`), update the rule to name the actual subtypes the driver throws.
- If neither subtype appears in the driver source at all, the rule's Fix must be reworded to "inspect the underlying YDB status code via the driver's status-extraction API (verify exact method against `ydb-jdbc-driver` source)." Don't invent.

- [ ] **Step 2: Verify `@YdbRetryable` (re-use Task 5 Step 1 result if already captured)**

If Task 5 located the annotation's FQN and module, use that directly. Otherwise:

```bash
gh search code --repo ydb-platform/ydb-java-dialects 'YdbRetryable' --extension java --limit 20
```

If the annotation cannot be found, the Spring path of the Fix is replaced with a generic "use the retry-annotation from the appropriate ydb-java-dialects Spring module; consult its README." Don't fabricate the FQN.

- [ ] **Step 3: Append the rule**

Append (replace `__CAPTURED_RETRYABLE_FQN__` with the value from Step 2):

````markdown

### RULE-JV-06: Ignoring retryable JDBC exceptions

**Severity**: Critical

**What to look for**: `catch (SQLException …)` blocks that log and continue, or that retry unconditionally without inspecting the subtype. Absence of `@__CAPTURED_RETRYABLE_FQN__` (or an equivalent manual classifying retry loop) around transactional methods.

**Problem**: the JDBC exception hierarchy classifies failures, and the two categories want different handling:

- `SQLRecoverableException` — fully retryable (YDB `ABORTED` from TLI, etc.). Safe to retry for any operation. Not retrying means losing work that would have succeeded on retry.
- `SQLTransientConnectionException` — connection-level failure. The server may have committed before the connection died; re-issuing a non-idempotent statement risks double effect (double charge, duplicate insert). Safe to retry only for idempotent operations (UPSERT, idempotency-key-protected writes, reads).

Catching the supertype `SQLException` and retrying both cases the same way violates this contract in one direction or the other.

**Fix**:

Spring path — annotate the transactional method:

```java
@__CAPTURED_RETRYABLE_FQN__
@Transactional
public void insertBatch(List<Token> batch) {
    repository.saveAll(batch);
}
```

Plain JDBC path — classify the exception and treat connection failures as idempotency-gated:

```java
void runWithRetry(Connection c, boolean idempotent, JdbcOp op) throws SQLException {
    for (int attempt = 0; ; attempt++) {
        try {
            op.run(c);
            return;
        } catch (SQLRecoverableException e) {
            if (attempt >= MAX_RETRIES) throw e;
        } catch (SQLTransientConnectionException e) {
            if (!idempotent || attempt >= MAX_RETRIES) throw e;
        }
    }
}
```

**Source**: `java.sql.SQLRecoverableException` and `SQLTransientConnectionException` — <https://docs.oracle.com/en/java/javase/21/docs/api/java.sql/java/sql/SQLException.html>. ydb-jdbc-driver exception mapping: <https://github.com/ydb-platform/ydb-jdbc-driver>. ydb-java-dialects Spring retry annotation: <https://github.com/ydb-platform/ydb-java-dialects>.
````

If Step 2 could not locate `@YdbRetryable`, drop the Spring snippet and replace with: "Spring path — ydb-java-dialects provides a Spring module with a retry annotation; consult its README for the current annotation FQN."

- [ ] **Step 4: Verify**

```bash
grep -c 'RULE-JV-' skills/ydb-table/rules/embed/java.md
```
Expected: `6`.

```bash
grep -nE 'TODO|__CAPTURED_' skills/ydb-table/rules/embed/java.md
```
Expected: no output.

- [ ] **Step 5: Commit**

```bash
git add skills/ydb-table/rules/embed/java.md
git commit -m "ydb-table rules: add RULE-JV-06 (ignoring retryable JDBC exceptions)

SQLRecoverableException retried always; SQLTransientConnectionException
retried only for idempotent operations. Catching the supertype erases
the classification."
```

---

## Task 11: Acceptance sweep

**Files:** (no file changes; verification only)

- [ ] **Step 1: `ydb-core` has zero TODOs**

```bash
grep -rn 'TODO(author)' skills/ydb-core
```
Expected: no output.

- [ ] **Step 2: Prefix registry contains JV**

```bash
grep -n '| JV |' docs/authoring.md
```
Expected: one match.

- [ ] **Step 3: Six Java rules exist with non-empty Source links**

```bash
grep -c '^### RULE-JV-' skills/ydb-table/rules/embed/java.md
```
Expected: `6`.

```bash
grep -c '\*\*Source\*\*:' skills/ydb-table/rules/embed/java.md
```
Expected: `6`.

```bash
grep -nE 'TODO|__CAPTURED_' skills/ydb-table/rules/embed/java.md
```
Expected: no output.

- [ ] **Step 4: YDB-level references stay language-agnostic**

```bash
grep -iE 'jdbc|hibernate|spring|java|jpa|@version|python|golang|\.net|dotnet|csharp' \
  skills/ydb-table/references/bulk-write.md \
  skills/ydb-table/references/transactions.md
```
Expected: no output.

- [ ] **Step 5: All intra-skill links resolve**

```bash
python3 - <<'PY'
import re, pathlib, sys
root = pathlib.Path('skills')
bad = []
for f in root.rglob('*.md'):
    text = f.read_text()
    for m in re.finditer(r'\]\((?!https?://|#)([^)]+)\)', text):
        target = (f.parent / m.group(1).split('#')[0]).resolve()
        if not target.exists():
            bad.append((str(f), m.group(1)))
for b in bad:
    print('BROKEN', *b)
sys.exit(1 if bad else 0)
PY
```
Expected: exit code 0, no output.

- [ ] **Step 6: All staged work is committed**

```bash
git status --short
```
Expected: empty (all changes from Tasks 1–10 committed).

- [ ] **Step 7: Summary report**

```bash
git log --oneline main..HEAD
```
Expected: 10 commits, one per task (Tasks 1, 2, 3, 4, 5, 6, 7, 8, 9, 10). Capture this list — that's the deliverable for the iteration.

---

## Self-review notes

- Spec coverage: every spec deliverable (ydb-core prune, JV prefix, six rules, three new reference files) maps to a task. Acceptance criteria from the spec are checked one-for-one in Task 11.
- Placeholders: all `__CAPTURED_*__` tokens have explicit "what to do if verification fails" branches. None ship to `main`.
- Type / name consistency: `findAllById`, `saveAll`, `deleteAllByIdInBatch`, `@Version`, `SQLRecoverableException`, `SQLTransientConnectionException`, `SerializableRW` — used consistently across `embed/java.md` reference and rule file.
- Verification-first ordering: rules with high-risk claims (JV-02 batch_size floor, JV-04 dialect override, JV-05 plan claim, JV-06 exception mapping + annotation FQN) have a Verify step *before* the rule is written. If verification fails, the rule is reworded or dropped; nothing is shipped on faith.
