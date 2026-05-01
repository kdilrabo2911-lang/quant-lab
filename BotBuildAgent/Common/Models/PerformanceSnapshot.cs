using System;

namespace KadirovQuantLab.Common.Models
{
    public class PerformanceSnapshot
    {
        public DateTime Timestamp { get; set; }
        public double PortfolioBalance { get; set; }
        public double InitialBalance { get; set; }
        public int OpenPositions { get; set; }
        public double LockedCapital { get; set; }
        public double UnrealizedPnL { get; set; }
        public double UnrealizedReturnPct { get; set; }
        public double RealizedPnL { get; set; }
        public double RealizedReturnPct { get; set; }
        public double TotalPnL { get; set; }
        public double TotalReturnPct { get; set; }
    }
}
