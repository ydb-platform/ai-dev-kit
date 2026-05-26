# Balancing and sessions in C++ (`ydb-cpp-sdk`)

Principles: [`../balancing.md`](../balancing.md), [`../session-lifecycle.md`](../session-lifecycle.md).

## Default = prefer-DC (unlike Go/Python)

`include/ydb-cpp-sdk/client/driver/driver.h`:

```cpp
//! default: TBalancingPolicy::UsePreferableLocation()
```

`src/client/driver/driver.cpp`:

```cpp
TBalancingPolicy::TImpl BalancingSettings =
    TBalancingPolicy::TImpl::UsePreferableLocation(std::nullopt);
```

Code that builds `TDriverConfig(connStr)` and never calls `SetBalancingPolicy(...)` runs prefer-DC implicitly. Override required for the spread-everywhere default.

## Opt out: `UseAllNodes()`

```cpp
auto driverConfig = NYdb::TDriverConfig(connectionString)
    .SetBalancingPolicy(NYdb::TBalancingPolicy::UseAllNodes());
```

Source: `ydb-cpp-sdk/tests/slo_workloads/utils/utils.cpp`.

## API

`include/ydb-cpp-sdk/client/types/ydb.h`:

```cpp
class TBalancingPolicy {
public:
    static TBalancingPolicy UsePreferableLocation(const std::optional<std::string>& location = {});
    static TBalancingPolicy UseAllNodes();
};
```

`UsePreferableLocation(location)` accepts an optional explicit DC; same failure modes as the Go `PreferLocalDC` family.

## Sessions

Use the client pool (`NYdb::NQuery::TQueryClient` / `NYdb::NTable::TTableClient`) and its per-call helpers. Do not store `TSession` in a struct field across operations.
