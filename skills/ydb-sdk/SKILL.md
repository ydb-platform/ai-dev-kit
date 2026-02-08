---
name: ydb-sdk
description: >
  This skill should be used when the user asks to "review YDB code", "check YDB SDK usage",
  "find YDB anti-patterns", "audit YDB best practices", "fix YDB SDK issues",
  "optimize YDB queries in code", or mentions ydb-go-sdk, ydb-python-sdk, ydb-cpp-sdk,
  ydb-java-sdk, Ydb.Sdk. Also use when the user wants to review Terraform HCL for YDB resources,
  or audit shell scripts using YDB CLI. Covers Go, Python, Java, C++, C#, YQL/SQL, Terraform, CLI.
version: 0.2.0
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
- **YDB overview**: `references/ydb-overview.md` — architecture context (sessions, TLI, partitioning)
- **Common rules**: `references/common-rules.md` — language-agnostic schema, YQL, config rules

Then load ONLY the subsystem-specific file(s) matching detected code:

**Go:**
- `references/go-driver.md` — connection, balancer, sessions, retry
- `references/go-query.md` — Query/Table Service, transactions
- `references/go-topics.md` — Topics (CDC, Streams)

**Python:**
- `references/python-driver.md` — connection, retry, configuration
- `references/python-query.md` — Query/Table Service, transactions
- `references/python-topics.md` — Topics

**Java:**
- `references/java-driver.md` — connection, retry (JDBC & native)
- `references/java-query.md` — Query/Table Service, transactions
- `references/java-topics.md` — Topics

**C++:**
- `references/cpp-driver.md` — connection, balancer
- `references/cpp-query.md` — Query/Table Service

**C#:**
- `references/csharp-query.md` — Query Service, ADO.NET

**Infrastructure:**
- `references/terraform.md` — Terraform resources
- `references/cli.md` — CLI scripts

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

## Rules

- NEVER fabricate rules — only report issues from reference files actually read
- Cite RULE-XX IDs from references
- Group findings by severity (Critical → Low)
- Return concise summary; full report only on request

## Test Fixtures

The `tests/` directory contains sample files with intentionally bad patterns for each language. Use them to validate review quality.
