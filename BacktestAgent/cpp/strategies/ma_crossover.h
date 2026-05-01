#ifndef MA_CROSSOVER_H
#define MA_CROSSOVER_H

#include "strategy_interface.hpp"
#include "types.hpp"
#include <vector>
#include <string>

namespace backtest {

/**
 * MA_Crossover Strategy
 *
 * Moving Average Crossover strategy. Buys when fast MA crosses above slow MA (golden cross) and sells when fast MA crosses below slow MA (death cross). Default fast MA=1 day (24h), slow MA=3 days (72h).
 */
class MA_Crossover : public StrategyInterface {
private:
    // Strategy parameters
    int fast_ma_period_;
    int slow_ma_period_;

public:
    MA_Crossover();

    // StrategyInterface implementation
    std::string GetName() const override { return "MA_Crossover"; }

    bool ShouldBuy(size_t idx, const MarketData& data, const std::vector<Position>& existing_positions) const override;
    bool ShouldSell(size_t idx, const MarketData& data, const Position& position) const override;

    void SetParameters(const ParameterSet& params) override;
    ParameterSet GetParameters() const override;

    void ComputeIndicators(MarketData& data) const override;

    std::string GetSellReason(size_t idx, const MarketData& data, const Position& position) const override;
};

} // namespace backtest

// Factory function for dynamic loading
extern "C" {
    backtest::StrategyInterface* CreateStrategy_MA_Crossover();
}

#endif // MA_CROSSOVER_H
