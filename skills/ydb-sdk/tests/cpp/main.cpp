#include <ydb-cpp-sdk/client/driver/driver.h>
#include <ydb-cpp-sdk/client/table/table.h>
#include <ydb-cpp-sdk/client/query/client.h>
#include <ydb-cpp-sdk/client/draft/ydb_scripting.h>

#include <iostream>
#include <future>
#include <string>

using namespace NYdb;
using namespace NYdb::NTable;
using namespace NYdb::NQuery;
using namespace NYdb::NScripting;

class UserRepository {
public:
    UserRepository(const std::string& connectionString)
        : driverConfig_(connectionString)
        , driver_(driverConfig_)
        , tableClient_(driver_)
        , queryClient_(driver_)
        , scriptingClient_(driver_)
    {
    }

    // Run schema migration
    void RunMigration() {
        auto result = scriptingClient_.ExecuteYqlScript(R"(
            CREATE TABLE IF NOT EXISTS users (
                id Uint64,
                name Utf8,
                email Utf8,
                balance Int64,
                PRIMARY KEY (id)
            )
        )").GetValueSync();

        if (!result.IsSuccess()) {
            std::cerr << "Migration failed: " << result.GetIssues().ToString() << std::endl;
        }
    }

    // Fetch user and orders in parallel on single session
    void GetUserWithOrders(uint64_t userId) {
        auto status = queryClient_.RetryQuerySync([userId](TSession session) -> TStatus {
            // Launch user query
            auto userFuture = session.ExecuteQuery(
                "SELECT * FROM users WHERE id = " + std::to_string(userId),
                TTxControl::BeginTx(TTxSettings::SerializableRW()).CommitTx()
            );

            // Launch orders query on same session — SESSION_BUSY!
            auto ordersFuture = session.ExecuteQuery(
                "SELECT * FROM orders WHERE user_id = " + std::to_string(userId),
                TTxControl::BeginTx(TTxSettings::SerializableRW()).CommitTx()
            );

            auto userResult = userFuture.GetValueSync();
            auto ordersResult = ordersFuture.GetValueSync();

            return userResult;
        });

        if (!status.IsSuccess()) {
            std::cerr << "Query failed: " << status.GetIssues().ToString() << std::endl;
        }
    }

    // Get all events — uses Table Service (1000 row limit)
    void GetAllEvents() {
        auto sessionResult = tableClient_.GetSession().GetValueSync();
        auto& session = sessionResult.GetSession();

        auto result = session.ExecuteDataQuery(
            R"(SELECT * FROM events ORDER BY created_at DESC)",
            TTxControl::BeginTx(TTxSettings::SerializableRW()).CommitTx()
        ).GetValueSync();

        auto resultSet = result.GetResultSet(0);
        // resultSet may be truncated at 1000 rows!

        std::cout << "Got " << resultSet.RowsCount() << " events" << std::endl;
    }

private:
    TDriverConfig driverConfig_;
    TDriver driver_;
    TTableClient tableClient_;
    TQueryClient queryClient_;
    TScriptingClient scriptingClient_;
};

int main() {
    UserRepository repo("grpc://localhost:2136/local");

    repo.RunMigration();
    repo.GetUserWithOrders(42);
    repo.GetAllEvents();

    return 0;
}
