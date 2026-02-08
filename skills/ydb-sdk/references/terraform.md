# Terraform Anti-Patterns

## Detection
Resource types: `yandex_ydb_table`, `ycp_ydb_table`, `yandex_ydb_database_serverless`, `ycp_ydb_database`

---

## RULE-T01: Monotonically increasing primary key

**Severity**: Critical

**What to look for**: Integer-only or timestamp-first primary key on tables expected to grow.

**Problem**: All writes go to last partition, creating a hot spot.

**Fix**: Use hash prefix in composite PK.

```hcl
# BAD
resource "yandex_ydb_table" "events" {
  column { name = "id"   type = "Uint64" }
  column { name = "data" type = "Utf8" }
  primary_key = ["id"]
}

# GOOD
resource "yandex_ydb_table" "events" {
  column { name = "hash" type = "Uint64" }
  column { name = "id"   type = "Uint64" }
  column { name = "data" type = "Utf8" }
  primary_key = ["hash", "id"]

  partitioning_settings {
    auto_partitioning_by_load         = true
    auto_partitioning_min_parts_count = 4
    auto_partitioning_max_parts_count = 100
  }
}
```

---

## RULE-T02: auto_partitioning_min_parts_count = 1

**Severity**: Medium

**What to look for**: `auto_partitioning_min_parts_count = 1` or missing this setting.

**Problem**: YDB can merge all partitions into one during low load. When load returns, splitting takes ~500ms per split.

**Fix**: Set min partitions >= 2, preferably matching node count.

```hcl
# BAD
partitioning_settings {
  auto_partitioning_min_parts_count = 1
}

# GOOD
partitioning_settings {
  auto_partitioning_min_parts_count = 4
  auto_partitioning_max_parts_count = 100
}
```

---

## RULE-T03: AUTO_PARTITIONING_BY_LOAD disabled

**Severity**: High

**What to look for**: `auto_partitioning_by_load = false` or missing on tables with significant traffic.

**Problem**: Hot partitions cannot be automatically split.

**Fix**: Enable for any table with non-trivial workload.

```hcl
# BAD
partitioning_settings {
  auto_partitioning_by_load = false
}

# GOOD
partitioning_settings {
  auto_partitioning_by_load = true
}
```

---

## RULE-CFG02: No TTL for monitoring metrics

**Severity**: Medium

**What to look for**: `ycp_ydb_database` or monitoring resources without `retention` or TTL settings.

**Problem**: Metrics accumulate indefinitely, causing storage overflow.

**Fix**: Set TTL: 30 days for operational metrics, 90+ days for business metrics.

```hcl
# BAD
resource "ycp_ydb_database" "db" {
  monitoring_config {
    enabled = true
    # no retention settings
  }
}

# GOOD
resource "ycp_ydb_database" "db" {
  monitoring_config {
    enabled                    = true
    retention_storage_interval = "PT24H"
    storage_retention_period   = "P30D"
  }
}
```
