using System;
using System.Collections.Generic;
using System.Linq;
using System.Threading.Tasks;
using KadirovQuantLab.Common.Models;
using KadirovQuantLab.Common.Exchange;

namespace KadirovQuantLab.Common.Portfolio
{
    public class PortfolioTracker : IPortfolioTracker
    {
        private PortfolioState _portfolioState;
        private readonly bool _dryRun;

        public double TotalBalance => _dryRun ? _portfolioState.TotalBalanceDryRun : _portfolioState.TotalBalance;
        public double InitialBalance => _dryRun ? _portfolioState.InitialBalanceDryRun : _portfolioState.InitialBalance;
        public double RealizedProfitLoss => _dryRun ? _portfolioState.RealizedProfitLossDryRun : _portfolioState.RealizedProfitLoss;

        public PortfolioTracker(PortfolioState initialState, bool dryRun = false)
        {
            _portfolioState = initialState ?? throw new ArgumentNullException(nameof(initialState));
            _dryRun = dryRun;
        }

        public double GetAvailableBalance(List<Position> positions)
        {
            // TotalBalance already represents free USD available to spend
            // No need to subtract locked capital since Kraken's Balance API returns free USD
            var balance = _dryRun ? _portfolioState.TotalBalanceDryRun : _portfolioState.TotalBalance;
            return balance;
        }

        public double GetLockedCapital(List<Position> positions)
        {
            // Sum up the cost basis of all open positions
            double lockedCapital = 0.0;
            foreach (var pos in positions)
            {
                lockedCapital += pos.BuyPrice * pos.Quantity;
            }
            return lockedCapital;
        }

        public async Task<double> CalculateUnrealizedPnLAsync(List<Position> positions, IKrakenClient krakenClient)
        {
            double unrealizedPnL = 0.0;

            foreach (var position in positions)
            {
                try
                {
                    var (currentPrice, _) = await krakenClient.GetCurrentPriceAsync(position.Coin);
                    var currentValue = currentPrice * position.Quantity;
                    var costBasis = position.BuyPrice * position.Quantity;
                    unrealizedPnL += (currentValue - costBasis);
                }
                catch (Exception ex)
                {
                    Console.WriteLine($"[WARNING] Failed to get price for {position.Coin}: {ex.Message}");
                }
            }

            return unrealizedPnL;
        }

        public void RecordClosedTrade(TradeLog tradeLog)
        {
            // Update realized P/L based on the trade outcome
            // This method is called after a position is closed
            if (_dryRun)
            {
                _portfolioState.RealizedProfitLossDryRun = InitialBalance > 0
                    ? ((TotalBalance - InitialBalance) / InitialBalance) * 100.0
                    : 0.0;
                _portfolioState.LastUpdatedDryRun = DateTime.Now;
            }
            else
            {
                _portfolioState.RealizedProfitLoss = InitialBalance > 0
                    ? ((TotalBalance - InitialBalance) / InitialBalance) * 100.0
                    : 0.0;
                _portfolioState.LastUpdated = DateTime.Now;
            }
        }

        public void UpdateBalance(double newBalance)
        {
            if (_dryRun)
            {
                _portfolioState.TotalBalanceDryRun = newBalance;
                _portfolioState.RealizedProfitLossDryRun = InitialBalance > 0
                    ? ((TotalBalance - InitialBalance) / InitialBalance) * 100.0
                    : 0.0;
                _portfolioState.LastUpdatedDryRun = DateTime.Now;
            }
            else
            {
                _portfolioState.TotalBalance = newBalance;
                _portfolioState.RealizedProfitLoss = InitialBalance > 0
                    ? ((TotalBalance - InitialBalance) / InitialBalance) * 100.0
                    : 0.0;
                _portfolioState.LastUpdated = DateTime.Now;
            }
        }

        public void DeductCost(double cost)
        {
            // Deduct cost from balance (for buy orders: position cost + fee)
            if (_dryRun)
            {
                _portfolioState.TotalBalanceDryRun -= cost;
                _portfolioState.LastUpdatedDryRun = DateTime.Now;
            }
            else
            {
                _portfolioState.TotalBalance -= cost;
                _portfolioState.LastUpdated = DateTime.Now;
            }
        }

        public void AddProceeds(double proceeds)
        {
            // Add proceeds to balance (for sell orders: proceeds - fee)
            if (_dryRun)
            {
                _portfolioState.TotalBalanceDryRun += proceeds;
                _portfolioState.RealizedProfitLossDryRun = InitialBalance > 0
                    ? ((TotalBalance - InitialBalance) / InitialBalance) * 100.0
                    : 0.0;
                _portfolioState.LastUpdatedDryRun = DateTime.Now;
            }
            else
            {
                _portfolioState.TotalBalance += proceeds;
                _portfolioState.RealizedProfitLoss = InitialBalance > 0
                    ? ((TotalBalance - InitialBalance) / InitialBalance) * 100.0
                    : 0.0;
                _portfolioState.LastUpdated = DateTime.Now;
            }
        }

        public PortfolioState GetState()
        {
            return _portfolioState;
        }
    }
}
