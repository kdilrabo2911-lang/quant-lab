#pragma once

#include <string>
#include <vector>
#include <map>

namespace backtest {

// OHLC candle data
struct CandleData {
    std::string timestamp;
    double open;
    double high;
    double low;
    double close;
    double volume;
    double close_btc;  // Price in BTC
};

// Market data container
struct MarketData {
    std::vector<double> close;
    std::vector<double> open;
    std::vector<double> high;
    std::vector<double> low;
    std::vector<double> volume;
    std::vector<double> close_btc;
    std::vector<std::string> timestamps;

    // Cached indicators (computed once, reused)
    std::map<std::string, std::vector<double>> indicators;

    size_t size() const { return close.size(); }
};

// Position in backtest
struct Position {
    double buy_price;
    double buy_price_btc;
    size_t buy_idx;
    double highest_profit_pct;
    bool active;

    Position() : buy_price(0), buy_price_btc(0), buy_idx(0), highest_profit_pct(0), active(false) {}
};

// Trade result
struct Trade {
    std::string coin;
    std::string buy_time;
    std::string sell_time;
    double buy_price;
    double sell_price;
    double profit_pct;
    double peak_profit_pct;
    std::string sell_reason;
    size_t hold_duration;  // candles
};

// Backtest results
struct BacktestResults {
    std::string strategy_name;
    std::string coin;
    double total_return_pct;
    int num_trades;
    double win_rate;
    double avg_profit_pct;
    double avg_loss_pct;
    double max_drawdown_pct;
    double sharpe_ratio;
    std::vector<Trade> trades;
    std::vector<double> equity_curve;

    BacktestResults() : total_return_pct(0), num_trades(0), win_rate(0),
                        avg_profit_pct(0), avg_loss_pct(0), max_drawdown_pct(0), sharpe_ratio(0) {}
};

// Strategy parameters (generic)
struct ParameterSet {
    std::map<std::string, int> int_params;
    std::map<std::string, double> double_params;
    std::map<std::string, std::string> string_params;

    int get_int(const std::string& key, int default_val = 0) const {
        auto it = int_params.find(key);
        return it != int_params.end() ? it->second : default_val;
    }

    double get_double(const std::string& key, double default_val = 0.0) const {
        auto it = double_params.find(key);
        return it != double_params.end() ? it->second : default_val;
    }

    std::string get_string(const std::string& key, const std::string& default_val = "") const {
        auto it = string_params.find(key);
        return it != string_params.end() ? it->second : default_val;
    }

    void set(const std::string& key, int val) { int_params[key] = val; }
    void set(const std::string& key, double val) { double_params[key] = val; }
    void set(const std::string& key, const std::string& val) { string_params[key] = val; }
};

} // namespace backtest
