using System;

namespace KadirovQuantLab.Common.Models
{
    public class TradeLog
    {
        // CRITICAL: Strategy identification for performance tracking
        public string StrategyName { get; set; } = string.Empty;  // e.g., "MovingAveragesTrailingMultiplier"

        public DateTime BuyTime { get; set; }
        public DateTime SellTime { get; set; }
        public string Coin { get; set; }
        public double BuyPrice { get; set; }
        public double SellPrice { get; set; }
        public double Quantity { get; set; }
        public double PositionSize { get; set; }
        public double BuyFee { get; set; }
        public double SellFee { get; set; }
        public double TotalFees { get; set; }
        public double GrossProfitUsd { get; set; }
        public double NetProfitUsd { get; set; }
        public double ProfitPct { get; set; }
        public double PeakProfitPct { get; set; }
        public double PortfolioBalance { get; set; }
        public string SellReason { get; set; }
        public string Mode { get; set; } = "LIVE"; // "LIVE" or "DRY_RUN"
    }
}
