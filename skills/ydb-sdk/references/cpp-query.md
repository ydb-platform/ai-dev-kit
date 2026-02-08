# C++ Query (ydb-cpp-sdk) — Query/Table Service

## Query Rules

### RULE-Q05: Using deprecated Scripting Service
**Severity**: Medium

**What to look for**: `#include <ydb-cpp-sdk/client/draft/ydb_scripting.h>`, `NScripting::TScriptingClient`, `ExecuteYqlScript`.

```cpp
// BAD
#include <ydb-cpp-sdk/client/draft/ydb_scripting.h>
NYdb::NScripting::TScriptingClient client(driver);
auto result = client.ExecuteYqlScript("SELECT * FROM series").GetValueSync();

// GOOD
#include <ydb-cpp-sdk/client/query/client.h>
NYdb::NQuery::TQueryClient client(driver);
auto result = client.ExecuteQuery(
    "SELECT * FROM series",
    NYdb::NQuery::TTxControl::NoTx()
).GetValueSync();
```

### RULE-Q06: Expecting >1000 rows from Table Service
**Severity**: High

**What to look for**: `TTableClient` + `ExecuteDataQuery` for queries returning many rows.

```cpp
// BAD: Table Service — 1000 row limit
TTableClient client(driver);
auto session = client.GetSession().GetValueSync().GetSession();
auto result = session.ExecuteDataQuery(
    "SELECT * FROM events ORDER BY ts",
    TTxControl::BeginTx(TTxSettings::SerializableRW()).CommitTx()
).GetValueSync();
// max 1000 rows

// GOOD: Query Service — no row limit
TQueryClient queryClient(driver);
auto result = queryClient.ExecuteQuery(
    "SELECT * FROM events ORDER BY ts",
    TTxControl::BeginTx(TTxSettings::SerializableRW()).CommitTx()
).GetValueSync();
```

### RULE-Q15: Parallel queries on single session (SESSION_BUSY)
**Severity**: High

**What to look for**: Multiple concurrent `ExecuteQuery` calls on same `TSession` object, async futures on one session.

```cpp
// BAD: parallel queries on same session
client.RetryQuerySync([](TSession session) -> TStatus {
    auto future1 = session.ExecuteQuery(...);
    auto future2 = session.ExecuteQuery(...); // SESSION_BUSY!
    return ...;
});

// GOOD: separate retry for each parallel query
auto status1 = client.RetryQuerySync([](TSession session) -> TStatus {
    return session.ExecuteQuery(...).GetValueSync();
});
auto status2 = client.RetryQuerySync([](TSession session) -> TStatus {
    return session.ExecuteQuery(...).GetValueSync();
});
```
