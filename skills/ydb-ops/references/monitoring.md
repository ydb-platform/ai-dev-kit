# Monitoring and Alerting Reference

TODO: Add monitoring reference covering:
- Key metrics to monitor:
  - Query latency (p50, p99)
  - TLI rate (Transaction Locks Invalidated)
  - Partition count and auto-split activity
  - Storage usage per database/table
  - CPU utilization per node
  - gRPC connection stats
  - Topic consumer lag
- Prometheus scrape configuration for YDB
- Grafana dashboard templates
- Alert rules:
  - High TLI rate
  - Storage approaching limits
  - Latency degradation
  - Node unavailability
  - Topic consumer lag
- TTL for metrics (operational: 30d, business: 90d, debug: 7d)
- Dynamic log level management (ydb admin log set-level)
