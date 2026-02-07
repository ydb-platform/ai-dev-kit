# Troubleshooting Guide

TODO: Add troubleshooting reference covering:
- Common errors and their causes:
  - OVERLOADED — tablet CPU saturation, need partitioning
  - SESSION_BUSY — parallel queries on one session
  - SCHEME_ERROR — schema mismatch, stale cache
  - UNAVAILABLE — node/network issues
  - DEADLINE_EXCEEDED — query timeout
  - Transaction locks invalidated (TLI) — normal, needs retry
  - Out of buffer memory — transaction > 64MB
  - too_many_pings — gRPC keep-alive too aggressive
- Diagnostic tools:
  - YDB CLI: ydb admin, ydb monitoring
  - YDB UI (Embedded UI)
  - EXPLAIN / EXPLAIN ANALYZE
  - System tables (system.tablets, system.nodes)
- Performance investigation workflow
- Incident response checklist
