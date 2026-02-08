# SQL to YQL Migration Reference

TODO: Add SQL dialect differences covering:
- PostgreSQL -> YQL differences
- MySQL -> YQL differences
- Key syntax differences:
  - No AUTO_INCREMENT (use hash-based keys)
  - No DEFAULT values on columns
  - No FOREIGN KEY constraints
  - UPSERT instead of INSERT ... ON CONFLICT
  - $param instead of $1 / ? placeholders
  - VIEW hint for index selection
  - AS_TABLE($list) instead of bulk VALUES
  - String::StartsWith instead of LIKE 'prefix%'
  - No stored procedures / triggers
  - No sequences
  - Multi-statement queries in single request
