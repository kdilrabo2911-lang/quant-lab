#ifndef MA_DIP_BUYER2_H
#define MA_DIP_BUYER2_H

#include "strategy_interface.hpp"
#include "types.hpp"
#include <vector>
#include <string>

namespace backtest {

/**
 * MA_Dip_Buyer2 Strategy
 *
 * A dip-buying strategy that enters positions when price is below a Moving Average and ensures sufficient distance from the last open/closed position price. Sells when a profit target is reached. MA period is set to 1 day (to be optimized later).
 */
class MA_Dip_Buyer2 : public StrategyInterface {
private:
    // Strategy parameters
    double ma_period_;
    double dip_threshold_pct_;
    double profit_target_pct_;

public:
    MA_Dip_Buyer2();

    // StrategyInterface implementation
    std::string GetName() const override { return "MA_Dip_Buyer2"; }

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
    backtest::StrategyInterface* CreateStrategy_MA_Dip_Buyer2();
}

#endif // MA_DIP_BUYER2_H
