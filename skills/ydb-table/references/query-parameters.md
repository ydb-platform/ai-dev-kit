# Query parameters and `DECLARE`

Query parameters keep caller values separate from YQL text. Pass every value through the typed parameter interface of the execution API; a `DECLARE` statement describes a parameter type but does not provide its value.

## Typed SDK requests in Syntax V1 on YDB 25.1.2.7 and newer

Starting with YDB 25.1.2.7, Syntax V1 can take parameter types from the typed values sent with the same request when implicit parameter type inference is enabled. It is enabled by default in YDB 25.1.2.7. The type comes from the request's `TypedValue`, not from SQL context such as the type of a column compared with the parameter. A query that receives a typed `$id` can therefore start directly with the statement that uses it:

```yql
SELECT id, value
FROM items
WHERE id = $id;
```

Omitting `DECLARE` does not permit interpolation: `$id` must still be bound separately. The shorter form is valid for SDK execution when the target server is known to be YDB 25.1.2.7 or newer, uses Syntax V1, has implicit parameter type inference available and enabled, and the request carries typed parameter values; keep the explicit form when its contract or compatibility value matters.

Sources: <https://ydb.tech/docs/en/changelog-server#25-1-2-7-rc>, <https://github.com/ydb-platform/ydb/blob/e0e29e98f0614e18e20f2861d69a6ee12590ad52/ydb/core/protos/feature_flags.proto#L114-L120>, <https://github.com/ydb-platform/ydb/blob/e0e29e98f0614e18e20f2861d69a6ee12590ad52/ydb/core/kqp/session_actor/kqp_query_state.h#L73-L79>.

## Explicit declarations and compatibility

Keep `DECLARE` for YQL v0, servers older than YDB 25.1.2.7, and operations that compile a query without parameter values. Also keep it when parameter types should be an explicit caller contract or when a compound shape is clearer next to the query. If the target syntax, server version, or execution path is unknown, keep the declarations or verify all three before relying on request types.

In Syntax V1, use normal unquoted YQL type syntax:

```yql
DECLARE $id AS Uint64;
DECLARE $items AS List<Struct<id: Uint64, value: Utf8>>;

SELECT id, value
FROM AS_TABLE($items)
WHERE id = $id;
```

Quoting the whole type is legacy YQL v0 syntax and fails under Syntax V1. In YQL v0, simple names such as `Uint64` may be bare, while compound types use the legacy quoted form. An explicit declaration keeps the expected caller contract next to the query; `DECLARE` itself is not an anti-pattern.

Sources: <https://ydb.tech/docs/en/yql/reference/syntax/declare>, <https://github.com/ydb-platform/ydb/blob/e0e29e98f0614e18e20f2861d69a6ee12590ad52/yql/essentials/sql/v0/SQL.g#L164-L168>.

## YDB CLI parameter input

For `ydb sql --param`, `--input-file`, and parameter values read from `stdin`, declare every parameter the CLI should accept even when the server is YDB 25.1.2.7 or newer. The CLI uses the declarations to match and convert its JSON, CSV, TSV, or raw input. An undeclared `--param` fails with `Query does not contain parameter`; undeclared keys in JSON input are ignored.

Source: <https://ydb.tech/docs/en/reference/ydb-cli/parameterized-query-execution>.
