# Embedding YDB in C++ applications

Official SDK: **`ydb-cpp-sdk`** (<https://github.com/ydb-platform/ydb-cpp-sdk>), namespace `NYdb`, headers `#include <ydb-cpp-sdk/client/...>`.

- **`NYdb::NQuery::TQueryClient`** — Query Service (preferred): `ExecuteQuery`, `StreamExecuteQuery`, fused `TTxControl`. Transaction modes: <https://ydb.tech/docs/en/recipes/ydb-sdk/tx-control>.
- **`NYdb::NTable::TTableClient`** — Table Service: `ExecuteDataQuery`, `BulkUpsert`, `StreamExecuteScanQuery`, `ExecuteSchemeQuery`.
- One **`NYdb::TDriver`** per process; clients are cheap on top. C++20. Docs: <https://ydb.tech/docs/en/reference/ydb-sdk/>.

Connection details: [`../../../ydb-core/SKILL.md#connecting`](../../../ydb-core/SKILL.md#connecting). Production: `NYdb::CreateFromEnvironment(connectionString)` (`helpers/helpers.h`).

## Query pattern

`RetryQuerySync(lambda, TRetryOperationSettings)` — the **lambda is the retry unit**; the lambda receives `TSession session`. See <https://ydb.tech/docs/en/recipes/ydb-sdk/retry>. Second arg: `.Idempotent(true)` when replay-safe (reads, client-keyed UPSERT); omit for non-idempotent writes.

```cpp
ThrowOnError(client.RetryQuerySync(
    [] (TSession session) {
        auto p = TParamsBuilder().AddParam("$id").Uint64(42).Build().Build();
        return session.ExecuteQuery(
            "SELECT name FROM users WHERE id = $id",
            TTxControl::BeginTx(TTxSettings::SnapshotRO()).CommitTx(), p
        ).GetValueSync();
    },
    NYdb::NRetry::TRetryOperationSettings().Idempotent(true)));
```

Bind values with **`TParamsBuilder`** — never concatenate into YQL. Build results **inside** the lambda; assign outers only on success (see [`rules/embed/cpp.md`](../../rules/embed/cpp.md) RULE-CPP-02).

## Transactions

Single statement: `TTxControl::BeginTx(TTxSettings::SerializableRW()).CommitTx()` on the query call. Multi-step: first query `BeginTx()` without `CommitTx`, later `TTxControl::Tx(tx).CommitTx()`. Modes: [`../working-with-data.md`](../working-with-data.md), <https://ydb.tech/docs/en/recipes/ydb-sdk/tx-control>.

## Retries

Use SDK retriers — not outer `for` on `RetryQuerySync` (RULE-CPP-04) and not `sleep_for` + bare `ExecuteQuery` (RULE-CPP-05). Status classes: always-retry (`ABORTED`, `UNAVAILABLE`, `BAD_SESSION`); conditional with `.Idempotent(true)` (`UNDETERMINED`, `TRANSPORT_UNAVAILABLE`); non-retryable (`PRECONDITION_FAILED`, `SCHEME_ERROR`). Tune via `TRetryOperationSettings`. Source: <https://ydb.tech/docs/en/recipes/ydb-sdk/retry>, <https://ydb.tech/docs/en/reference/ydb-sdk/ydb-status-codes>.

## Large reads & streams

- **`ExecuteDataQuery`**: check `TResultSet::Truncated()` or paginate / use `StreamExecuteScanQuery` (RULE-CPP-01).
- **`StreamExecuteQuery`**: wrap with `RetryQuerySync`; `ReadNext()` parts. Retrier replay can re-emit rows — dedupe side effects. RULE-CPP-09; see <https://ydb.tech/docs/en/dev/example-app/example-cpp#stream-query>.

```cpp
ThrowOnError(client.RetryQuerySync(
    [] (TSession session) -> TStatus {
        auto stream = session.StreamExecuteQuery(
            "SELECT id FROM events", TTxControl::NoTx()).GetValueSync();
        if (!stream.IsSuccess()) {
            return stream;
        }
        // ReadNext loop — side effects must be idempotent per key
        return TStatus(EStatus::SUCCESS, NYdb::NIssue::TIssues());
    }));
```

## Bulk upsert

`TTableClient::BulkUpsert` via `RetryOperationSync` — non-transactional, UPSERT-keyed, `.Idempotent(true)` conventional. See <https://ydb.tech/docs/en/dev/batch-upload> and [`../working-with-data.md`](../working-with-data.md).
