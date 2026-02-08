# Query Optimization Reference

TODO: Add query optimization reference covering:
- Reading EXPLAIN / EXPLAIN ANALYZE output
- TableFullScan vs TableRangeScan vs TableLookup
- Index selection and VIEW hints
- Covering indexes (COVER clause)
- StartsWith vs LIKE for prefix search
- Batch sizing for IN queries
- KeepInCache and query plan caching
- Multi-statement queries (reducing round-trips)
- Pagination patterns (keyset pagination by PK)
- Partitioning-aware query design
- Avoiding hot partitions in queries
