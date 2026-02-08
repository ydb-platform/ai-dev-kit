# Go Topics (ydb-go-sdk) — CDC, Streams, Producers

## Correct Usage Cheat Sheet

```go
// Topic writer with stable producerId
hostname, _ := os.Hostname()
workerID := os.Getenv("WORKER_ID")
producerID := fmt.Sprintf("my-service-%s-%s", hostname, workerID)
writer, err := db.Topic().StartWriter(producerID, "my-topic")
defer writer.Close(ctx)

// Topic reader
reader, err := db.Topic().StartReader("my-consumer", topicoptions.ReadTopic("my-topic"))
defer reader.Close(ctx)
for {
    msg, err := reader.ReadMessage(ctx)
    // ... process message ...
    reader.Commit(ctx, msg)
}
```

---

## RULE-TP02: All keyed writes through single producer
**Severity**: High

**What to look for**: Single writer instance writing keyed messages without sharding by key hash.

**Fix**: Use pool of writers sharded by key hash (one per partition).

## RULE-TP03: Random/UUID producerId
**Severity**: Medium

**What to look for**: `uuid.New()`, random strings as `producerId` in topic writer creation.

```go
// BAD
producerID := uuid.New().String()
writer, err := db.Topic().StartWriter(producerID, "my-topic")

// GOOD
hostname, _ := os.Hostname()
workerID := os.Getenv("WORKER_ID")
producerID := fmt.Sprintf("my-service-%s-%s", hostname, workerID)
writer, err := db.Topic().StartWriter(producerID, "my-topic")
```
