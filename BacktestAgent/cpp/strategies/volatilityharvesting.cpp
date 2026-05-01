#include "volatilityharvesting.h"
#include <cmath>
#include <algorithm>
#include <numeric>

namespace backtest {

VolatilityHarvesting::VolatilityHarvesting() {
    lookback_period_ = 24;
    position_size_pct_ = 10.0;
    volatility_threshold_pct_ = 2.0;
}

void VolatilityHarvesting::SetParameters(const ParameterSet& params) {
    // Update parameters from ParameterSet
    if (params.int_params.count("lookback_period")) {
        lookback_period_ = params.int_params.at("lookback_period");
    }
    if (params.double_params.count("position_size_pct")) {
        position_size_pct_ = params.double_params.at("position_size_pct");
    }
    if (params.double_params.count("volatility_threshold_pct")) {
        volatility_threshold_pct_ = params.double_params.at("volatility_threshold_pct");
    }
}

ParameterSet VolatilityHarvesting::GetParameters() const {
    ParameterSet params;
    params.int_params["lookback_period"] = lookback_period_;
    params.double_params["position_size_pct"] = position_size_pct_;
    params.double_params["volatility_threshold_pct"] = volatility_threshold_pct_;
    return params;
}

void VolatilityHarvesting::ComputeIndicators(MarketData& data) const {
    // Pre-compute indicators if needed
    // For now, we compute indicators on-demand in ShouldBuy/ShouldSell
}

bool VolatilityHarvesting::ShouldBuy(size_t idx, const MarketData& data, const std::vector<Position>& existing_positions) const {
    // Limit to 1 position at a time
    if (!existing_positions.empty()) return false;

    // Check if we have enough data
    if (idx < 50) return false;

    // Get current values
    double current_price = data.close[idx];
    double current_volume = data.volume[idx];

    // Volatility: Buy on % dip from recent peak
    const int lookback = lookback_period_;
    bool condition_0 = false;

    if (idx >= lookback) {
        // Find recent peak
        double recent_peak = data.close[idx - lookback];
        for (size_t j = idx - lookback + 1; j < idx; j++) {
            if (data.close[j] > recent_peak) recent_peak = data.close[j];
        }

        // Check if current price is below peak by volatility_threshold_pct_%
        double dip_threshold = recent_peak * (1.0 - volatility_threshold_pct_ / 100.0);
        condition_0 = (current_price <= dip_threshold);
    }

    return condition_0;
}

bool VolatilityHarvesting::ShouldSell(size_t idx, const MarketData& data, const Position& position) const {
    // Get current price and calculate profit
    double current_price = data.close[idx];
    double profit_pct = ((current_price - position.buy_price) / position.buy_price) * 100.0;

    // Volatility: Sell when price rises % from entry
    bool condition_0 = (profit_pct >= volatility_threshold_pct_);

    return condition_0;
}

std::string VolatilityHarvesting::GetSellReason(size_t idx, const MarketData& data, const Position& position) const {
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
    backtest::StrategyInterface* CreateStrategy_VolatilityHarvesting() {
        return new backtest::VolatilityHarvesting();
    }
}
