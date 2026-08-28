# Running SQL with YDB CLI

Use `ydb sql` for query execution. Pair this reference with [`ydb-core`'s CLI workflow](../../ydb-core/SKILL.md#cli) and load [`query-parameters.md`](query-parameters.md) whenever values enter the query.

## Workflow

1. Verify the installed interface with `ydb version`, `ydb --help`, and `ydb sql --help`. Use `ydb sql -hh` before relying on options omitted from short help.
2. Inspect every referenced table whose schema is not already known with `ydb scheme describe <path>`. Do not guess column names, types, or primary-key order.
3. For a filter whose actual values are unknown, run a bounded discovery query such as `SELECT DISTINCT ... LIMIT 20` before composing the final predicate. Do not guess a value merely because it is plausible.
4. Keep values outside SQL text. Declare CLI parameters in the query and bind them with `--param`, `--input-file`, or an input stream.
5. Validate unfamiliar built-ins, joins, windows, casts, or multi-statement scripts with `ydb sql --explain` before execution. Iterate on validation errors without executing the query.
6. Execute only after validation succeeds and the user asked to run the query. Show the exact query and connection target before DDL or DML and obtain explicit confirmation.
7. Bound exploratory reads with `LIMIT`. Use a machine-readable `--format` only when the result will be parsed; use an export workflow rather than printing a large result into the agent context.

## Command shapes

Put global connection options before `sql`:

```bash
ydb -p <profile> sql -s 'SELECT 1;'
```

For a short parameterized query:

```bash
ydb -p <profile> sql \
  -s 'DECLARE $id AS Uint64;
      SELECT id, value FROM items WHERE id = $id LIMIT 100;' \
  --param '$id=42'
```

For a multiline query that does not consume standard input for parameters, prefer a file over fragile shell quoting:

```bash
ydb -p <profile> sql --explain -f query.sql
ydb -p <profile> sql -f query.sql --format json-unicode
```

Replace the example profile only with connection options already supplied or approved by the user. Do not silently select a default, development, or production target.

## Explain modes

- `--explain` prints the logical plan without executing the query or changing database data.
- `--explain-ast` adds the internal AST and is also non-executing.
- `--explain-analyze` executes the query; ignored result rows do not make it read-only. Treat it like normal execution, including mutation confirmation and workload impact.

## Gotchas

- **A SQL command is not inherently read-only.** `ydb sql` accepts DDL, DML, and multi-statement queries; classify the query text before execution.
- **CLI parameters still need `DECLARE`.** The CLI uses declarations to match and convert input values; see [`query-parameters.md`](query-parameters.md).
- **Unbounded streaming can fill the context.** The CLI does not impose a read-volume limit, so add a query limit for exploration instead of relying on output truncation downstream.
- **Bare `ydb` is interactive.** Keep agent workflows non-interactive unless the user explicitly asks to enter the interactive terminal.

Sources: <https://ydb.tech/docs/en/reference/ydb-cli/sql>, <https://ydb.tech/docs/en/reference/ydb-cli/parameterized-query-execution>, <https://ydb.tech/docs/en/reference/ydb-cli/commands/scheme-describe>, and the YDB CLI AI-mode implementation under <https://github.com/ydb-platform/ydb/tree/0c0d3f432c737269b0b91a2ec93cf76a8b76d00d/ydb/public/lib/ydb_cli/commands/interactive/ai>.
