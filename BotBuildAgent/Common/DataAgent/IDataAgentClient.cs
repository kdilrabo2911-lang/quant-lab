using System;
using System.Collections.Generic;
using System.Threading.Tasks;
using KadirovQuantLab.Common.Models;

namespace KadirovQuantLab.Common.DataAgent
{
    /// <summary>
    /// Interface for communicating with the DataAgent service.
    /// Replaces local file storage (DataRepository) with centralized database.
    /// </summary>
    public interface IDataAgentClient
    {
        // ============ POSITIONS ============
        /// <summary>
        /// Load open positions for a specific strategy
        /// </summary>
        Task<List<Position>> LoadPositionsAsync(string strategyName);

        /// <summary>
        /// Save open positions for a specific strategy
        /// </summary>
        Task SavePositionsAsync(string strategyName, List<Position> positions);

        // ============ PORTFOLIO STATE ============
        /// <summary>
        /// Load portfolio state (balances, P/L)
        /// </summary>
        Task<PortfolioState> LoadPortfolioStateAsync();

        /// <summary>
        /// Save portfolio state
        /// </summary>
        Task SavePortfolioStateAsync(PortfolioState portfolio);

        // ============ TRADE LOGS ============
        /// <summary>
        /// Append a completed trade to the trade log
        /// IMPORTANT: TradeLog.StrategyName must be set!
        /// </summary>
        Task AppendTradeLogAsync(TradeLog trade);

        // ============ PERFORMANCE SNAPSHOTS ============
        /// <summary>
        /// Append a performance snapshot (periodic portfolio metrics)
        /// </summary>
        Task AppendPerformanceSnapshotAsync(PerformanceSnapshot snapshot);

        // ============ HISTORICAL DATA ============
        /// <summary>
        /// Load historical OHLC candles for a coin
        /// </summary>
        Task<List<OhlcCandle>> LoadHistoricalCandlesAsync(string coin);

        /// <summary>
        /// Append a new ticker update to historical data
        /// NOTE: This should rarely be used - DataAgent handles data ingestion
        /// </summary>
        Task AppendTickerToHistoryAsync(string coin, TickerUpdateEvent ticker, double btcPrice);

        // ============ STRATEGY PARAMETERS ============
        /// <summary>
        /// Load optimal parameters for a strategy
        /// Returns: Dictionary[coin -> parameters]
        /// </summary>
        Task<Dictionary<string, T>> LoadStrategyParametersAsync<T>(string strategyName) where T : class;
    }
}
