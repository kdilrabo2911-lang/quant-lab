using System;

namespace KadirovQuantLab.Common.Utilization
{
    public class CapitalAllocator : ICapitalAllocator
    {
        private const double KRAKEN_MINIMUM_POSITION_SIZE = 10.0; // Kraken requires minimum $10 per trade

        public double CalculatePositionSize(double initialBalance, double availableBalance, int totalCoins)
        {
            if (totalCoins <= 0)
            {
                throw new ArgumentException("Total coins must be greater than zero", nameof(totalCoins));
            }

            // Target position size: what we want to allocate per coin based on initial portfolio
            var targetPositionSize = initialBalance / totalCoins;

            // Max position size: what we can actually afford now based on available capital
            var maxPositionSize = availableBalance / totalCoins;

            // Return the minimum of the two: we want target size, but cap at what's available
            return Math.Min(targetPositionSize, maxPositionSize);
        }

        public bool CanAffordPosition(double positionSize, double availableBalance, double estimatedFee)
        {
            // Check if position size meets minimum requirement
            if (positionSize < KRAKEN_MINIMUM_POSITION_SIZE)
            {
                return false;
            }

            // Check if we have enough balance to cover position + fee
            var totalCost = positionSize + estimatedFee;
            return totalCost <= availableBalance;
        }

        public double GetMinimumPositionSize()
        {
            return KRAKEN_MINIMUM_POSITION_SIZE;
        }
    }
}
