# Java Topics (ydb-java-sdk) — CDC, Streams, Producers

## Correct Usage Cheat Sheet

```java
// Topic writer with stable producerId and sharding
Map<String, SyncWriter> writers = new HashMap<>();
for (int i = 0; i < partitionsCount; i++) {
    String producerId = "user-service-part-" + i;
    writers.put(producerId, topicClient.createSyncWriter(
        WriterSettings.newBuilder()
            .setTopicPath("user-events")
            .setProducerId(producerId)
            .build()));
}

// Select writer by key hash
String producerId = "user-service-part-" + (Math.abs(userId.hashCode()) % partitionsCount);
writers.get(producerId).write(Message.of(eventData));
```

---

## RULE-TP02: All keyed writes through single producer
**Severity**: High

**What to look for**: Single `SyncWriter` handling all keyed messages without sharding.

```java
// BAD: single producer for all keys
WriterSettings settings = WriterSettings.newBuilder()
    .setTopicPath("user-events")
    .setProducerId("user-service")
    .build();
SyncWriter writer = topicClient.createSyncWriter(settings);
writer.write(Message.of(eventData)); // all events through one writer

// GOOD: sharded by key hash
Map<String, SyncWriter> writers = new HashMap<>();
for (int i = 0; i < partitionsCount; i++) {
    String producerId = "user-service-part-" + i;
    writers.put(producerId, topicClient.createSyncWriter(
        WriterSettings.newBuilder()
            .setTopicPath("user-events")
            .setProducerId(producerId)
            .build()));
}
String producerId = "user-service-part-" + (Math.abs(userId.hashCode()) % partitionsCount);
writers.get(producerId).write(Message.of(eventData));
```
