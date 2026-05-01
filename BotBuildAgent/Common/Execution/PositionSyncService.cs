using System;
using System.Collections.Generic;
using System.Linq;
using System.Threading.Tasks;
using KadirovQuantLab.Common.DataAgent;
using KadirovQuantLab.Common.Exchange;
using KadirovQuantLab.Common.Models;
using KadirovQuantLab.Common.Portfolio;

namespace KadirovQuantLab.Common.Execution
{
    /// <summary>
    /// UNIFIED position synchronization service.
    /// Detects manual trades and syncs positions with exchange.
    /// </summary>
    public class PositionSyncService : IPositionSyncService
    {
        private readonly IKrakenClient _krakenClient;
        private readonly IDataAgentClient _dataAgent;
        private readonly IPortfolioTracker _portfolio;
        private readonly bool _dryRun;

        private const double MANUAL_BUY_FEE = 0.0025;  // 0.25%

        public PositionSyncService(
            IKrakenClient krakenClient,
            IDataAgentClient dataAgent,
            IPortfolioTracker portfolio,
            bool dryRun = false)
        {
            _krakenClient = krakenClient;
            _dataAgent = dataAgent;
            _portfolio = portfolio;
            _dryRun = dryRun;
        }

        public async Task<List<Position>> SyncPositionsWithExchangeAsync(List<Position> currentPositions)
        {
            // Always sync positions, even in dry run mode (for testing manual trade detection)
            try
            {
                var coinBalances = await _krakenClient.FetchAllCoinBalancesAsync();
                var positions = new List<Position>(currentPositions);

                // Detect manual sells
                positions = await DetectManualSellsAsync(positions, coinBalances);

                // Detect manual buys
                positions = await DetectManualBuysAsync(positions, coinBalances);

                // TODO: Determine strategy name for synced positions
                // For now, save all positions (mixed strategies)
                await _dataAgent.SavePositionsAsync("ALL", positions);

                // Update portfolio realized P/L
                var portfolioState = _portfolio.GetState();
                portfolioState.RealizedProfitLoss = ((portfolioState.TotalBalance - portfolioState.InitialBalance) / portfolioState.InitialBalance) * 100.0;
                await _dataAgent.SavePortfolioStateAsync(portfolioState);

                return positions;
            }
            catch (Exception ex)
            {
                Console.WriteLine($"[POSITION SYNC ERROR] {ex.Message}");
                return currentPositions;
            }
        }

        public async Task<List<Position>> DetectManualSellsAsync(List<Position> positions, Dictionary<string, double> coinBalances)
        {
            var updatedPositions = new List<Position>();

            foreach (var position in positions)
            {
                if (coinBalances.TryGetValue(position.Coin, out var balance))
                {
                    if (balance >= position.Quantity)
                    {
                        // Position still exists
                        updatedPositions.Add(position);
                    }
                    else
                    {
                        // Position partially or fully sold manually
                        Console.WriteLine($"[MANUAL SELL DETECTED] {position.Coin} | Expected: {position.Quantity:F8} | Found: {balance:F8}");

                        if (balance > 0)
                        {
                            // Partially sold - adjust quantity
                            position.Quantity = balance;
                            updatedPositions.Add(position);
                            Console.WriteLine($"[POSITION ADJUSTED] {position.Coin} | New Qty: {balance:F8}");
                        }
                        else
                        {
                            // Fully sold - log and remove
                            Console.WriteLine($"[POSITION CLOSED] {position.Coin} (manual sell)");

                            // Log manual sell trade
                            var tradeLog = new TradeLog
                            {
                                StrategyName = position.StrategyName + "_MANUAL_SELL",
                                BuyTime = position.BuyTime,
                                SellTime = DateTime.UtcNow,
                                Coin = position.Coin,
                                BuyPrice = position.BuyPrice,
                                SellPrice = 0.0,  // Unknown - manual trade
                                Quantity = position.Quantity,
                                PositionSize = position.BuyPrice * position.Quantity,
                                BuyFee = position.BuyFee,
                                SellFee = 0.0,  // Unknown
                                TotalFees = position.BuyFee,
                                GrossProfitUsd = 0.0,  // Unknown
                                NetProfitUsd = 0.0,  // Unknown
                                ProfitPct = 0.0,
                                PeakProfitPct = position.HighestProfitPct,
                                PortfolioBalance = _portfolio.TotalBalance,
                                SellReason = "Manual Sell (Detected)",
                                Mode = _dryRun ? "DRY_RUN" : "LIVE"
                            };

                            await _dataAgent.AppendTradeLogAsync(tradeLog);
                        }
                    }
                }
                else
                {
                    // Coin not in balances - likely sold
                    Console.WriteLine($"[MANUAL SELL DETECTED] {position.Coin} | Position not found in exchange balances");
                    // Log and remove
                }
            }

            return updatedPositions;
        }

        public async Task<List<Position>> DetectManualBuysAsync(List<Position> positions, Dictionary<string, double> coinBalances)
        {
            var updatedPositions = new List<Position>(positions);

            foreach (var (coin, balance) in coinBalances)
            {
                if (balance > 0.0001)  // Ignore dust
                {
                    var existingPosition = positions.FirstOrDefault(p => p.Coin == coin);

                    if (existingPosition == null)
                    {
                        // New position detected - manual buy
                        Console.WriteLine($"[MANUAL BUY DETECTED] {coin} | Qty: {balance:F8}");
                        Console.WriteLine($"[WARNING] Manual buy detection not fully implemented yet - skipping");
                        // TODO: Implement price fetching to create position
                    }
                    else if (balance > existingPosition.Quantity + 0.0001)
                    {
                        // Quantity increased - manual buy to average down
                        var additionalQty = balance - existingPosition.Quantity;
                        Console.WriteLine($"[MANUAL BUY DETECTED] {coin} | Additional Qty: {additionalQty:F8}");

                        // Update position quantity
                        existingPosition.Quantity = balance;
                        Console.WriteLine($"[POSITION ADJUSTED] {coin} | New Qty: {balance:F8}");
                    }
                }
            }

            return updatedPositions;
        }
    }
}
