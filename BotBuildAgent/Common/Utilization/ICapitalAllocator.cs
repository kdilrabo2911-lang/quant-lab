namespace KadirovQuantLab.Common.Utilization
{
    public interface ICapitalAllocator
    {
        double CalculatePositionSize(double initialBalance, double availableBalance, int totalCoins);
        bool CanAffordPosition(double positionSize, double availableBalance, double estimatedFee);
        double GetMinimumPositionSize();
    }
}
