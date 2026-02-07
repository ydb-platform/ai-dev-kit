# Java Driver (ydb-java-sdk / JDBC) — Connection, Retry

## SDK Detection
- Import: `tech.ydb`, `com.yandex.ydb`
- JDBC: `jdbc:ydb:` connection string
- Maven/Gradle: `tech.ydb:ydb-sdk-*`

## Correct Usage Cheat Sheet

```java
// JDBC (recommended — uses Query Service by default)
try (Connection conn = DriverManager.getConnection("jdbc:ydb:grpc://localhost:2136/local")) {
    try (PreparedStatement ps = conn.prepareStatement(
            "SELECT * FROM users WHERE id = ?")) {
        ps.setLong(1, userId);
        try (ResultSet rs = ps.executeQuery()) {
            while (rs.next()) { /* process */ }
        }
    }
}

// Native SDK with retry
RetrySettings retrySettings = RetrySettings.newBuilder()
    .maxRetries(5)
    .idempotent(true)
    .build();

Retry.retryWithSettings(retrySettings, () -> {
    try (Session session = tableClient.createSession().join().getValue()) {
        session.executeDataQuery(query, txControl, params).join();
    }
    return null;
});
```

---

## Retry Rules

### RULE-R02: Manual retry loops
**Severity**: High

**What to look for**: `for` / `while` loops with `Thread.sleep()` wrapping YDB calls. Custom retry logic.

```java
// BAD
for (int i = 0; i < 10; i++) {
    try {
        session.executeDataQuery(query, txControl, params).join();
        break;
    } catch (Exception e) {
        Thread.sleep(100);
    }
}

// GOOD: use SDK retry
RetrySettings settings = RetrySettings.newBuilder()
    .maxRetries(5)
    .idempotent(true)
    .build();
Retry.retryWithSettings(settings, () -> {
    session.executeDataQuery(query, txControl, params).join();
    return null;
});
```

### RULE-R07: Missing idempotent flag
**Severity**: High

**What to look for**: `RetrySettings` without `.idempotent(true)` for read or UPSERT operations.

```java
// BAD
RetrySettings settings = RetrySettings.newBuilder().maxRetries(5).build();

// GOOD
RetrySettings settings = RetrySettings.newBuilder()
    .maxRetries(5)
    .idempotent(true)
    .build();
```
