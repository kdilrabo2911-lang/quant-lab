#pragma once

#include "types.hpp"
#include <memory>

namespace backtest {

// Base strategy interface - all strategies must implement this
class StrategyInterface {
public:
    virtual ~StrategyInterface() = default;

    // Strategy identification
    virtual std::string GetName() const = 0;

    // Signal generation
    virtual bool ShouldBuy(size_t idx, const MarketData& data, const std::vector<Position>& existing_positions) const = 0;
    virtual bool ShouldSell(size_t idx, const MarketData& data, const Position& position) const = 0;

    // Optional: sell reason for logging
    virtual std::string GetSellReason(size_t idx, const MarketData& data, const Position& position) const {
        return "signal";
    }

    // Parameter management
    virtual void SetParameters(const ParameterSet& params) = 0;
    virtual ParameterSet GetParameters() const = 0;

    // Indicator caching (compute once, reuse)
    virtual void ComputeIndicators(MarketData& data) const = 0;
};

} // namespace backtest
