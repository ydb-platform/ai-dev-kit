# Embedding YDB in C++ applications

## Stack

The official C++ SDK is **`ydb-cpp-sdk`** (<https://github.com/ydb-platform/ydb-cpp-sdk>). Public API lives in namespace `NYdb::inline V3` under `#include <ydb-cpp-sdk/client/...>`.

Two application surfaces for table work:

- **`NYdb::NQuery::TQueryClient`** — Query Service. Preferred for new YQL-centric code. Supports `TTxControl::NoTx()` for DDL, `StreamExecuteQuery` for large reads, `ReadCommittedRW` transaction mode.
- **`NYdb::NTable::TTableClient`** — Table / KQP Service. Use for `PrepareDataQuery`, `BulkUpsert`, `StreamExecuteScanQuery`, schema builders (`TTableBuilder`, `CreateTable`). `NTable::TTxControl` has no `NoTx()` — DDL via `CreateTable` / `ExecuteSchemeQuery`.

Open one **`NYdb::TDriver`** per process; stack surface clients on top. APIs return `NThreading::TFuture<T>`; examples block with `.GetValueSync()` / `.ExtractValueSync()`.

Build: C++20, static libraries. CMake consumer pattern from upstream README:

```cmake
find_package(ydb-cpp-sdk REQUIRED COMPONENTS Driver Query Table)
target_link_libraries(myapp PRIVATE YDB-CPP-SDK::Driver YDB-CPP-SDK::Query)
```

Debian packages: `libydb-cpp-dev` (core), optional `libydb-cpp-iam-dev`. After install, pass `-DCMAKE_PREFIX_PATH=/usr/share/yandex`.

Primary documentation: <https://ydb.tech/docs/en/reference/ydb-sdk/>. Runnable demos for orientation: <https://github.com/ydb-platform/ydb-cpp-sdk/tree/main/examples> — illustrative, not normative.

## Connection

See [`../../../ydb-core/SKILL.md#connecting`](../../../ydb-core/SKILL.md#connecting) for connection-string shape and auth env vars.

```cpp
#include <ydb-cpp-sdk/client/driver/driver.h>

auto cfg = NYdb::TDriverConfig()
    .SetEndpoint("grpc://localhost:2136")
    .SetDatabase("/local")
    .SetAuthToken(std::getenv("YDB_TOKEN") ? std::getenv("YDB_TOKEN") : "");
NYdb::TDriver driver(cfg);
// ... work ...
driver.Stop(true);
```

`TDriverConfig` also accepts a connection string: `grpc://host:port/?database=/path` or `grpcs://...`. Credentials factories: `CreateOAuthCredentialsProviderFactory`, `CreateInsecureCredentialsProviderFactory` — `include/ydb-cpp-sdk/client/types/credentials/credentials.h`.

For production code, prefer letting the SDK pick credentials from the standard `YDB_*` environment variables via `NYdb::CreateFromEnvironment(connectionString)` in `include/ydb-cpp-sdk/client/helpers/helpers.h` — it returns a ready `TDriverConfig` honouring `YDB_SERVICE_ACCOUNT_KEY_FILE_CREDENTIALS`, `YDB_ACCESS_TOKEN_CREDENTIALS`, `YDB_METADATA_CREDENTIALS`, `YDB_OAUTH2_KEY_FILE`, and `YDB_ANONYMOUS_CREDENTIALS`. The full env-var list is in [`../../../ydb-core/SKILL.md#connecting`](../../../ydb-core/SKILL.md#connecting).

## Query execution

Canonical Query Service pattern — `RetryQuerySync` wraps a lambda; the lambda is the retry unit:

```cpp
#include <ydb-cpp-sdk/client/query/client.h>
#include <ydb-cpp-sdk/client/params/params.h>

using namespace NYdb::NQuery;

static TStatus SelectUserById(TSession session) {
    auto params = TParamsBuilder()
        .AddParam("$id").Uint64(42).Build()
        .Build();
    return session.ExecuteQuery(
        "SELECT name FROM users WHERE id = $id",
        TTxControl::BeginTx(TTxSettings::SerializableRW()).CommitTx(),
        params
    ).GetValueSync();
}

ThrowOnError(client.RetryQuerySync(
    SelectUserById,
    NYdb::NRetry::TRetryOperationSettings().Idempotent(true)));
```

Three load-bearing pieces:

- **`TRetryOperationSettings().Idempotent(true)`** on `RetryQuerySync` / `RetryOperationSync` declares replay-safe work. Required for reads and for writes keyed on a client-generated id. Omit on non-idempotent writes (counter increment, unkeyed `INSERT`).
- **`TParamsBuilder`** binds values — do not concatenate them into the query text. A leading `DECLARE` block is optional for scalars; use it for `List<Struct<...>>` and other compound shapes.
- **Build results inside the lambda.** Assign to outer variables only on the success path (the returned `TStatus` is success). Mutations to outer state mid-lambda survive across retry attempts.

Source: YDB docs — retry recipe at <https://ydb.tech/docs/en/recipes/ydb-sdk/retry> and parameterized queries at <https://ydb.tech/docs/en/reference/ydb-sdk/parameterized_queries>.

## Transactions

**Single-statement** — fuse begin and commit in `TTxControl`:

```cpp
TTxControl::BeginTx(TTxSettings::SerializableRW()).CommitTx()
```

**Multi-step client logic** — first query opens the tx (no `CommitTx`), second commits:

```cpp
auto result = session.ExecuteQuery(query1, TTxControl::BeginTx(TTxSettings::SerializableRW()), params1)
    .GetValueSync();
auto tx = *result.GetTransaction();
auto result2 = session.ExecuteQuery(query2, TTxControl::Tx(tx).CommitTx(), params2).GetValueSync();
```

Per the YDB transactions guide: "if the transaction body is fully formed before accessing the database, it will be processed more efficiently" — fuse with `CommitTx()` whenever client logic doesn't sit between statements.

For transaction modes and optimistic-locking consequences, see [`../working-with-data.md`](../working-with-data.md).

Source: YDB docs — <https://ydb.tech/docs/en/concepts/transactions>.

## Retries

YDB uses optimistic concurrency — application code that talks to YDB must run inside SDK retriers, not as bare one-shot RPCs.

`RetryQuerySync` / `RetryOperationSync` classify errors internally per the YDB status-code table:

- **Always retried**: `ABORTED`, `OVERLOADED`, `CLIENT_RESOURCE_EXHAUSTED`, `UNAVAILABLE`, `BAD_SESSION`, `SESSION_BUSY` (session reset).
- **Retried only when `.Idempotent(true)`**: `UNDETERMINED`, `TRANSPORT_UNAVAILABLE`.
- **Non-retryable**: schema / semantic failures (`SCHEME_ERROR`, `BAD_REQUEST`, `PRECONDITION_FAILED`) — propagated to caller.

No outer `for` loop or hand-rolled `Sleep` backoff around SDK calls. Tune via `TRetryOperationSettings` (`MaxRetries`, `FastBackoffSettings`, `SlowBackoffSettings`).

Source: YDB docs — status-code retry table at <https://ydb.tech/docs/en/reference/ydb-sdk/ydb-status-codes>, retry recipe at <https://ydb.tech/docs/en/recipes/ydb-sdk/retry>, error-handling guidance at <https://ydb.tech/docs/en/reference/ydb-sdk/error_handling>.

## Result parsing

```cpp
TResultSetParser parser(result.GetResultSet(0));
while (parser.TryNextRow()) {
    auto id = parser.ColumnParser("id").GetOptionalUint64();
}
```

## Bulk upsert

Non-transactional ingest via Table client:

```cpp
NYdb::TValueBuilder rows;
rows.BeginList().AddListItem().BeginStruct()
    .AddMember("id").Uint64(1)
    .AddMember("payload").Utf8("x")
    .EndStruct().EndList();

struct TBulkUpsertOp {
    std::string TablePath;
    NYdb::TValue Rows;
    TStatus operator()(NYdb::NTable::TTableClient& tableClient) const {
        return tableClient.BulkUpsert(TablePath, Rows).GetValueSync();
    }
};

client.RetryOperationSync(
    TBulkUpsertOp{tablePath, rows.Build()},
    NYdb::NTable::TRetryOperationSettings().Idempotent(true).MaxRetries(20));
```

`BulkUpsert` is UPSERT-keyed (insert-or-overwrite by primary key), so replaying the same chunk converges to the same final state — that's why `.Idempotent(true)` is safe here and is the conventional setting. Each `BulkUpsert` call is its own non-transactional batch, not part of a surrounding `TTxControl`.

When bulk is appropriate vs `AS_TABLE` in a transaction — see [`../working-with-data.md`](../working-with-data.md).

Source: YDB docs — batch upload guide at <https://ydb.tech/docs/en/dev/batch-upload> (non-transactional ingest path, incompatible with synchronous secondary indexes).

## Large reads

Pick one structural path:

- **Query Service streaming** — `client.StreamExecuteQuery(...)` returns `TExecuteQueryIterator`; iterate with `ReadNext()`. The SDK may replay the lambda on retry, so an in-progress stream can re-emit already-seen rows — consumers must tolerate duplicates or dedupe.
- **Table Service scan** — `session.StreamExecuteScanQuery(...)` for unbounded scans without the Table `ExecuteDataQuery` result cap.
- **Keyset pagination** — outer loop with cursor predicate over the primary key; each page is its own `RetryQuerySync` call. See [`../working-with-data.md`](../working-with-data.md).

If using `ExecuteDataQuery`, check `TResultSet::Truncated()` — a `true` value means the result was cut off and the read must be continued (pagination or streaming).

Source: YDB docs — paging guide at <https://ydb.tech/docs/en/dev/paging> (keyset pagination over the primary key as the canonical strategy).
