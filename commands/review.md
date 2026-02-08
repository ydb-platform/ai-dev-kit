---
description: Review YDB SDK code for anti-patterns and issues
argument-hint: [file-or-directory]
allowed-tools: Read, Grep, Glob, Edit
---

Review the following code for YDB SDK anti-patterns, performance issues, and incorrect usage.

Target: $ARGUMENTS

Use the ydb-sdk skill to load the appropriate reference files and perform a systematic review.

Detect languages from imports (ydb-go-sdk, ydb-python-sdk, tech.ydb, ydb-cpp-sdk, Ydb.Sdk, Terraform ydb resources, ydb CLI).

Report findings grouped by severity (Critical → Low) with RULE-XX citations.

If no specific files are provided, scan the current project for files importing YDB SDKs.
