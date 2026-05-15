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

**Source**: Spring Data Commons — `CrudRepository#findAllById(Iterable<ID>)` (returns all instances of the type with the given ids in a single call). <https://docs.spring.io/spring-data/commons/docs/current/api/org/springframework/data/repository/CrudRepository.html>.

### RULE-JV-02: JDBC batching not configured

**Severity**: High

**What to look for**: `application.properties` / `application.yml` files without `spring.jpa.properties.hibernate.jdbc.batch_size`, or Hibernate `persistence.xml` / `hibernate.cfg.xml` without `hibernate.jdbc.batch_size`. Also missing `hibernate.order_inserts` / `hibernate.order_updates`.

**Problem**: Hibernate's default JDBC batch size is 1 — every `INSERT` / `UPDATE` / `DELETE` is a separate statement and a separate network round trip. On write-heavy paths this multiplies cost.

**Fix**:

```properties
spring.jpa.properties.hibernate.jdbc.batch_size=1000
spring.jpa.properties.hibernate.order_inserts=true
spring.jpa.properties.hibernate.order_updates=true
```

Batches form only when both batch size and ordering are enabled — without `order_inserts` / `order_updates`, the session can't group like statements together. The upstream `ydb-token-app` example (`ydb-java-examples/jdbc/ydb-token-app/src/main/resources/application.properties`) uses `batch_size=1000`.

**Source**: Hibernate user guide — JDBC batching configuration. <https://docs.hibernate.org/orm/6.6/userguide/html_single/#batch>. YDB JDBC driver examples: <https://github.com/ydb-platform/ydb-jdbc-driver>.

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

**Source**: Spring Data JPA — `CrudRepository#saveAll(Iterable<S>)`. <https://docs.spring.io/spring-data/commons/docs/current/api/org/springframework/data/repository/CrudRepository.html>.

### RULE-JV-04: Spring `delete()` / `deleteAllById()` for bulk paths

**Severity**: High

**What to look for**: `repository.delete(` or `repository.deleteAllById(` in bulk-delete paths (loops, batch services). Anywhere a list of ids is being removed.

**Problem**: Spring Data JPA's `deleteAllById(Iterable<ID>)` calls `deleteById(id)` per id, and `deleteById` does `findById(id).ifPresent(this::delete);` — N `SELECT` + N `DELETE`. Strictly worse than naive `delete()`-in-loop. (Verified in `SimpleJpaRepository.deleteAllById` / `deleteById`, spring-data-jpa current source.)

**Fix**:

```java
repository.deleteAllByIdInBatch(ids);
```

JavaDoc: "Deletes the entities identified by the given ids using a single query. This kind of operation leaves JPAs first level cache and the database out of sync. Consider flushing the `EntityManager` before calling this method." Emits a single `DELETE … WHERE id IN (?, ?, …)` (verify via SQL logging — current ydb-java-dialects does not override this method).

**Source**: Spring Data JPA — `JpaRepository#deleteAllByIdInBatch(Iterable<ID>)`. <https://docs.spring.io/spring-data/jpa/docs/current/api/org/springframework/data/jpa/repository/JpaRepository.html>.

### RULE-JV-05: JPA `@Version` (optimistic locking) over YDB

**Severity**: High

**What to look for**: `@Version` annotations on JPA entity fields.

**Problem**: YDB Query Service runs `SerializableRW` by default — conflicting transactions are detected by the server and surface as a retryable `ABORTED`. `@Version` adds `WHERE … AND version = ?` to every `UPDATE`. The predicate is on a non-key column and adds work to every UPDATE; on YDB it provides no additional safety because server-side serializability under SerializableRW already prevents lost updates.

**Fix**: remove `@Version` from the entity. Let conflicts surface from the server and handle them via the retry classification in RULE-JV-06.

```java
@Entity
public class Token {
    @Id private Long id;
    private String payload;
    // no @Version field
}
```

**Source**: YDB transaction modes — <https://ydb.tech/docs/en/concepts/transactions>. JPA `@Version` semantics — <https://jakarta.ee/specifications/persistence/3.1/jakarta-persistence-spec-3.1.html#a2059>.

### RULE-JV-06: Ignoring retryable JDBC exceptions

**Severity**: Critical

**What to look for**: `catch (SQLException …)` blocks that log and continue, or that retry unconditionally without inspecting the subtype. Absence of any retry classification around transactional methods that talk to YDB.

**Problem**: the `ydb-jdbc-driver` surfaces failures through the standard `java.sql` exception hierarchy, and the two categories the JDBC contract exposes want different handling:

- `SQLRecoverableException` — fully retryable. Safe to retry for any operation. Not retrying loses work that would have succeeded on retry.
- `SQLTransientException` — the server may have already committed before the failure surfaced. Retrying a non-idempotent statement (`INSERT`, decrement, transfer) risks double effect. Safe to retry only for idempotent operations: `UPSERT`, idempotency-key-protected writes, reads.

These are the two types JDBC consumers should branch on. Driver-internal subclasses exist but should not be referenced from application code — they are not part of the published contract and can change.

Catching the supertype `SQLException` (or `Exception`) and retrying both categories the same way violates the contract in one direction or the other.

**Fix**:

Plain JDBC — classify the exception and treat transients as idempotency-gated:

```java
static final int MAX_RETRIES = 15;

void runWithRetry(Connection c, boolean idempotent, JdbcOp op) throws SQLException {
    for (int attempt = 0; ; attempt++) {
        try {
            op.run(c);
            return;
        } catch (SQLRecoverableException e) {
            if (attempt >= MAX_RETRIES) throw e;
        } catch (SQLTransientException e) {
            if (!idempotent || attempt >= MAX_RETRIES) throw e;
        }
    }
}
```

Spring path — `ydb-java-dialects` does not ship a retry annotation; hand-roll Spring Retry's `@Retryable` with the YDB exception buckets, or copy the meta-annotation pattern from the upstream example app (`ydb-java-examples/jdbc/ydb-token-app`). Note: retrying `SQLTransientException` for all annotated methods is only safe when those methods are themselves idempotent.

```java
@Retryable(
    retryFor = { SQLRecoverableException.class, SQLTransientException.class },
    maxAttempts = MAX_RETRIES,
    backoff = @Backoff(delay = 100, multiplier = 2.0, maxDelay = 5000, random = true)
)
@Transactional
public void insertBatch(List<Token> batch) {
    repository.saveAll(batch);
}
```

**Source**: `java.sql.SQLRecoverableException`, `SQLTransientException` — <https://docs.oracle.com/en/java/javase/21/docs/api/java.sql/java/sql/SQLException.html>. Example meta-annotation pattern: <https://github.com/ydb-platform/ydb-java-examples/tree/master/jdbc/ydb-token-app>.
