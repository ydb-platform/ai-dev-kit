using System;
using System.Collections.Generic;
using System.Threading.Tasks;
using Ydb.Sdk;
using Ydb.Sdk.Value;

namespace MyApp.Data
{
    public class UserRepository
    {
        private readonly QueryClient _client;

        public UserRepository(QueryClient client)
        {
            _client = client;
        }

        /// <summary>
        /// Get user by login — vulnerable to SQL injection
        /// </summary>
        public async Task<Dictionary<string, string>> GetUserByLogin(string login)
        {
            var query = $"SELECT id, name, email FROM users WHERE login = '{login}'";
            var result = await _client.Exec(query);
            return ParseUser(result);
        }

        /// <summary>
        /// Search users by name pattern
        /// </summary>
        public async Task<List<Dictionary<string, string>>> SearchUsers(string namePattern)
        {
            var query = $"SELECT * FROM users WHERE name LIKE '%{namePattern}%' ORDER BY name";
            var result = await _client.Exec(query);
            return ParseUsers(result);
        }

        /// <summary>
        /// Create order with multiple round-trips
        /// </summary>
        public async Task CreateOrder(ulong userId, ulong productId, int quantity)
        {
            // Round-trip 1: check user
            var userResult = await _client.Exec(
                $"SELECT balance FROM users WHERE id = {userId}"
            );

            var balance = GetBalance(userResult);

            // Round-trip 2: check product
            var productResult = await _client.Exec(
                $"SELECT price, stock FROM products WHERE id = {productId}"
            );

            var price = GetPrice(productResult);
            var total = price * quantity;

            if (balance < total)
                throw new InvalidOperationException("Insufficient funds");

            // Round-trip 3: debit user
            await _client.Exec(
                $"UPDATE users SET balance = balance - {total} WHERE id = {userId}"
            );

            // Round-trip 4: create order
            await _client.Exec(
                $"INSERT INTO orders (user_id, product_id, quantity, total, status) "
                + $"VALUES ({userId}, {productId}, {quantity}, {total}, 'pending')"
            );

            // Round-trip 5: update stock
            await _client.Exec(
                $"UPDATE products SET stock = stock - {quantity} WHERE id = {productId}"
            );
        }

        /// <summary>
        /// Get dashboard data — multiple sequential queries
        /// </summary>
        public async Task<DashboardData> GetDashboard(ulong userId)
        {
            var userData = await _client.Exec(
                $"SELECT * FROM users WHERE id = {userId}"
            );

            var ordersData = await _client.Exec(
                $"SELECT * FROM orders WHERE user_id = {userId} ORDER BY created_at DESC LIMIT 10"
            );

            var notificationsData = await _client.Exec(
                $"SELECT * FROM notifications WHERE user_id = {userId} AND read = false"
            );

            return new DashboardData(userData, ordersData, notificationsData);
        }

        private Dictionary<string, string> ParseUser(object result) => new();
        private List<Dictionary<string, string>> ParseUsers(object result) => new();
        private decimal GetBalance(object result) => 0;
        private decimal GetPrice(object result) => 0;
    }

    public record DashboardData(object User, object Orders, object Notifications);
}
