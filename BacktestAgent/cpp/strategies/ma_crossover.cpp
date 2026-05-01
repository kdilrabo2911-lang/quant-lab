#include "ma_crossover.h"
#include <cmath>
#include <algorithm>
#include <numeric>

namespace backtest {

MA_Crossover::MA_Crossover() {
    fast_ma_period_ = 24;
    slow_ma_period_ = 72;
}

void MA_Crossover::SetParameters(const ParameterSet& params) {
    // Update parameters from ParameterSet
    // (Implementation would parse params and update member variables)
}

ParameterSet MA_Crossover::GetParameters() const {
    ParameterSet params;
    // (Implementation would return current parameters)
    return params;
}

void MA_Crossover::ComputeIndicators(MarketData& data) const {
    // Pre-compute indicators if needed
    // For now, we compute indicators on-demand in ShouldBuy/ShouldSell
}

bool MA_Crossover::ShouldBuy(size_t idx, const MarketData& data, const std::vector<Position>& existing_positions) const {
    // Limit to 1 position at a time
    if (!existing_positions.empty()) return false;

    // Check if we have enough data
    if (idx < 50) return false;

    // Get current values
    double current_price = data.close[idx];
    double current_volume = data.volume[idx];

    bool condition_0 = true;  // ma_crossover_above (not yet implemented)

    return condition_0;
}

bool MA_Crossover::ShouldSell(size_t idx, const MarketData& data, const Position& position) const {
    // Get current price and calculate profit
    double current_price = data.close[idx];
    double profit_pct = ((current_price - position.buy_price) / position.buy_price) * 100.0;

    bool condition_0 = (profit_pct >= 3.0);  // ma_crossover_below default

    return condition_0;
}

std::string MA_Crossover::GetSellReason(size_t idx, const MarketData& data, const Position& position) const {
    double current_price = data.close[idx];
    double profit_pct = ((current_price - position.buy_price) / position.buy_price) * 100.0;

    // Check sell conditions and return reason
    if (profit_pct >= 3.0) {
        return "profit_target";
    }

    return "signal";
}

} // namespace backtest

// Factory function
extern "C" {
    backtest::StrategyInterface* CreateStrategy_MA_Crossover() {
        return new backtest::MA_Crossover();
    }
}
