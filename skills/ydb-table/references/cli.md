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

Use one `--param` per simple value. The part after `=` is JSON whose conversion is driven by `DECLARE`; see [`query-parameters.md`](query-parameters.md) for YDB type encodings. For example, timestamps and decimals are JSON strings:

```bash
ydb -p <profile> sql -f query.sql \
  --param '$id=42' \
  --param '$at="2026-08-28T12:34:56.123456Z"' \
  --param '$price="123.450000000"'
```

For a multiline query that does not consume standard input for parameters, prefer a file over fragile shell quoting:

```bash
ydb -p <profile> sql --explain -f query.sql
ydb -p <profile> sql -f query.sql --format json-unicode
```

Replace the example profile only with connection options already supplied or approved by the user. Do not silently select a default, development, or production target.

## Parameter sources and files

Choose the least fragile supported source:

- Use repeated `--param` for a few scalar values.
- Use one `--input-file <path> --input-format json` for many or composite values. Object keys are parameter names without `$`; `List`, `Struct`, `Tuple`, optional, temporal, decimal, binary, and document values follow [`query-parameters.md`](query-parameters.md).
- Use `csv` or `tsv` for row-shaped scalar data. The header supplies parameter names without `$`; if the file has no header, set `--input-columns 'name1,name2'`. Type conversion still comes from `DECLARE`.
- Use `raw` only for one `String` or `Utf8` value and name it with `--input-param-name`.

Run `ydb sql -hh` before relying on these options. This is a local, read-only discovery command, not query execution; include it as a prerequisite when the user asks for commands but says not to execute the query. In reusable file-based commands, always spell out `--input-format`, including `json`, rather than depending on the default.

Do not use the hidden legacy `--param-file`; use `--input-file`. Only one input file is accepted. Values may be combined with `--param` only when a parameter name appears in exactly one source. If parameters come from standard input, keep the query in `-s` or `-f`; the query and parameters cannot both consume stdin.

For a JSON file containing one parameter set:

```json
{
  "id": 42,
  "at": "2026-08-28T12:34:56.123456Z",
  "price": "123.450000000",
  "tags": ["blue", "green"],
  "metadata": "{\"source\":\"cli\"}",
  "deleted_at": null
}
```

```bash
ydb -p <profile> sql -f query.sql \
  --input-file params.json \
  --input-format json
```

For one CSV or TSV row, the default `no-framing` executes once. For multiple rows, use newline framing; the default `iterative` batch mode executes the query once per row, each in its own transaction:

```bash
ydb -p <profile> sql -f query.sql \
  --input-file params.csv \
  --input-format csv \
  --input-framing newline-delimited
```

Use the same shape with `--input-format tsv` for TSV. CSV/TSV cells support scalar, decimal, optional, and PostgreSQL values; use JSON instead of embedding lists, dicts, or nested structs in a cell. An empty CSV/TSV field maps to `NULL` only when the declared type is optional.

For a single batched execution, declare one `List<Struct<...>>` parameter, set its name without `$`, and choose `full` or `adaptive` batching:

```bash
ydb -p <profile> sql -f upsert.sql \
  --input-file rows.csv \
  --input-format csv \
  --input-framing newline-delimited \
  --input-batch adaptive \
  --input-param-name rows \
  --input-batch-max-rows 1000
```

`full` sends all rows once at EOF. `adaptive` sends a list whenever its row or delay threshold is reached. Both require the named query parameter to be a `List<...>`; preserve the normal DML confirmation gate.

### Arrow boundary

`ydb sql` does not accept Arrow IPC/Feather as a parameter input format. Its current parameter inputs are `json`, `csv`, `tsv`, and `raw`; do not invent `--input-format arrow`. Ask the user to convert Arrow data to a supported parameter format. If the real task is bulk ingestion rather than query parameter binding, treat it as a separate mutating workflow and check the installed import command; current CLI file import supports CSV, TSV, JSON, and Parquet, not Arrow IPC.

## Explain modes

- `--explain` prints the logical plan without executing the query or changing database data.
- `--explain-ast` adds the internal AST and is also non-executing.
- `--explain-analyze` executes the query; ignored result rows do not make it read-only. Treat it like normal execution, including mutation confirmation and workload impact.

## Gotchas

- **A SQL command is not inherently read-only.** `ydb sql` accepts DDL, DML, and multi-statement queries; classify the query text before execution.
- **CLI parameters still need `DECLARE`.** The CLI uses declarations to match and convert input values; see [`query-parameters.md`](query-parameters.md).
- **Input and output formats are different option sets.** `--format parquet` controls query results; it does not make Parquet or Arrow a SQL parameter input.
- **Unbounded streaming can fill the context.** The CLI does not impose a read-volume limit, so add a query limit for exploration instead of relying on output truncation downstream.
- **Bare `ydb` is interactive.** Keep agent workflows non-interactive unless the user explicitly asks to enter the interactive terminal.

Sources: <https://ydb.tech/docs/en/reference/ydb-cli/sql>, <https://ydb.tech/docs/en/reference/ydb-cli/parameterized-query-execution>, <https://ydb.tech/docs/en/reference/ydb-cli/commands/scheme-describe>, and the YDB CLI AI-mode implementation under <https://github.com/ydb-platform/ydb/tree/0c0d3f432c737269b0b91a2ec93cf76a8b76d00d/ydb/public/lib/ydb_cli/commands/interactive/ai>.
