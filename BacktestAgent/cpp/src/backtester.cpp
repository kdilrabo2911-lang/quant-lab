#include "backtester.hpp"
#include <fstream>
#include <sstream>
#include <iostream>
#include <algorithm>
#include <cmath>

namespace backtest {

BacktestEngine::BacktestEngine() : fee_rate_(0.0026) {}

void BacktestEngine::LoadDataFromCSV(const std::string& filepath, const std::string& coin) {
    coin_ = coin;
    std::ifstream file(filepath);

    if (!file.is_open()) {
        throw std::runtime_error("Failed to open file: " + filepath);
    }

    std::string line;
    std::getline(file, line);  // Skip header

    while (std::getline(file, line)) {
        std::stringstream ss(line);
        std::string timestamp, open_str, high_str, low_str, close_str, volume_str, close_btc_str;

        std::getline(ss, timestamp, ',');
        std::getline(ss, open_str, ',');
        std::getline(ss, high_str, ',');
        std::getline(ss, low_str, ',');
        std::getline(ss, close_str, ',');
        std::getline(ss, volume_str, ',');
        std::getline(ss, close_btc_str, ',');

        data_.timestamps.push_back(timestamp);
        data_.open.push_back(std::stod(open_str));
        data_.high.push_back(std::stod(high_str));
        data_.low.push_back(std::stod(low_str));
        data_.close.push_back(std::stod(close_str));
        data_.volume.push_back(std::stod(volume_str));
        data_.close_btc.push_back(std::stod(close_btc_str));
    }

    file.close();
}

void BacktestEngine::LoadDataFromVectors(const std::string& coin,
                                         const std::vector<std::string>& timestamps,
                                         const std::vector<double>& close,
                                         const std::vector<double>& open,
                                         const std::vector<double>& high,
                                         const std::vector<double>& low,
                                         const std::vector<double>& volume,
                                         const std::vector<double>& close_btc) {
    coin_ = coin;
    data_.timestamps = timestamps;
    data_.close = close;
    data_.open = open;
    data_.high = high;
    data_.low = low;
    data_.volume = volume;
    data_.close_btc = close_btc;
}

void BacktestEngine::SetStrategy(std::shared_ptr<StrategyInterface> strategy) {
    strategy_ = strategy;
}

void BacktestEngine::SetParameters(const ParameterSet& params) {
    if (strategy_) {
        strategy_->SetParameters(params);
    }
}

BacktestResults BacktestEngine::Run() {
    if (!strategy_) {
        throw std::runtime_error("Strategy not set");
    }

    if (data_.size() == 0) {
        throw std::runtime_error("No data loaded");
    }

    BacktestResults results;
    results.strategy_name = strategy_->GetName();
    results.coin = coin_;

    // Compute indicators once
    strategy_->ComputeIndicators(data_);

    // Track all positions (can have multiple)
    std::vector<Position> positions;

    // Equity tracking (start with 100%)
    double equity = 100.0;
    results.equity_curve.push_back(equity);

    // Simulate trading
    for (size_t idx = 0; idx < data_.size(); idx++) {
        double current_price = data_.close[idx];
        double current_price_btc = data_.close_btc[idx];

        // Check sell signals for existing positions
        for (auto it = positions.begin(); it != positions.end(); ) {
            if (strategy_->ShouldSell(idx, data_, *it)) {
                std::string reason = strategy_->GetSellReason(idx, data_, *it);
                Trade trade = SimulateTrade(*it, idx, reason);
                results.trades.push_back(trade);

                // Update equity
                equity *= (1.0 + trade.profit_pct / 100.0);

                it = positions.erase(it);
            } else {
                // Update highest profit
                double profit_pct = ((current_price - it->buy_price) / it->buy_price) * 100.0;
                it->highest_profit_pct = std::max(it->highest_profit_pct, profit_pct);
                ++it;
            }
        }

        // Check buy signal
        if (strategy_->ShouldBuy(idx, data_, positions)) {
            Position pos;
            pos.buy_price = current_price;
            pos.buy_price_btc = current_price_btc;
            pos.buy_idx = idx;
            pos.highest_profit_pct = 0.0;
            pos.active = true;

            positions.push_back(pos);
        }

        results.equity_curve.push_back(equity);
    }

    // Close any remaining positions at end
    for (const auto& pos : positions) {
        Trade trade = SimulateTrade(pos, data_.size() - 1, "end_of_data");
        results.trades.push_back(trade);
        equity *= (1.0 + trade.profit_pct / 100.0);
    }

    results.total_return_pct = equity - 100.0;
    results.num_trades = results.trades.size();

    CalculateMetrics(results);

    return results;
}

Trade BacktestEngine::SimulateTrade(const Position& pos, size_t sell_idx, const std::string& reason) {
    Trade trade;
    trade.coin = coin_;
    trade.buy_time = data_.timestamps[pos.buy_idx];
    trade.sell_time = data_.timestamps[sell_idx];
    trade.buy_price = pos.buy_price;
    trade.sell_price = data_.close[sell_idx];
    trade.peak_profit_pct = pos.highest_profit_pct;
    trade.sell_reason = reason;
    trade.hold_duration = sell_idx - pos.buy_idx;

    // Calculate profit with fees
    double gross_profit_pct = ((trade.sell_price - trade.buy_price) / trade.buy_price) * 100.0;
    double buy_fee_pct = fee_rate_ * 100.0;
    double sell_fee_pct = fee_rate_ * 100.0;
    trade.profit_pct = gross_profit_pct - buy_fee_pct - sell_fee_pct;

    return trade;
}

void BacktestEngine::CalculateMetrics(BacktestResults& results) {
    if (results.trades.empty()) {
        return;
    }

    // Win rate
    int wins = 0;
    double total_profit = 0.0;
    double total_loss = 0.0;

    for (const auto& trade : results.trades) {
        if (trade.profit_pct > 0) {
            wins++;
            total_profit += trade.profit_pct;
        } else {
            total_loss += trade.profit_pct;
        }
    }

    results.win_rate = static_cast<double>(wins) / results.num_trades;
    results.avg_profit_pct = wins > 0 ? total_profit / wins : 0.0;
    results.avg_loss_pct = (results.num_trades - wins) > 0 ? total_loss / (results.num_trades - wins) : 0.0;

    // Max drawdown
    double peak = 100.0;
    double max_dd = 0.0;

    for (double equity : results.equity_curve) {
        peak = std::max(peak, equity);
        double dd = ((peak - equity) / peak) * 100.0;
        max_dd = std::max(max_dd, dd);
    }

    results.max_drawdown_pct = max_dd;

    // Sharpe ratio (simplified - using trade returns)
    if (results.num_trades > 1) {
        std::vector<double> returns;
        for (const auto& trade : results.trades) {
            returns.push_back(trade.profit_pct);
        }

        double mean = 0.0;
        for (double r : returns) mean += r;
        mean /= returns.size();

        double variance = 0.0;
        for (double r : returns) {
            variance += (r - mean) * (r - mean);
        }
        variance /= returns.size();

        double std_dev = std::sqrt(variance);
        results.sharpe_ratio = std_dev > 0 ? mean / std_dev : 0.0;
    }
}

} // namespace backtest
