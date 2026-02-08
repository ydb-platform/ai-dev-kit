# Schema Design Reference

TODO: Add schema design reference covering:
- Primary key design (avoiding monotonic keys, hash prefixes)
- Partitioning settings (AUTO_PARTITIONING_BY_LOAD, MIN/MAX partitions, partition size)
- Secondary indexes (GLOBAL SYNC, GLOBAL ASYNC, covering indexes)
- Column families and compression (LZ4, ZSTD)
- TTL (automatic row deletion by timestamp)
- Denormalization strategies (3NF limit for YDB)
- Row-oriented vs column-oriented tables
- Data types selection (Uint64 vs Int64, Utf8 vs String, Json vs JsonDocument)
