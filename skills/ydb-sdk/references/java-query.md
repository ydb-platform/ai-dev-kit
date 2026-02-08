# Java Query & Transactions (ydb-java-sdk / JDBC) — Query/Table Service, Transactions

## Query Rules

### RULE-Q06: Expecting >1000 rows from Table Service
**Severity**: High

**What to look for**: `session.executeDataQuery()` for queries returning many rows.

```java
// BAD: Table Service — 1000 row limit
try (Session session = tableClient.createSession().join().getValue()) {
    Result<ResultSetReader> result = session.executeDataQuery(
        "SELECT * FROM events ORDER BY ts",
        TxControl.serializableRw().setCommitTx(true), Params.empty()
    ).join();
    // rs.getRowCount() — max 1000
}

// GOOD: JDBC with Query Service
try (Connection conn = DriverManager.getConnection(
        "jdbc:ydb:grpc://localhost:2136/local?useQueryService=true")) {
    try (ResultSet rs = conn.createStatement()
            .executeQuery("SELECT * FROM events ORDER BY ts")) {
        while (rs.next()) { /* no 1000-row limit */ }
    }
}
```

---

## Transaction Rules

### RULE-TX05: Not handling TLI for idempotent operations
**Severity**: High

**What to look for**: Transaction code without idempotency flag, especially `SerializableReadWrite` mode.

```java
// BAD: no idempotent flag, TLI won't be retried
Retry.retryWithSettings(RetrySettings.newBuilder().build(), () -> {
    session.executeDataQuery(query, txControl, params).join();
    return null;
});

// GOOD: idempotent=true allows TLI retry
Retry.retryWithSettings(
    RetrySettings.newBuilder().idempotent(true).build(), () -> {
    session.executeDataQuery(query, txControl, params).join();
    return null;
});
```
