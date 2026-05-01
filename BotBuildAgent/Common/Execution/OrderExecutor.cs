using System;
using System.Threading.Tasks;
using KadirovQuantLab.Common.DataAgent;
using KadirovQuantLab.Common.Exchange;
using KadirovQuantLab.Common.Models;
using KadirovQuantLab.Common.Portfolio;

namespace KadirovQuantLab.Common.Execution
{
    /// <summary>
    /// UNIFIED order executor for ALL strategies.
    /// Handles buy/sell orders with strategy tracking.
    /// </summary>
    public class OrderExecutor : IOrderExecutor
    {
        private readonly IKrakenClient _krakenClient;
        private readonly IPortfolioTracker _portfolio;
        private readonly IDataAgentClient _dataAgent;
        private readonly bool _dryRun;

        private const double KRAKEN_TAKER_FEE = 0.0026; // 0.26%
        private const double MANUAL_BUY_FEE = 0.0025;  // 0.25%
        private const double MANUAL_SELL_FEE = 0.0040; // 0.40%

        public OrderExecutor(
            IKrakenClient krakenClient,
            IPortfolioTracker portfolio,
            IDataAgentClient dataAgent,
            bool dryRun = false)
        {
            _krakenClient = krakenClient;
            _portfolio = portfolio;
            _dataAgent = dataAgent;
            _dryRun = dryRun;
        }

        public async Task<Position> ExecuteBuyAsync(
            string strategyName,
            string coin,
            double priceUsd,
            double priceBtc,
            double positionSizeUsd)
        {
            var estimatedBuyFee = positionSizeUsd * KRAKEN_TAKER_FEE;
            var estimatedTotalCost = positionSizeUsd + estimatedBuyFee;
            var quantity = positionSizeUsd / priceUsd;

            var mode = _dryRun ? "[DRY RUN]" : "[LIVE]";

            Console.WriteLine($"{mode} [{strategyName}] [BUY] {coin} | Price: ${priceUsd:F4} ({priceBtc:F8} BTC) | Qty: {quantity:F4} | Size: ${positionSizeUsd:F2}");
            Console.WriteLine($"  Estimated Fee: ${estimatedBuyFee:F2} | Estimated Total Cost: ${estimatedTotalCost:F2}");
            Console.WriteLine($"  Portfolio Balance: ${_portfolio.TotalBalance:F2}");

            string orderId = null;
            double actualFee = estimatedBuyFee;
            double actualCost = positionSizeUsd;
            double actualQuantity = quantity;

            if (!_dryRun)
            {
                try
                {
                    // Place market order
                    orderId = await _krakenClient.PlaceMarketOrderAsync(coin, "buy", quantity);
                    Console.WriteLine($"[ORDER] Buy order placed | Order ID: {orderId}");

                    // Try to fetch actual order details with retry logic
                    var orderDetails = await _krakenClient.QueryOrderDetailsAsync(orderId, maxRetries: 3);

                    if (orderDetails.HasValue)
                    {
                        actualCost = orderDetails.Value.cost;
                        actualFee = orderDetails.Value.fee;
                        actualQuantity = orderDetails.Value.quantity;

                        Console.WriteLine($"[ORDER] Buy order filled | Actual Cost: ${actualCost:F2} | Actual Fee: ${actualFee:F2} | Actual Qty: {actualQuantity:F8}");
                    }
                    else
                    {
                        // Fallback to manual fee estimate
                        Console.WriteLine($"[WARNING] Could not fetch order details after 5s, using manual fee estimate (0.25%)");
                        actualFee = positionSizeUsd * MANUAL_BUY_FEE;
                        actualCost = positionSizeUsd;
                        actualQuantity = quantity;
                    }
                }
                catch (Exception ex)
                {
                    Console.WriteLine($"[ERROR] Failed to place buy order: {ex.Message}");
                    throw;
                }
            }

            // Deduct cost from portfolio
            var totalCostActual = actualCost + actualFee;
            _portfolio.DeductCost(totalCostActual);
            await _dataAgent.SavePortfolioStateAsync(_portfolio.GetState());

            // Create position with strategy name
            var position = new Position
            {
                Id = Guid.NewGuid().ToString(),
                StrategyName = strategyName,  // CRITICAL: Tag position with strategy
                Coin = coin,
                BuyPrice = actualCost / actualQuantity,
                BuyPriceBtc = priceBtc,
                BuyTime = DateTime.UtcNow,
                Quantity = actualQuantity,
                BuyFee = actualFee,
                HighestProfitPct = 0.0,
                OrderId = orderId
            };

            Console.WriteLine($"[POSITION] Created: {coin} ({position.Id[..8]}) | Strategy: {strategyName} | Qty: {actualQuantity:F8} | Cost: ${actualCost + actualFee:F2}");

            return position;
        }

        public async Task<TradeLog> ExecuteSellAsync(
            string strategyName,
            Position position,
            double priceUsd,
            string reason)
        {
            var profitPct = ((priceUsd - position.BuyPrice) / position.BuyPrice) * 100.0;
            var grossProfitUsd = (priceUsd * position.Quantity) - (position.BuyPrice * position.Quantity);
            var estimatedSellFee = (priceUsd * position.Quantity) * KRAKEN_TAKER_FEE;

            var mode = _dryRun ? "[DRY RUN]" : "[LIVE]";

            Console.WriteLine($"{mode} [{strategyName}] [SELL] {position.Coin} | Price: ${priceUsd:F4} | Qty: {position.Quantity:F4} | Profit: {profitPct:F2}%");
            Console.WriteLine($"  Reason: {reason}");
            Console.WriteLine($"  Buy Price: ${position.BuyPrice:F4} | Sell Price: ${priceUsd:F4}");
            Console.WriteLine($"  Estimated Fee: ${estimatedSellFee:F2}");

            string orderId = null;
            double actualSellFee = estimatedSellFee;
            double actualProceeds = priceUsd * position.Quantity;

            if (!_dryRun)
            {
                try
                {
                    // Place market sell order
                    orderId = await _krakenClient.PlaceMarketOrderAsync(position.Coin, "sell", position.Quantity);
                    Console.WriteLine($"[ORDER] Sell order placed | Order ID: {orderId}");

                    // Try to fetch actual order details
                    var orderDetails = await _krakenClient.QueryOrderDetailsAsync(orderId, maxRetries: 3);

                    if (orderDetails.HasValue)
                    {
                        actualProceeds = orderDetails.Value.cost;
                        actualSellFee = orderDetails.Value.fee;

                        Console.WriteLine($"[ORDER] Sell order filled | Actual Proceeds: ${actualProceeds:F2} | Actual Fee: ${actualSellFee:F2}");
                    }
                    else
                    {
                        // Fallback to manual fee estimate
                        Console.WriteLine($"[WARNING] Could not fetch order details after 5s, using manual fee estimate (0.40%)");
                        actualSellFee = actualProceeds * MANUAL_SELL_FEE;
                    }
                }
                catch (Exception ex)
                {
                    Console.WriteLine($"[ERROR] Failed to place sell order: {ex.Message}");
                    throw;
                }
            }

            // Calculate actual P/L
            var positionCost = position.BuyPrice * position.Quantity;
            var netProceeds = actualProceeds - actualSellFee;
            var totalFees = position.BuyFee + actualSellFee;
            var netProfitUsd = netProceeds - positionCost - position.BuyFee;
            var actualProfitPct = (netProfitUsd / (positionCost + position.BuyFee)) * 100.0;

            // Add proceeds to portfolio
            _portfolio.AddProceeds(netProceeds);
            await _dataAgent.SavePortfolioStateAsync(_portfolio.GetState());

            // Create trade log with strategy name
            var tradeLog = new TradeLog
            {
                StrategyName = strategyName,  // CRITICAL: Tag trade with strategy
                BuyTime = position.BuyTime,
                SellTime = DateTime.UtcNow,
                Coin = position.Coin,
                BuyPrice = position.BuyPrice,
                SellPrice = priceUsd,
                Quantity = position.Quantity,
                PositionSize = positionCost,
                BuyFee = position.BuyFee,
                SellFee = actualSellFee,
                TotalFees = totalFees,
                GrossProfitUsd = grossProfitUsd,
                NetProfitUsd = netProfitUsd,
                ProfitPct = actualProfitPct,
                PeakProfitPct = position.HighestProfitPct,
                PortfolioBalance = _portfolio.TotalBalance,
                SellReason = reason,
                Mode = _dryRun ? "DRY_RUN" : "LIVE"
            };

            // Record trade and update realized P/L
            _portfolio.RecordClosedTrade(tradeLog);
            await _dataAgent.AppendTradeLogAsync(tradeLog);
            await _dataAgent.SavePortfolioStateAsync(_portfolio.GetState());

            Console.WriteLine($"[TRADE] [{strategyName}] Closed: {position.Coin} | Net P/L: ${netProfitUsd:F2} ({actualProfitPct:F2}%) | New Balance: ${_portfolio.TotalBalance:F2}");

            return tradeLog;
        }
    }
}
