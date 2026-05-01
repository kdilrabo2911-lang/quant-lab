using System;

namespace KadirovQuantLab.Common.Models
{
    public class PortfolioState
    {
        // Live mode metrics
        public double TotalBalance { get; set; }
        public double InitialBalance { get; set; }
        public double RealizedProfitLoss { get; set; }
        public DateTime LastUpdated { get; set; }

        // Dry run mode metrics (separate tracking)
        public double TotalBalanceDryRun { get; set; }
        public double InitialBalanceDryRun { get; set; }
        public double RealizedProfitLossDryRun { get; set; }
        public DateTime LastUpdatedDryRun { get; set; }
    }
}
