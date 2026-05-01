using System;

namespace KadirovQuantLab.Common.Models
{
    public class Position
    {
        public string Id { get; set; }

        // CRITICAL: Strategy identification for performance tracking
        public string StrategyName { get; set; } = string.Empty;  // e.g., "MovingAveragesTrailingMultiplier"

        public string Coin { get; set; }
        public double BuyPrice { get; set; }
        public double BuyPriceBtc { get; set; }
        public DateTime BuyTime { get; set; }
        public double Quantity { get; set; }
        public double BuyFee { get; set; }
        public double HighestProfitPct { get; set; }
        public string OrderId { get; set; }
    }
}
