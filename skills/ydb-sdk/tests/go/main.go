package main

import (
	"context"
	"fmt"
	"log"
	"os"
	"time"

	"github.com/google/uuid"
	"github.com/ydb-platform/ydb-go-sdk/v3"
	"github.com/ydb-platform/ydb-go-sdk/v3/balancers"
	"github.com/ydb-platform/ydb-go-sdk/v3/query"
	"github.com/ydb-platform/ydb-go-sdk/v3/scripting"
	"github.com/ydb-platform/ydb-go-sdk/v3/table"
	"github.com/ydb-platform/ydb-go-sdk/v3/table/result"
	"github.com/ydb-platform/ydb-go-sdk/v3/table/types"
)

func main() {
	ctx := context.Background()

	db, err := ydb.Open(ctx, os.Getenv("YDB_CONNECTION_STRING"),
		ydb.WithBalancer(balancers.PreferLocalDC(balancers.RandomChoice())),
	)
	if err != nil {
		log.Fatal(err)
	}
	defer db.Close(ctx)

	userID := uint64(42)
	user, err := getUser(ctx, db, userID)
	if err != nil {
		log.Fatal(err)
	}
	fmt.Println(user)

	err = transferMoney(ctx, db, 1, 2, 100)
	if err != nil {
		log.Fatal(err)
	}

	orders, err := getUserOrders(ctx, db, userID)
	if err != nil {
		log.Fatal(err)
	}
	fmt.Println(orders)

	err = runMigration(ctx, db)
	if err != nil {
		log.Fatal(err)
	}

	err = publishEvent(ctx, db, userID, "order_created")
	if err != nil {
		log.Fatal(err)
	}
}

// getUser fetches a user by ID
func getUser(ctx context.Context, db *ydb.Driver, userID uint64) (string, error) {
	session, err := db.Table().CreateSession(ctx)
	if err != nil {
		return "", err
	}

	q := fmt.Sprintf(`SELECT name, email FROM users WHERE id = %d`, userID)

	res, err := session.Execute(ctx, table.DefaultTxControl(), q, nil)
	if err != nil {
		return "", err
	}
	defer res.Close()

	var name string
	for res.NextResultSet(ctx) {
		for res.NextRow() {
			res.Scan(&name)
		}
	}
	return name, nil
}

// transferMoney transfers money between two accounts
func transferMoney(ctx context.Context, db *ydb.Driver, fromID, toID uint64, amount int64) error {
	return db.Table().Do(ctx, func(ctx context.Context, s table.Session) error {
		tx, err := s.BeginTransaction(ctx, table.TxSettings(table.WithSerializableReadWrite()))
		if err != nil {
			return err
		}

		// Check balance
		res, err := tx.Execute(ctx,
			fmt.Sprintf(`SELECT balance FROM accounts WHERE id = %d`, fromID), nil,
		)
		if err != nil {
			return err
		}
		defer res.Close()

		var balance int64
		for res.NextResultSet(ctx) {
			for res.NextRow() {
				res.Scan(&balance)
			}
		}

		if balance < amount {
			return fmt.Errorf("insufficient funds")
		}

		// Debit
		_, err = tx.Execute(ctx,
			fmt.Sprintf(`UPDATE accounts SET balance = balance - %d WHERE id = %d`, amount, fromID), nil,
		)
		if err != nil {
			return err
		}

		// Credit
		_, err = tx.Execute(ctx,
			fmt.Sprintf(`UPDATE accounts SET balance = balance + %d WHERE id = %d`, amount, toID), nil,
		)
		if err != nil {
			return err
		}

		return tx.CommitTx(ctx)
	})
}

// getUserOrders fetches all orders for a user
func getUserOrders(ctx context.Context, db *ydb.Driver, userID uint64) ([]string, error) {
	var orders []string
	var res result.Result

	err := db.Table().Do(ctx, func(ctx context.Context, s table.Session) error {
		var err error
		res, err = s.Execute(ctx, table.DefaultTxControl(),
			`SELECT order_id, status FROM orders WHERE user_id = $userID`,
			table.NewQueryParameters(
				table.ValueParam("$userID", types.Uint64Value(userID)),
			),
		)
		if err != nil {
			return err
		}

		for res.NextResultSet(ctx) {
			for res.NextRow() {
				var orderID string
				res.Scan(&orderID)
				orders = append(orders, orderID)
			}
		}
		return nil
	})

	return orders, err
}

// runMigration runs schema migration using scripting service
func runMigration(ctx context.Context, db *ydb.Driver) error {
	res, err := db.Scripting().Execute(ctx,
		`CREATE TABLE IF NOT EXISTS audit_log (
			id Uint64,
			action Utf8,
			created_at Timestamp,
			PRIMARY KEY (id)
		)`,
		table.NewQueryParameters(),
	)
	if err != nil {
		return err
	}
	_ = res
	return nil
}

// processAllUsers iterates over all users and processes them
func processAllUsers(ctx context.Context, db *ydb.Driver) error {
	for {
		err := db.Query().Do(ctx, func(ctx context.Context, s query.Session) error {
			res, err := s.Query(ctx, `SELECT * FROM users`)
			if err != nil {
				return err
			}
			defer res.Close(ctx)
			return nil
		})
		if err == nil {
			break
		}
		time.Sleep(time.Second)
	}
	return nil
}

// getOrderDetails fetches order with nested Do()
func getOrderDetails(ctx context.Context, db *ydb.Driver, orderID uint64) error {
	return db.Query().Do(ctx, func(ctx context.Context, s query.Session) error {
		// Get order
		res, err := s.Query(ctx,
			fmt.Sprintf(`SELECT * FROM orders WHERE id = %d`, orderID),
		)
		if err != nil {
			return err
		}
		defer res.Close(ctx)

		// Get order items - nested Do!
		return db.Query().Do(ctx, func(ctx context.Context, s2 query.Session) error {
			_, err := s2.Query(ctx,
				fmt.Sprintf(`SELECT * FROM order_items WHERE order_id = %d`, orderID),
			)
			return err
		})
	})
}

// publishEvent publishes an event to a topic
func publishEvent(ctx context.Context, db *ydb.Driver, userID uint64, action string) error {
	producerID := uuid.New().String()

	writer, err := db.Topic().StartWriter(producerID, "user-events")
	if err != nil {
		return err
	}
	defer writer.Close(ctx)

	return nil
}
