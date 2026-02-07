# YDB Architecture Overview (for reviewers)

## What is YDB
Distributed OLTP database with horizontal scaling. Tables are automatically partitioned (sharded) by primary key ranges.

## Key Concepts

### Sessions
A session is a **single-threaded actor** on the server side. One session = one query at a time. Sending parallel queries to one session causes `SESSION_BUSY` error (400190). Use session pools and let SDK manage sessions.

### Optimistic Locking & TLI
YDB uses **optimistic concurrency control** (MVCC). Transactions don't take locks during reads — conflicts are detected at commit time. When a conflict occurs, the transaction fails with **TLI** (Transaction Locks Invalidated). TLI is **normal and expected** — code MUST handle it via retries. The idempotency flag tells the SDK it's safe to retry automatically.

### Partitioning
Each table is split into partitions by PK ranges. One partition = one tablet actor = one CPU core max. Hot partitions (monotonic PK writes, single-partition load) are the #1 performance problem. Auto-split by load can help but takes time (~500ms per split).

### Table Service vs Query Service
- **Table Service** (legacy): 1000-row limit per response, `KeepInCache` off by default, unary gRPC
- **Query Service** (modern, production-ready since YDB 24.3): no row limit, streaming, query cache on by default

### Transaction Buffer
YDB accumulates write data in memory before commit. Buffer limit is **64MB** per transaction. Exceeding it = transaction failure.

### Query Compilation
YDB compiles YQL text into an execution plan. Plans are cached per-node in an LRU cache. Non-parametrized queries (values inline) waste cache and add CPU overhead.

## Error Handling Model
YDB errors are classified by the SDK into:
- **Retryable** (transient): OVERLOADED, UNAVAILABLE, BAD_SESSION, TLI — SDK retries automatically (if idempotent flag is set where needed)
- **Non-retryable**: SCHEME_ERROR, GENERIC_ERROR, PRECONDITION_FAILED — no point retrying

Using SDK retry wrappers (`Do()`, `DoTx()`, `execute_with_retries()`) is **mandatory**, not optional.
