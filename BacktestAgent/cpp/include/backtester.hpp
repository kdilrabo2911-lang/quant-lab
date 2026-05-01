#pragma once

#include "types.hpp"
#include "strategy_interface.hpp"
#include <memory>

namespace backtest {

class BacktestEngine {
public:
    BacktestEngine();

    // Data loading
    void LoadDataFromCSV(const std::string& filepath, const std::string& coin);
    void LoadDataFromVectors(const std::string& coin,
                             const std::vector<std::string>& timestamps,
                             const std::vector<double>& close,
                             const std::vector<double>& open,
                             const std::vector<double>& high,
                             const std::vector<double>& low,
                             const std::vector<double>& volume,
                             const std::vector<double>& close_btc);

    // Strategy setup
    void SetStrategy(std::shared_ptr<StrategyInterface> strategy);
    void SetParameters(const ParameterSet& params);

    // Execution
    BacktestResults Run();

    // Configuration
    void SetFeeRate(double fee_rate) { fee_rate_ = fee_rate; }

private:
    MarketData data_;
    std::string coin_;
    std::shared_ptr<StrategyInterface> strategy_;
    double fee_rate_;  // e.g., 0.0026 for 0.26%

    // Simulate single trade
    Trade SimulateTrade(const Position& pos, size_t sell_idx, const std::string& reason);

    // Calculate performance metrics
    void CalculateMetrics(BacktestResults& results);
};

} // namespace backtest
