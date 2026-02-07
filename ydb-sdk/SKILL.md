---
name: ydb-sdk
description: >
  Review code that uses YDB SDK for anti-patterns, performance issues, and incorrect usage.
  Covers Go, Python, Java, C++, C#, YQL/SQL, Terraform, and YDB CLI.
  Use when the user asks to review, audit, lint, or check code that interacts with YDB. 
  Also use when user asks to find YDB anti-patterns, fix YDB SDK usage,
  or optimize YDB queries. Triggers on mentions of: YDB review, YDB SDK check, YDB anti-patterns,
  YDB best practices, YDB code audit, ydb-go-sdk, ydb-python-sdk, ydb-cpp-sdk, ydb-java-sdk.
  Supports two modes: analysis-only (report findings) and fix mode (apply corrections).
---

# YDB SDK Reviewer

Review code for incorrect YDB SDK usage, anti-patterns, and performance issues across all supported languages and frameworks.

## Workflow

### 1. Identify scope and languages

Determine what to review and detect languages/frameworks used:

| Language | Detection |
|----------|-----------|
| Go | `github.com/ydb-platform/ydb-go-sdk` |
| Python | `import ydb` |
| Java | `tech.ydb`, `jdbc:ydb:` |
| C++ | `#include <ydb-cpp-sdk/...>`, `NYdb::` |
| C# | `using Ydb.Sdk` |
| YQL/SQL | `.yql` files, `CREATE TABLE`, `UPSERT`, `SELECT` with YDB syntax |
| Terraform | `yandex_ydb_table`, `ycp_ydb_table` |
| CLI | `ydb` commands in scripts |

### 2. Load references

Always load:
- **YDB overview**: [references/ydb-overview.md](references/ydb-overview.md) — architecture context
- **Common rules**: [references/common-rules.md](references/common-rules.md) — schema, YQL, config rules

Then load ONLY the subsystem-specific file(s) matching detected code:

**Go:**
- [references/go-driver.md](references/go-driver.md) — connection, balancer, sessions, retry
- [references/go-query.md](references/go-query.md) — Query/Table Service, transactions
- [references/go-topics.md](references/go-topics.md) — Topics (CDC, Streams)

**Python:**
- [references/python-driver.md](references/python-driver.md) — connection, retry, configuration
- [references/python-query.md](references/python-query.md) — Query/Table Service, transactions
- [references/python-topics.md](references/python-topics.md) — Topics

**Java:**
- [references/java-driver.md](references/java-driver.md) — connection, retry (JDBC & native)
- [references/java-query.md](references/java-query.md) — Query/Table Service, transactions
- [references/java-topics.md](references/java-topics.md) — Topics

**C++:**
- [references/cpp-driver.md](references/cpp-driver.md) — connection, balancer
- [references/cpp-query.md](references/cpp-query.md) — Query/Table Service

**C#:**
- [references/csharp-query.md](references/csharp-query.md) — Query Service, ADO.NET

**Infrastructure:**
- [references/terraform.md](references/terraform.md) — Terraform resources
- [references/cli.md](references/cli.md) — CLI scripts

### 3. Scan and report

For each file, check against rules from loaded references. Report findings as:

```
## Review Results

### [filename:line] RULE-XX: Rule title
**Severity**: Critical/High/Medium/Low
**Issue**: Description of what's wrong
**Current code**:
\`\`\`
<problematic code snippet>
\`\`\`
**Recommended fix**:
\`\`\`
<corrected code snippet>
\`\`\`
```

Group findings by severity (Critical first).

### 4. Apply fixes (if requested)

If the user asks to fix issues (not just report), apply corrections using the Edit tool. Always explain what was changed and why.
