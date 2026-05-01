using System.Collections.Generic;
using System.Threading.Tasks;
using KadirovQuantLab.Common.Models;

namespace KadirovQuantLab.Common.Execution
{
    public interface IPositionSyncService
    {
        Task<List<Position>> SyncPositionsWithExchangeAsync(List<Position> currentPositions);
        Task<List<Position>> DetectManualSellsAsync(List<Position> positions, Dictionary<string, double> coinBalances);
        Task<List<Position>> DetectManualBuysAsync(List<Position> positions, Dictionary<string, double> coinBalances);
    }
}
