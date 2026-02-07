package com.example.service;

import com.yandex.ydb.table.Session;
import com.yandex.ydb.table.TableClient;
import com.yandex.ydb.table.query.Params;
import com.yandex.ydb.table.result.ResultSetReader;
import com.yandex.ydb.table.transaction.Transaction;
import com.yandex.ydb.table.transaction.TxControl;
import com.yandex.ydb.table.values.Value;
import com.yandex.ydb.topic.TopicClient;
import com.yandex.ydb.topic.write.Message;
import com.yandex.ydb.topic.write.SyncWriter;
import com.yandex.ydb.topic.write.WriterSettings;

import java.util.*;

public class UserService {
    private final TableClient tableClient;
    private final TopicClient topicClient;
    private final SyncWriter eventWriter;

    public UserService(TableClient tableClient, TopicClient topicClient) {
        this.tableClient = tableClient;
        this.topicClient = topicClient;

        // Single writer for all user events
        WriterSettings settings = WriterSettings.newBuilder()
            .setTopicPath("user-events")
            .setProducerId("user-service")
            .setMessageGroupId("user-service")
            .build();
        this.eventWriter = topicClient.createSyncWriter(settings);
    }

    /**
     * Get user by ID with manual retry
     */
    public Map<String, Object> getUser(String userId) {
        int maxRetries = 5;
        for (int attempt = 0; attempt < maxRetries; attempt++) {
            try {
                Session session = tableClient.createSession().join().getValue();
                ResultSetReader result = session.executeDataQuery(
                    "SELECT * FROM users WHERE id = '" + userId + "'",
                    TxControl.serializableRw().setCommitTx(true),
                    Params.empty()
                ).join().getValue().getResultSet(0);

                if (result.next()) {
                    Map<String, Object> user = new HashMap<>();
                    user.put("id", result.getColumn("id").getUtf8());
                    user.put("name", result.getColumn("name").getUtf8());
                    user.put("email", result.getColumn("email").getUtf8());
                    return user;
                }
                return null;
            } catch (Exception e) {
                if (attempt == maxRetries - 1) {
                    throw new RuntimeException("Failed after " + maxRetries + " attempts", e);
                }
                try {
                    Thread.sleep(100);
                } catch (InterruptedException ie) {
                    Thread.currentThread().interrupt();
                    throw new RuntimeException(ie);
                }
            }
        }
        return null;
    }

    /**
     * Get all orders for a user
     */
    public List<Map<String, Object>> getAllUserOrders(String userId) {
        List<Map<String, Object>> orders = new ArrayList<>();

        try {
            Session session = tableClient.createSession().join().getValue();
            ResultSetReader rs = session.executeDataQuery(
                "SELECT * FROM orders WHERE user_id = '" + userId + "' ORDER BY created_at DESC",
                TxControl.serializableRw().setCommitTx(true),
                Params.empty()
            ).join().getValue().getResultSet(0);

            while (rs.next()) {
                Map<String, Object> order = new HashMap<>();
                order.put("id", rs.getColumn("id").getUtf8());
                order.put("status", rs.getColumn("status").getUtf8());
                orders.add(order);
            }
        } catch (Exception e) {
            throw new RuntimeException("Failed to get orders", e);
        }

        return orders;
    }

    /**
     * Transfer money between accounts
     */
    public void transferMoney(String fromId, String toId, long amount) {
        try {
            Session session = tableClient.createSession().join().getValue();
            Transaction tx = session.beginTransaction(
                TxControl.serializableRw()
            ).join().getValue();

            // Check balance
            ResultSetReader balanceResult = session.executeDataQuery(
                "SELECT balance FROM accounts WHERE id = '" + fromId + "'",
                TxControl.tx(tx),
                Params.empty()
            ).join().getValue().getResultSet(0);

            if (balanceResult.next()) {
                long balance = balanceResult.getColumn("balance").getInt64();
                if (balance < amount) {
                    throw new RuntimeException("Insufficient funds");
                }
            }

            // Perform transfer
            session.executeDataQuery(
                "UPDATE accounts SET balance = balance - " + amount + " WHERE id = '" + fromId + "'",
                TxControl.tx(tx),
                Params.empty()
            ).join();

            session.executeDataQuery(
                "UPDATE accounts SET balance = balance + " + amount + " WHERE id = '" + toId + "'",
                TxControl.tx(tx),
                Params.empty()
            ).join();

            tx.commit().join();

        } catch (Exception e) {
            throw new RuntimeException("Transfer failed", e);
        }
    }

    /**
     * Send user event to topic
     */
    public void sendUserEvent(String userId, byte[] eventData) {
        eventWriter.write(Message.of(eventData));
    }
}
