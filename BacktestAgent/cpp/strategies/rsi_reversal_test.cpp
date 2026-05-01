#include "rsi_reversal_test.h"
#include <cmath>
#include <algorithm>
#include <numeric>

namespace backtest {

RSI_Reversal_Test::RSI_Reversal_Test() {
    rsi_period_ = 14.0;
    rsi_oversold_ = 30.0;
    rsi_overbought_ = 70.0;
    profit_target_pct_ = 3.0;
}

void RSI_Reversal_Test::SetParameters(const ParameterSet& params) {
    // Update parameters from ParameterSet
    // (Implementation would parse params and update member variables)
}

ParameterSet RSI_Reversal_Test::GetParameters() const {
    ParameterSet params;
    // (Implementation would return current parameters)
    return params;
}

void RSI_Reversal_Test::ComputeIndicators(MarketData& data) const {
    // Pre-compute indicators if needed
    // For now, we compute indicators on-demand in ShouldBuy/ShouldSell
}

bool RSI_Reversal_Test::ShouldBuy(size_t idx, const MarketData& data, const std::vector<Position>& existing_positions) const {
    // Limit to 1 position at a time
    if (!existing_positions.empty()) return false;

    // Check if we have enough data
    if (idx < 50) return false;

    // Get current values
    double current_price = data.close[idx];
    double current_volume = data.volume[idx];

    bool condition_0 = true;  // Condition (simplified)

    return condition_0;
}

bool RSI_Reversal_Test::ShouldSell(size_t idx, const MarketData& data, const Position& position) const {
    // Get current price and calculate profit
    double current_price = data.close[idx];
    double profit_pct = ((current_price - position.buy_price) / position.buy_price) * 100.0;

    bool condition_0 = (profit_pct >= 3.0);  // Default profit target

    return condition_0;
}

std::string RSI_Reversal_Test::GetSellReason(size_t idx, const MarketData& data, const Position& position) const {
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
    backtest::StrategyInterface* CreateStrategy_RSI_Reversal_Test() {
        return new backtest::RSI_Reversal_Test();
    }
}
