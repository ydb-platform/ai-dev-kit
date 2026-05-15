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
