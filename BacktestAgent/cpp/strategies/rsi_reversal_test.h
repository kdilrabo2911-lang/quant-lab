#ifndef RSI_REVERSAL_TEST_H
#define RSI_REVERSAL_TEST_H

#include "strategy_interface.hpp"
#include "types.hpp"
#include <vector>
#include <string>

namespace backtest {

/**
 * RSI_Reversal_Test Strategy
 *
 * RSI reversal strategy for testing complete workflow
 */
class RSI_Reversal_Test : public StrategyInterface {
private:
    // Strategy parameters
    double rsi_period_;
    double rsi_oversold_;
    double rsi_overbought_;
    double profit_target_pct_;

public:
    RSI_Reversal_Test();

    // StrategyInterface implementation
    std::string GetName() const override { return "RSI_Reversal_Test"; }

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
    backtest::StrategyInterface* CreateStrategy_RSI_Reversal_Test();
}

#endif // RSI_REVERSAL_TEST_H
