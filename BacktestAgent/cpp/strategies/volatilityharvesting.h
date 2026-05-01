#ifndef VOLATILITYHARVESTING_H
#define VOLATILITYHARVESTING_H

#include "strategy_interface.hpp"
#include "types.hpp"
#include <vector>
#include <string>

namespace backtest {

/**
 * VolatilityHarvesting Strategy
 *
 * Harvests profits from coin volatility by buying dips and selling peaks. Captures a configurable percentage (default 2%) off volatility swings. The threshold is adjustable per coin since volatility varies - more volatile coins may use higher thresholds, less volatile coins lower ones.
 */
class VolatilityHarvesting : public StrategyInterface {
private:
    // Strategy parameters
    int lookback_period_;
    double position_size_pct_;
    double volatility_threshold_pct_;

public:
    VolatilityHarvesting();

    // StrategyInterface implementation
    std::string GetName() const override { return "VolatilityHarvesting"; }

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
    backtest::StrategyInterface* CreateStrategy_VolatilityHarvesting();
}

#endif // VOLATILITYHARVESTING_H
