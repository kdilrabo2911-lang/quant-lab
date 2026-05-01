using System.Threading.Tasks;
using KadirovQuantLab.Common.Models;

namespace KadirovQuantLab.Common.Execution
{
    /// <summary>
    /// Unified order executor for ALL strategies.
    /// CRITICAL: strategyName parameter tracks which strategy initiated the trade.
    /// </summary>
    public interface IOrderExecutor
    {
        Task<Position> ExecuteBuyAsync(
            string strategyName,     // NEW: Track which strategy made this trade
            string coin,
            double priceUsd,
            double priceBtc,
            double positionSizeUsd
        );

        Task<TradeLog> ExecuteSellAsync(
            string strategyName,     // NEW: Track which strategy made this trade
            Position position,
            double priceUsd,
            string reason
        );
    }
}
