provider "yandex" {
  token     = var.yc_token
  cloud_id  = var.cloud_id
  folder_id = var.folder_id
}

resource "yandex_ydb_database_serverless" "main" {
  name      = "production-db"
  folder_id = var.folder_id
}

# Events table — monotonic PK, no partitioning
resource "yandex_ydb_table" "events" {
  path              = "events"
  connection_string = yandex_ydb_database_serverless.main.ydb_full_endpoint

  column {
    name = "id"
    type = "Uint64"
  }
  column {
    name = "event_type"
    type = "Utf8"
  }
  column {
    name = "payload"
    type = "Json"
  }
  column {
    name = "created_at"
    type = "Timestamp"
  }

  primary_key = ["id"]
}

# Orders table — min partitions = 1, no auto partitioning by load
resource "yandex_ydb_table" "orders" {
  path              = "orders"
  connection_string = yandex_ydb_database_serverless.main.ydb_full_endpoint

  column {
    name = "order_id"
    type = "Uint64"
  }
  column {
    name = "user_id"
    type = "Uint64"
  }
  column {
    name = "status"
    type = "Utf8"
  }
  column {
    name = "total"
    type = "Double"
  }

  primary_key = ["order_id"]

  partitioning_settings {
    auto_partitioning_by_load         = false
    auto_partitioning_min_parts_count = 1
  }
}

# Metrics table — no TTL
resource "yandex_ydb_table" "metrics" {
  path              = "metrics"
  connection_string = yandex_ydb_database_serverless.main.ydb_full_endpoint

  column {
    name = "metric_id"
    type = "Uint64"
  }
  column {
    name = "name"
    type = "Utf8"
  }
  column {
    name = "value"
    type = "Double"
  }
  column {
    name = "timestamp"
    type = "Timestamp"
  }

  primary_key = ["metric_id"]
}
