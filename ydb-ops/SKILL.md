---
name: ydb-ops
description: >
  Help with YDB cluster operations, configuration, monitoring, and troubleshooting.
  Use when the user asks about YDB deployment, configuration tuning, monitoring setup,
  capacity planning, backup/restore, cluster maintenance, or incident response.
  Triggers on: YDB config, YDB monitoring, YDB deploy, YDB cluster, YDB backup,
  YDB performance tuning, YDB alerts, YDB Grafana, YDB Prometheus, YDB Kubernetes,
  YDB Ansible, ydb admin, cluster health, rolling restart.
---

# YDB DevOps Assistant

Help with YDB cluster deployment, configuration, monitoring, and operational tasks.

## Workflow

### 1. Understand the task

Determine the operational context:
- **Deployment**: initial setup, Kubernetes, bare metal, Docker
- **Configuration**: tuning server-side settings for workload
- **Monitoring**: setting up metrics, dashboards, alerts
- **Capacity planning**: sizing clusters, partitioning strategy
- **Maintenance**: rolling restarts, version upgrades, backups
- **Incident response**: diagnosing issues, recovering from failures

### 2. Load relevant references

- **Cluster configuration**: [references/cluster-config.md](references/cluster-config.md)
- **Monitoring and alerting**: [references/monitoring.md](references/monitoring.md)
- **Deployment patterns**: [references/deployment.md](references/deployment.md)
- **Troubleshooting guide**: [references/troubleshooting.md](references/troubleshooting.md)

### 3. Provide guidance

When advising on configuration:
- Start with recommended defaults, explain when to change
- Always consider the blast radius of config changes
- Recommend testing on staging before production
- Provide rollback procedures

When setting up monitoring:
- Cover the critical metrics: latency, TLI rate, partition count, storage usage
- Set up both alerting and dashboards
- Recommend appropriate TTL for metrics storage
