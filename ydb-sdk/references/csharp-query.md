# C# Query (Ydb.Sdk) — Query/Table Service

## SDK Detection
- Using: `using Ydb.Sdk`, `using Ydb.Sdk.Value`
- NuGet: `Ydb.Sdk`

## Correct Usage Cheat Sheet

```csharp
// ADO.NET (recommended)
await using var connection = new YdbConnection("Host=localhost;Port=2136;Database=/local");
await connection.OpenAsync();

await using var command = connection.CreateCommand();
command.CommandText = "SELECT * FROM users WHERE id = $id";
command.Parameters.Add(new YdbParameter("$id", YdbValue.MakeUint64(userId)));
await using var reader = await command.ExecuteReaderAsync();
```

---

## RULE-Q03: SQL injection via string interpolation
**Severity**: Critical

**What to look for**: `$"SELECT ... {variable}"`, string concatenation in query text.

```csharp
// BAD
var query = $"SELECT * FROM users WHERE login = '{userLogin}'";
await client.Exec(query);

// GOOD
await client.Exec(
    "SELECT * FROM users WHERE login = $login",
    new Dictionary<string, YdbValue> { { "$login", YdbValue.MakeUtf8(userLogin) } }
);
```

## RULE-Q10: Non-parametrized queries
**Severity**: High

**What to look for**: `$"..."` string interpolation in query text, values inlined.

```csharp
// BAD
var query = $"SELECT * FROM users WHERE id = {userId} AND status = '{status}'";

// GOOD
await client.Exec(
    "SELECT * FROM users WHERE id = $userId AND status = $status",
    new Dictionary<string, YdbValue> {
        { "$userId", YdbValue.MakeUint64(userId) },
        { "$status", YdbValue.MakeUtf8(status) }
    }
);
```

## RULE-Q12: Multiple sequential queries instead of batch
**Severity**: Medium

**What to look for**: Multiple separate `Exec()` calls that could be one multi-statement query.

```csharp
// BAD: three round-trips
await client.Exec("SELECT name FROM users WHERE user_id = $userId", ...);
await client.Exec("SELECT title FROM products WHERE product_id = $productId", ...);
await client.Exec("INSERT INTO orders ...", ...);

// GOOD: one round-trip
await client.Exec(@"
    SELECT name FROM users WHERE user_id = $userId;
    SELECT title FROM products WHERE product_id = $productId;
    INSERT INTO orders ... RETURNING *;
", new Dictionary<string, YdbValue> { ... });
```
