using System.Collections.Generic;
using System.Threading.Tasks;
using KadirovQuantLab.Common.Models;
using KadirovQuantLab.Common.Exchange;

namespace KadirovQuantLab.Common.Portfolio
{
    public interface IPortfolioTracker
    {
        double TotalBalance { get; }
        double InitialBalance { get; }
        double RealizedProfitLoss { get; }

        double GetAvailableBalance(List<Position> positions);
        double GetLockedCapital(List<Position> positions);
        Task<double> CalculateUnrealizedPnLAsync(List<Position> positions, IKrakenClient krakenClient);
        void RecordClosedTrade(TradeLog tradeLog);
        void UpdateBalance(double newBalance);
        void DeductCost(double cost);
        void AddProceeds(double proceeds);
        PortfolioState GetState();
    }
}
