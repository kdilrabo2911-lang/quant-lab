#include "ma_dip_buyer2.h"
#include <cmath>
#include <algorithm>
#include <numeric>

namespace backtest {

MA_Dip_Buyer2::MA_Dip_Buyer2() {
    ma_period_ = 1152.0;
    dip_threshold_pct_ = 2.5;
    profit_target_pct_ = 2.5;
}

void MA_Dip_Buyer2::SetParameters(const ParameterSet& params) {
    // Update parameters from ParameterSet
    // (Implementation would parse params and update member variables)
}

ParameterSet MA_Dip_Buyer2::GetParameters() const {
    ParameterSet params;
    // (Implementation would return current parameters)
    return params;
}

void MA_Dip_Buyer2::ComputeIndicators(MarketData& data) const {
    // Pre-compute indicators if needed
    // For now, we compute indicators on-demand in ShouldBuy/ShouldSell
}

bool MA_Dip_Buyer2::ShouldBuy(size_t idx, const MarketData& data, const std::vector<Position>& existing_positions) const {
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

bool MA_Dip_Buyer2::ShouldSell(size_t idx, const MarketData& data, const Position& position) const {
    // Get current price and calculate profit
    double current_price = data.close[idx];
    double profit_pct = ((current_price - position.buy_price) / position.buy_price) * 100.0;

    bool condition_0 = (profit_pct >= 3.0);  // Default profit target

    return condition_0;
}

std::string MA_Dip_Buyer2::GetSellReason(size_t idx, const MarketData& data, const Position& position) const {
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
    backtest::StrategyInterface* CreateStrategy_MA_Dip_Buyer2() {
        return new backtest::MA_Dip_Buyer2();
    }
}
