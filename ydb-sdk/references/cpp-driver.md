# C++ Driver (ydb-cpp-sdk) — Connection, Balancer

## SDK Detection
- Include: `#include <ydb-cpp-sdk/...>`
- Namespace: `NYdb::`, `NYdb::NQuery::`, `NYdb::NTable::`
- CMake: `ydb-cpp-sdk`

## Correct Usage Cheat Sheet

```cpp
// Driver initialization
auto driverConfig = NYdb::TDriverConfig(connectionString)
    .SetBalancingPolicy(NYdb::TBalancingPolicy::UseAllNodes());
NYdb::TDriver driver(driverConfig);

// Query Service (preferred)
NYdb::NQuery::TQueryClient client(driver);
auto status = client.RetryQuerySync([](NYdb::NQuery::TSession session) -> NYdb::TStatus {
    auto result = session.ExecuteQuery(
        "SELECT * FROM users WHERE id = $id",
        NYdb::NQuery::TTxControl::BeginTx(NYdb::NQuery::TTxSettings::SerializableRW()).CommitTx(),
        NYdb::TParamsBuilder().AddParam("$id").Uint64(userId).Build().Build()
    ).GetValueSync();
    return result;
});
```

---

## RULE-B01: PreferLocalDC / default balancing policy
**Severity**: High

**What to look for**: `TDriverConfig` without `SetBalancingPolicy`, or explicit `PreferLocalDC`.

```cpp
// BAD: default may use prefer_local_dc
auto driverConfig = NYdb::TDriverConfig(connectionString);

// GOOD
auto driverConfig = NYdb::TDriverConfig(connectionString)
    .SetBalancingPolicy(NYdb::TBalancingPolicy::UseAllNodes());
```
