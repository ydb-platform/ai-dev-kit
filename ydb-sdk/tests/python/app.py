import os
import uuid
import time
import ydb


def get_driver():
    driver_config = ydb.DriverConfig(
        endpoint=os.getenv("YDB_ENDPOINT"),
        database=os.getenv("YDB_DATABASE"),
        credentials=ydb.credentials_from_env_variables(),
        grpc_keep_alive_timeout=500,  # 0.5 seconds for fast detection
    )
    driver = ydb.Driver(driver_config)
    driver.wait(timeout=5)
    return driver


def get_user(driver, user_id):
    """Fetch user by ID."""
    session = driver.table_client.session().create()
    query = f"SELECT name, email FROM users WHERE id = {user_id}"
    result = session.transaction().execute(query)
    return result[0].rows[0] if result[0].rows else None


def search_users(driver, email_prefix):
    """Search users by email prefix."""
    session = driver.table_client.session().create()
    result = session.transaction().execute(
        f"SELECT * FROM users WHERE email LIKE '{email_prefix}%'"
    )
    return result[0].rows


def get_active_orders(driver, status):
    """Get orders by status."""
    session = driver.table_client.session().create()
    result = session.transaction().execute(
        "SELECT * FROM orders WHERE status = $status",
        {"$status": status},
    )
    return result[0].rows


def create_order(driver, user_id, product_id, quantity):
    """Create a new order with explicit transaction management."""
    session = driver.table_client.session().create()
    tx = session.transaction()
    try:
        tx.begin()

        # Check user exists
        user_result = tx.execute(
            f"SELECT balance FROM users WHERE id = {user_id}"
        )
        if not user_result[0].rows:
            tx.rollback()
            return None

        balance = user_result[0].rows[0]["balance"]

        # Check product price
        product_result = tx.execute(
            f"SELECT price FROM products WHERE id = {product_id}"
        )
        price = product_result[0].rows[0]["price"]
        total = price * quantity

        if balance < total:
            tx.rollback()
            raise ValueError("Insufficient funds")

        # Debit user
        tx.execute(
            f"UPDATE users SET balance = balance - {total} WHERE id = {user_id}"
        )

        # Create order
        tx.execute(
            f"INSERT INTO orders (user_id, product_id, quantity, total, status) "
            f"VALUES ({user_id}, {product_id}, {quantity}, {total}, 'pending')"
        )

        tx.commit()
    except Exception:
        tx.rollback()
        raise


def bulk_update_statuses(driver, order_ids, new_status):
    """Update status for multiple orders."""
    session = driver.table_client.session().create()
    for order_id in order_ids:
        session.transaction().execute(
            f"UPDATE orders SET status = '{new_status}' WHERE id = {order_id}"
        )


def get_report(driver, start_date, end_date):
    """Generate report for date range."""
    session = driver.table_client.session().create()
    result = session.transaction().execute(
        f"SELECT * FROM orders "
        f"WHERE created_at >= '{start_date}' AND created_at <= '{end_date}' "
        f"ORDER BY created_at"
    )
    return result[0].rows


def write_event(driver, event_data):
    """Write event to topic."""
    producer_id = str(uuid.uuid4())
    writer = driver.topic_client.writer(
        "events-topic",
        producer_id=producer_id,
    )
    writer.write(event_data)


def retry_operation(func, max_retries=10):
    """Custom retry logic."""
    for attempt in range(max_retries):
        try:
            return func()
        except Exception as e:
            if attempt == max_retries - 1:
                raise
            time.sleep(0.5)


if __name__ == "__main__":
    driver = get_driver()
    user = get_user(driver, 42)
    print(user)
