# Common Rules (Language-Agnostic)

Rules detectable in YQL/SQL, schema definitions, configuration files. Apply regardless of SDK language.

---

## Schema Design

### RULE-T01: Monotonically increasing primary key
**Severity**: Critical

**What to look for**: `AUTO_INCREMENT`, `SERIAL`, `SEQUENCE`, monotonic UUID, timestamp-first PK, integer-only PK on growing tables.

**Problem**: All writes go to the last partition = hot spot. One partition = one CPU core max.

**Fix**: Hash prefix + monotonic counter as composite PK.

```sql
-- BAD
CREATE TABLE events (
    id Uint64,
    data String,
    PRIMARY KEY (id)
);

-- GOOD
CREATE TABLE events (
    hash Uint64,       -- Digest::NumericHash(id)
    id Uint64,
    data String,
    PRIMARY KEY (hash, id)
) WITH (
    AUTO_PARTITIONING_BY_LOAD = ENABLED,
    AUTO_PARTITIONING_MIN_PARTITIONS_COUNT = 4,
    AUTO_PARTITIONING_MAX_PARTITIONS_COUNT = 100
);
```

### RULE-T02: Missing AUTO_PARTITIONING_MIN_PARTITIONS_COUNT
**Severity**: Medium

**What to look for**: `AUTO_PARTITIONING_MIN_PARTITIONS_COUNT = 1` or absent in CREATE/ALTER TABLE.

**Problem**: Default min=1 allows merging all partitions into one during low load. Re-splitting takes ~500ms per split.

**Fix**: Set min partitions >= 2, preferably matching node count.

### RULE-T03: AUTO_PARTITIONING_BY_LOAD disabled
**Severity**: High

**What to look for**: `AUTO_PARTITIONING_BY_LOAD = DISABLED` or absent on tables with significant traffic.

**Problem**: Hot partitions cannot be split automatically.

**Fix**: Enable for any table with non-trivial workload.

### RULE-T04: Large partitions without size tuning
**Severity**: Medium

**What to look for**: Tables without `AUTO_PARTITIONING_PARTITION_SIZE_MB`, or default 2000MB on high-load tables.

**Problem**: Default 2GB may be too large for high-throughput tables.

**Fix**: Set 100-500MB for high-load tables.

### RULE-T05: Missing secondary indexes on filtered columns
**Severity**: High

**What to look for**: `WHERE` on non-PK columns without corresponding index. Queries filtering by email, status, etc. without index.

**Problem**: FullScan — reads all rows. Gets slower as data grows.

**Fix**: Create secondary index, use `VIEW idx_name` hint.

```sql
ALTER TABLE users ADD INDEX idx_email GLOBAL ON (email);
SELECT * FROM users VIEW idx_email WHERE email = 'user@example.com';
```

### RULE-T06: No upper bound on index partition count
**Severity**: Medium

**What to look for**: Indexes without `AUTO_PARTITIONING_MAX_PARTITIONS_COUNT` (default=50).

**Problem**: Default max=50 may be insufficient for large datasets.

**Fix**: Set explicit max matching expected data volume.

### RULE-T07: No compaction tuning for bulk deletes
**Severity**: Low

**What to look for**: Large DELETE operations without compaction config changes.

**Problem**: Tombstones from deletions still occupy space.

**Fix**: Tune `BackgroundCompaction` settings.

### RULE-T08: Over-normalization beyond 3NF
**Severity**: Medium

**What to look for**: Multiple JOINs, many small lookup tables, 4NF+ patterns.

**Problem**: Excessive JOINs increase TLI frequency and query complexity.

**Fix**: Limit to 3NF. Denormalize frequently co-accessed data.

### RULE-T09: No compression for large text/JSON fields
**Severity**: Low

**What to look for**: `Json`, `Utf8`, `String` columns storing large data without column family compression.

**Problem**: Up to 60-80% storage savings possible.

**Fix**: Use column families with LZ4 or ZSTD compression.

```sql
CREATE TABLE logs (
    id Uint64,
    log_text Utf8 FAMILY compressed,
    PRIMARY KEY (id),
    FAMILY default (COMPRESSION = "lz4"),
    FAMILY compressed (COMPRESSION = "zstd", COMPRESSION_LEVEL = 5)
);
```

---

## YQL Query Patterns

### RULE-Q04: Assuming result order without ORDER BY
**Severity**: Medium

**What to look for**: SELECT without ORDER BY where code assumes specific row ordering.

**Problem**: YDB does not guarantee result order without ORDER BY. Order may change between executions.

**Fix**: Always specify ORDER BY when order matters.

### RULE-Q08: LIKE for prefix search instead of StartsWith
**Severity**: Medium

**What to look for**: `WHERE column LIKE 'prefix%'` patterns.

**Problem**: LIKE may not use index. StartsWith is optimized for prefix matching.

**Fix**: Use `String::StartsWith(column, 'prefix')` or range comparison `column >= 'prefix' AND column < 'prefiy'`.

```sql
-- BAD
SELECT * FROM users WHERE email LIKE 'admin%';

-- GOOD
SELECT * FROM users WHERE StartsWith(email, 'admin');
```

### RULE-Q14: DECLARE with EmptyList parameter mismatch
**Severity**: Medium

**What to look for**: `DECLARE $list AS List<SomeType>` where the parameter might be an empty list at runtime.

**Problem**: If app passes `EmptyList` as parameter, it doesn't match `List<SomeType>` — query fails.

**Fix**: Remove explicit DECLARE (supported since YDB 25.1) or handle empty list separately.

```sql
-- BAD: fails when $ids is empty
DECLARE $ids AS List<Uint64>;
SELECT * FROM t WHERE id IN $ids;

-- GOOD: no DECLARE, type inferred from parameter
SELECT * FROM t WHERE id IN $ids;
```

### RULE-Q16: Wrong INSERT vs UPSERT choice
**Severity**: Medium

**What to look for**: `UPSERT` on tables with many sync indexes. `INSERT` for idempotent operations.

**Problem**: UPSERT with sync indexes reads + updates all indexes (slow). INSERT without indexes has existence check overhead.

**Fix**: Use UPSERT for tables without sync indexes. Use INSERT for tables with sync indexes. Always prefer batch operations.

### RULE-Q18: VIEW hint missing for secondary index queries
**Severity**: Medium

**What to look for**: SELECT with WHERE on indexed column but without `VIEW index_name`.

**Problem**: Without VIEW hint, YDB may not use the index, falling back to FullScan.

**Fix**: Add `VIEW index_name` after table name.

```sql
-- BAD
SELECT * FROM users WHERE email = 'user@example.com';

-- GOOD
SELECT * FROM users VIEW idx_email WHERE email = 'user@example.com';

-- Also works for primary key
SELECT * FROM t VIEW PRIMARY KEY WHERE key_col = $value;
```

---

## Configuration

### RULE-CFG01: Full TRACE logging in production
**Severity**: High

**What to look for**: `default_level: 8` (TRACE), `sampling_rate: 1` with high levels in production configs.

**Problem**: TRACE adds 20-30% CPU overhead, +5-10ms latency, massive log volume.

**Fix**: NOTICE (5) as default with sampling for DEBUG/TRACE.

```yaml
# BAD
log_config:
  default_level: 8  # TRACE

# GOOD
log_config:
  default_level: 5  # NOTICE
  default_sampling_level: 7  # DEBUG
  default_sampling_rate: 20  # 5% of DEBUG messages
```

### RULE-CFG02: No TTL for monitoring metrics
**Severity**: Medium

**What to look for**: Monitoring configs without `retention` or `TTL`, `scrape_interval: 5s` without filtering.

**Problem**: Metrics accumulate indefinitely, causing storage overflow.

**Fix**: Set TTL: 30 days for operational, 90+ days for business metrics.

### RULE-C01: Aggressive gRPC keep-alive settings
**Severity**: Medium

**What to look for**: gRPC keep-alive time < 10 seconds, `GRPC_ARG_KEEPALIVE_TIME_MS` < 10000.

**Problem**: Too frequent pings cause `too_many_pings` errors, leading to connection drops.

**Fix**: Use default settings (10s intervals minimum). Let SDK manage keep-alive.
