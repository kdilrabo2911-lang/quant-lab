using System;
using System.Collections.Generic;
using System.Net.Http;
using System.Net.Http.Json;
using System.Threading.Tasks;
using KadirovQuantLab.Common.Models;

namespace KadirovQuantLab.Common.DataAgent
{
    /// <summary>
    /// REST API client for communicating with DataAgent service.
    ///
    /// IMPLEMENTATION STATUS: STUB - DataAgent service doesn't exist yet
    /// TODO: Implement real HTTP calls once DataAgent is deployed
    ///
    /// For now, returns empty/default data. Strategies should handle DataAgent unavailability.
    /// </summary>
    public class DataAgentClient : IDataAgentClient
    {
        private readonly HttpClient _httpClient;
        private readonly string _dataAgentUrl;

        public DataAgentClient(string dataAgentUrl = "http://localhost:8000")
        {
            _dataAgentUrl = dataAgentUrl;
            _httpClient = new HttpClient { BaseAddress = new Uri(dataAgentUrl) };
        }

        public async Task<List<Position>> LoadPositionsAsync(string strategyName)
        {
            try
            {
                // TODO: Implement real API call
                var response = await _httpClient.GetAsync($"/api/positions?strategy={strategyName}");
                response.EnsureSuccessStatusCode();
                return await response.Content.ReadFromJsonAsync<List<Position>>() ?? new List<Position>();
            }
            catch (HttpRequestException)
            {
                Console.WriteLine($"[DATA AGENT] Service unavailable - returning empty positions");
                return new List<Position>();
            }
        }

        public async Task SavePositionsAsync(string strategyName, List<Position> positions)
        {
            try
            {
                // TODO: Implement real API call
                var response = await _httpClient.PostAsJsonAsync($"/api/positions?strategy={strategyName}", positions);
                response.EnsureSuccessStatusCode();
            }
            catch (HttpRequestException ex)
            {
                Console.WriteLine($"[DATA AGENT] Failed to save positions: {ex.Message}");
            }
        }

        public async Task<PortfolioState> LoadPortfolioStateAsync()
        {
            try
            {
                var response = await _httpClient.GetAsync("/api/portfolio/state");
                response.EnsureSuccessStatusCode();
                return await response.Content.ReadFromJsonAsync<PortfolioState>() ?? new PortfolioState();
            }
            catch (HttpRequestException)
            {
                Console.WriteLine($"[DATA AGENT] Service unavailable - returning empty portfolio state");
                return new PortfolioState();
            }
        }

        public async Task SavePortfolioStateAsync(PortfolioState portfolio)
        {
            try
            {
                var response = await _httpClient.PostAsJsonAsync("/api/portfolio/state", portfolio);
                response.EnsureSuccessStatusCode();
            }
            catch (HttpRequestException ex)
            {
                Console.WriteLine($"[DATA AGENT] Failed to save portfolio: {ex.Message}");
            }
        }

        public async Task AppendTradeLogAsync(TradeLog trade)
        {
            if (string.IsNullOrEmpty(trade.StrategyName))
            {
                throw new ArgumentException("TradeLog.StrategyName must be set!");
            }

            try
            {
                var response = await _httpClient.PostAsJsonAsync("/api/trades/log", trade);
                response.EnsureSuccessStatusCode();
            }
            catch (HttpRequestException ex)
            {
                Console.WriteLine($"[DATA AGENT] Failed to log trade: {ex.Message}");
            }
        }

        public async Task AppendPerformanceSnapshotAsync(PerformanceSnapshot snapshot)
        {
            try
            {
                var response = await _httpClient.PostAsJsonAsync("/api/performance/snapshot", snapshot);
                response.EnsureSuccessStatusCode();
            }
            catch (HttpRequestException ex)
            {
                Console.WriteLine($"[DATA AGENT] Failed to log performance: {ex.Message}");
            }
        }

        public async Task<List<OhlcCandle>> LoadHistoricalCandlesAsync(string coin)
        {
            try
            {
                var response = await _httpClient.GetAsync($"/api/historical/{coin}");
                response.EnsureSuccessStatusCode();
                return await response.Content.ReadFromJsonAsync<List<OhlcCandle>>() ?? new List<OhlcCandle>();
            }
            catch (HttpRequestException)
            {
                Console.WriteLine($"[DATA AGENT] Service unavailable - returning empty historical data for {coin}");
                return new List<OhlcCandle>();
            }
        }

        public async Task AppendTickerToHistoryAsync(string coin, TickerUpdateEvent ticker, double btcPrice)
        {
            try
            {
                var payload = new { coin, ticker, btcPrice };
                var response = await _httpClient.PostAsJsonAsync("/api/historical/append", payload);
                response.EnsureSuccessStatusCode();
            }
            catch (HttpRequestException ex)
            {
                Console.WriteLine($"[DATA AGENT] Failed to append ticker: {ex.Message}");
            }
        }

        public async Task<Dictionary<string, T>> LoadStrategyParametersAsync<T>(string strategyName) where T : class
        {
            try
            {
                var response = await _httpClient.GetAsync($"/api/strategies/{strategyName}/parameters");
                response.EnsureSuccessStatusCode();
                return await response.Content.ReadFromJsonAsync<Dictionary<string, T>>() ?? new Dictionary<string, T>();
            }
            catch (HttpRequestException)
            {
                Console.WriteLine($"[DATA AGENT] Service unavailable - returning empty parameters for {strategyName}");
                return new Dictionary<string, T>();
            }
        }
    }
}
