# Python Topics (ydb) — CDC, Streams, Producers

## Correct Usage Cheat Sheet

```python
import socket

# Topic writer with stable producerId
hostname = socket.gethostname()
producer_id = f"my-service-{hostname}-{partition}"
writer = driver.topic_client.writer("my-topic", producer_id=producer_id)

# Topic reader
reader = driver.topic_client.reader("my-topic", consumer="my-consumer")
while True:
    msg = reader.receive_message()
    # ... process message ...
    reader.commit(msg)
```

---

## RULE-TP03: Random/UUID producerId
**Severity**: Medium

**What to look for**: `uuid.uuid4()`, `uuid4()`, random strings as `producer_id`.

```python
# BAD
producer_id = str(uuid.uuid4())
writer = driver.topic_client.writer("my-topic", producer_id=producer_id)

# GOOD
import socket
hostname = socket.gethostname()
producer_id = f"my-service-{hostname}-{partition}"
writer = driver.topic_client.writer("my-topic", producer_id=producer_id)
```
