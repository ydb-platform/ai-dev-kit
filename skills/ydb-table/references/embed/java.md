# Embedding YDB in Java applications

## Stack

YDB Java app code typically layers as: **ydb-java-sdk** → **ydb-jdbc-driver** → **Hibernate** → **Spring Data JPA**. Most application code uses the JDBC driver as the entry point. Connection-string format and authentication environment variables: see [`../../../ydb-core/SKILL.md#connecting`](../../../ydb-core/SKILL.md#connecting). Setup and connection examples: <https://github.com/ydb-platform/ydb-jdbc-driver>. Worked Spring Data JDBC / JPA / Flyway / jOOQ / Liquibase examples: <https://github.com/ydb-platform/ydb-java-examples/tree/master/jdbc>.

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

For the underlying YDB-level mechanisms (`AS_TABLE`, `BulkUpsert`), see [`../working-with-data.md`](../working-with-data.md).

## Retries

The `ydb-jdbc-driver` classifies retryability through the standard `java.sql` exception hierarchy. Concrete subtypes (see `tech.ydb.jdbc.exception` in the driver):

- `YdbRetryableException extends SQLRecoverableException` — base retryable statuses (e.g. `ABORTED`). Safe to retry for any operation.
- `YdbUnavailbaleException extends SQLTransientConnectionException` — `TRANSPORT_UNAVAILABLE`. Retry only for idempotent operations: the server may have committed before the connection died.
- `YdbConditionallyRetryableException extends SQLTransientException` — other transient statuses including `TIMEOUT`. Retry only for idempotent operations.

So in plain JDBC: catch `SQLRecoverableException` unconditionally; catch `SQLTransientException` (and its `SQLTransientConnectionException` subtype) only when the call is idempotent.

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

Failsafe library form, taken from the official jdbc-driver example
(<https://github.com/ydb-platform/ydb-java-examples/blob/master/jdbc/failsafe-example/src/main/java/tech/ydb/jdbc/failsafe/Main.java>):

```java
private static final RetryPolicy<?> DEFAULT_POLICY = RetryPolicy.builder()
        .handle(SQLRecoverableException.class)
        .withBackoff(100, 1000, ChronoUnit.MILLIS, 2)
        .withMaxDuration(Duration.ofSeconds(5))
        .build();

private static final RetryPolicy<?> IDEMPOTENT_POLICY = RetryPolicy.builder()
        .handle(SQLRecoverableException.class, SQLTransientException.class)
        .withBackoff(100, 1000, ChronoUnit.MILLIS, 2)
        .withMaxDuration(Duration.ofSeconds(5))
        .build();
```

Spring path — `ydb-java-dialects` does not currently ship a retry annotation. The official example app
(<https://github.com/ydb-platform/ydb-java-examples/tree/master/jdbc/ydb-token-app>) defines a thin
meta-annotation over Spring Retry that you can copy or adapt:

```java
@Target({ ElementType.METHOD, ElementType.TYPE })
@Retention(RetentionPolicy.RUNTIME)
@Retryable(
        retryFor = { SQLRecoverableException.class, SQLTransientException.class },
        maxAttempts = MAX_RETRIES,
        backoff = @Backoff(delay = 100, multiplier = 2.0, maxDelay = 5000, random = true)
)
public @interface YdbRetryable { /* AliasFor passthroughs */ }
```

Applied to a transactional service method:

```java
@YdbRetryable
@Transactional
public void loadData(int firstID, int lastID) {
    List<Token> batch = new ArrayList<>();
    for (int id = firstID; id < lastID; id++) {
        batch.add(new Token("user_" + id));
    }
    tokenRepo.saveAll(batch);
}
```

Note that this annotation in the example app retries `SQLTransientException` for *all* annotated methods, which is only safe because every annotated operation there is idempotent. In your own code, restrict the non-`SQLRecoverableException` catch to methods you know are idempotent.

## Transactions

YDB Query Service defaults to `SerializableRW`. Conflicting transactions are detected by the server and surface as retryable `SQLRecoverableException` (`ABORTED`). For the full mode list and the consequence for application-level optimistic locking, see [`../working-with-data.md`](../working-with-data.md).

## Connection

See [`../../../ydb-core/SKILL.md#connecting`](../../../ydb-core/SKILL.md#connecting).
