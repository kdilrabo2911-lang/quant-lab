#include "backtester.hpp"
#include "strategy_interface.hpp"
#include <iostream>
#include <fstream>
#include <memory>
#include <string>
#include <iomanip>
#include <sstream>

using namespace backtest;

// Forward declarations for strategy factory functions
extern "C" {
    // Only MA_Dip_Buyer2 is currently compiled
    StrategyInterface* CreateStrategy_MA_Dip_Buyer2();
    StrategyInterface* CreateStrategy_RSI_Reversal_Test();
    StrategyInterface* CreateStrategy_VolatilityHarvesting();
    StrategyInterface* CreateStrategy_MA_Crossover();
}

std::shared_ptr<StrategyInterface> CreateStrategy(const std::string& strategy_name) {
    if (strategy_name == "ma_dip_buyer2" || strategy_name == "MA_Dip_Buyer2") {
        return std::shared_ptr<StrategyInterface>(CreateStrategy_MA_Dip_Buyer2());
    } else if (strategy_name == "rsi_reversal_test" || strategy_name == "RSI_Reversal_Test") {
        return std::shared_ptr<StrategyInterface>(CreateStrategy_RSI_Reversal_Test());
    } else if (strategy_name == "volatilityharvesting" || strategy_name == "VolatilityHarvesting") {
        return std::shared_ptr<StrategyInterface>(CreateStrategy_VolatilityHarvesting());
    } else if (strategy_name == "ma_crossover" || strategy_name == "MA_Crossover") {
        return std::shared_ptr<StrategyInterface>(CreateStrategy_MA_Crossover());
    } else {
        throw std::runtime_error("Unknown strategy: " + strategy_name);
    }
}

std::string EscapeJSON(const std::string& s) {
    std::ostringstream o;
    for (char c : s) {
        switch (c) {
            case '"': o << "\\\""; break;
            case '\\': o << "\\\\"; break;
            case '\b': o << "\\b"; break;
            case '\f': o << "\\f"; break;
            case '\n': o << "\\n"; break;
            case '\r': o << "\\r"; break;
            case '\t': o << "\\t"; break;
            default:
                if (c < 0x20) {
                    o << "\\u" << std::hex << std::setw(4) << std::setfill('0') << (int)c;
                } else {
                    o << c;
                }
        }
    }
    return o.str();
}

void WriteJSON(const BacktestResults& results, const std::string& output_file) {
    std::ofstream out(output_file);
    if (!out.is_open()) {
        throw std::runtime_error("Failed to open output file: " + output_file);
    }

    out << std::fixed << std::setprecision(6);
    out << "{\n";
    out << "  \"strategy_name\": \"" << EscapeJSON(results.strategy_name) << "\",\n";
    out << "  \"coin\": \"" << EscapeJSON(results.coin) << "\",\n";
    out << "  \"total_return_pct\": " << results.total_return_pct << ",\n";
    out << "  \"num_trades\": " << results.num_trades << ",\n";
    out << "  \"win_rate\": " << results.win_rate << ",\n";
    out << "  \"avg_profit_pct\": " << results.avg_profit_pct << ",\n";
    out << "  \"avg_loss_pct\": " << results.avg_loss_pct << ",\n";
    out << "  \"max_drawdown_pct\": " << results.max_drawdown_pct << ",\n";
    out << "  \"sharpe_ratio\": " << results.sharpe_ratio << ",\n";

    // Trades array
    out << "  \"trades\": [\n";
    for (size_t i = 0; i < results.trades.size(); i++) {
        const auto& trade = results.trades[i];
        out << "    {\n";
        out << "      \"coin\": \"" << EscapeJSON(trade.coin) << "\",\n";
        out << "      \"buy_time\": \"" << EscapeJSON(trade.buy_time) << "\",\n";
        out << "      \"sell_time\": \"" << EscapeJSON(trade.sell_time) << "\",\n";
        out << "      \"buy_price\": " << trade.buy_price << ",\n";
        out << "      \"sell_price\": " << trade.sell_price << ",\n";
        out << "      \"profit_pct\": " << trade.profit_pct << ",\n";
        out << "      \"peak_profit_pct\": " << trade.peak_profit_pct << ",\n";
        out << "      \"sell_reason\": \"" << EscapeJSON(trade.sell_reason) << "\",\n";
        out << "      \"hold_duration\": " << trade.hold_duration << "\n";
        out << "    }" << (i < results.trades.size() - 1 ? "," : "") << "\n";
    }
    out << "  ],\n";

    // Equity curve
    out << "  \"equity_curve\": [";
    for (size_t i = 0; i < results.equity_curve.size(); i++) {
        if (i > 0) out << ", ";
        out << results.equity_curve[i];
    }
    out << "]\n";

    out << "}\n";
    out.close();
}

void PrintResults(const BacktestResults& results) {
    std::cout << "\n========================================\n";
    std::cout << "BACKTEST RESULTS\n";
    std::cout << "========================================\n";
    std::cout << "Strategy: " << results.strategy_name << "\n";
    std::cout << "Coin: " << results.coin << "\n";
    std::cout << "----------------------------------------\n";
    std::cout << std::fixed << std::setprecision(2);
    std::cout << "Total Return: " << results.total_return_pct << "%\n";
    std::cout << "Number of Trades: " << results.num_trades << "\n";
    std::cout << "Win Rate: " << (results.win_rate * 100.0) << "%\n";
    std::cout << "Avg Profit: " << results.avg_profit_pct << "%\n";
    std::cout << "Avg Loss: " << results.avg_loss_pct << "%\n";
    std::cout << "Max Drawdown: " << results.max_drawdown_pct << "%\n";
    std::cout << "Sharpe Ratio: " << results.sharpe_ratio << "\n";
    std::cout << "========================================\n\n";

    if (!results.trades.empty()) {
        std::cout << "TRADES:\n";
        std::cout << "----------------------------------------\n";
        for (size_t i = 0; i < std::min(size_t(10), results.trades.size()); i++) {
            const auto& trade = results.trades[i];
            std::cout << "Trade #" << (i + 1) << ": ";
            std::cout << trade.buy_time << " -> " << trade.sell_time;
            std::cout << " | Profit: " << trade.profit_pct << "%";
            std::cout << " | Reason: " << trade.sell_reason << "\n";
        }
        if (results.trades.size() > 10) {
            std::cout << "... (" << (results.trades.size() - 10) << " more trades)\n";
        }
        std::cout << "========================================\n";
    }
}

int main(int argc, char* argv[]) {
    if (argc < 3) {
        std::cerr << "Usage: " << argv[0] << " <strategy> <data_csv> [coin_name] [--json output.json] [--param key=value ...]\n";
        std::cerr << "\nAvailable strategies:\n";
        std::cerr << "  ma_trailing       - Moving Averages with Trailing Stop\n";
        std::cerr << "  ma                - Simple Moving Averages\n";
        std::cerr << "  volatility        - Volatility Harvesting\n";
        std::cerr << "  sentiment         - Sentiment Momentum\n";
        std::cerr << "\nExample:\n";
        std::cerr << "  " << argv[0] << " ma_trailing /tmp/backtest_BTC.csv BTC\n";
        std::cerr << "  " << argv[0] << " ma_trailing /tmp/backtest_BTC.csv BTC --json results.json\n";
        std::cerr << "  " << argv[0] << " volatility /tmp/backtest_RNDR.csv RNDR --param bb_period=15 --param bb_std_dev=2.5\n";
        return 1;
    }

    std::string strategy_name = argv[1];
    std::string data_file = argv[2];
    std::string coin_name = (argc > 3 && std::string(argv[3]) != "--json" && std::string(argv[3]) != "--param") ? argv[3] : "UNKNOWN";

    // Parse flags
    std::string json_output;
    ParameterSet custom_params;

    for (int i = 3; i < argc; i++) {
        std::string arg = argv[i];

        if (arg == "--json" && i + 1 < argc) {
            json_output = argv[i + 1];
            i++;  // Skip next arg
        }
        else if (arg == "--param" && i + 1 < argc) {
            std::string param_str = argv[i + 1];
            i++;  // Skip next arg

            // Parse key=value
            size_t eq_pos = param_str.find('=');
            if (eq_pos != std::string::npos) {
                std::string key = param_str.substr(0, eq_pos);
                std::string value = param_str.substr(eq_pos + 1);

                // Try to parse as int first
                try {
                    size_t pos;
                    int int_val = std::stoi(value, &pos);
                    if (pos == value.length()) {
                        custom_params.set(key, int_val);
                        std::cout << "Parameter: " << key << " = " << int_val << " (int)\n";
                        continue;
                    }
                } catch (...) {}

                // Try to parse as double
                try {
                    size_t pos;
                    double double_val = std::stod(value, &pos);
                    if (pos == value.length()) {
                        custom_params.set(key, double_val);
                        std::cout << "Parameter: " << key << " = " << double_val << " (double)\n";
                        continue;
                    }
                } catch (...) {}

                // Store as string
                custom_params.set(key, value);
                std::cout << "Parameter: " << key << " = " << value << " (string)\n";
            }
        }
    }

    try {
        // Create strategy
        auto strategy = CreateStrategy(strategy_name);
        std::cout << "Running backtest for " << strategy->GetName() << " on " << coin_name << "...\n";

        // Apply custom parameters if provided
        if (!custom_params.int_params.empty() || !custom_params.double_params.empty() || !custom_params.string_params.empty()) {
            std::cout << "Applying custom parameters...\n";
            strategy->SetParameters(custom_params);
        }

        // Create backtester
        BacktestEngine engine;
        engine.SetStrategy(strategy);

        // Load data
        std::cout << "Loading data from " << data_file << "...\n";
        engine.LoadDataFromCSV(data_file, coin_name);

        // Run backtest
        std::cout << "Running backtest...\n";
        BacktestResults results = engine.Run();

        // Print results to console
        PrintResults(results);

        // Write JSON if requested
        if (!json_output.empty()) {
            std::cout << "\nWriting results to " << json_output << "...\n";
            WriteJSON(results, json_output);
            std::cout << "JSON output saved successfully.\n";
        }

        return 0;

    } catch (const std::exception& e) {
        std::cerr << "ERROR: " << e.what() << "\n";
        return 1;
    }
}
