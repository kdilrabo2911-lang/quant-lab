#include "rndr_dipbuyer.h"
#include <cmath>
#include <algorithm>
#include <numeric>

RNDR_DipBuyer::RNDR_DipBuyer(const nlohmann::json& params) {
    // Load configurable parameters from JSON

}

void RNDR_DipBuyer::ComputeIndicators(const std::vector<Candle>& candles) {
    // Pre-compute indicators for efficiency

    // RSI
    if (candles.size() > 0) {
        rsi_values_.clear();
        // Compute RSI for all candles (implementation details...)
    }

    // SMA
    if (candles.size() > 0) {
        sma_values_.clear();
        // Compute SMA for all candles (implementation details...)
    }

    // Volume Average
    if (candles.size() > 0) {
        volume_avg_.clear();
        // Compute volume average (implementation details...)
    }
}

bool RNDR_DipBuyer::ShouldBuy(const MarketData& data) {
    const auto& candles = data.candles;
    if (candles.size() < 50) {
        return false;  // Not enough data
    }

    // Compute indicators
    ComputeIndicators(candles);

    // Get current values
    double current_price = candles.back().close;
    double current_volume = candles.back().volume;

    return false;  // No conditions defined

}

bool RNDR_DipBuyer::ShouldSell(const Position& position, const MarketData& data) {
    const auto& candles = data.candles;
    if (candles.empty()) {
        return false;
    }

    // Compute indicators
    ComputeIndicators(candles);

    // Get current values
    double current_price = candles.back().close;
    double entry_price = position.entry_price;
    double profit_pct = ((current_price - entry_price) / entry_price) * 100.0;

    return false;  // No conditions defined

}

// Helper implementations
double RNDR_DipBuyer::ComputeRSI(const std::vector<Candle>& candles, int period) {
    if (candles.size() < period + 1) {
        return 50.0;  // Neutral
    }

    double gains = 0.0;
    double losses = 0.0;

    for (size_t i = candles.size() - period; i < candles.size(); ++i) {
        double change = candles[i].close - candles[i-1].close;
        if (change > 0) {
            gains += change;
        } else {
            losses += std::abs(change);
        }
    }

    double avg_gain = gains / period;
    double avg_loss = losses / period;

    if (avg_loss == 0.0) {
        return 100.0;
    }

    double rs = avg_gain / avg_loss;
    double rsi = 100.0 - (100.0 / (1.0 + rs));

    return rsi;
}

double RNDR_DipBuyer::ComputeSMA(const std::vector<Candle>& candles, int period) {
    if (candles.size() < period) {
        return candles.back().close;
    }

    double sum = 0.0;
    for (size_t i = candles.size() - period; i < candles.size(); ++i) {
        sum += candles[i].close;
    }

    return sum / period;
}

double RNDR_DipBuyer::ComputeVolumeAvg(const std::vector<Candle>& candles, int period) {
    if (candles.size() < period) {
        return candles.back().volume;
    }

    double sum = 0.0;
    for (size_t i = candles.size() - period; i < candles.size(); ++i) {
        sum += candles[i].volume;
    }

    return sum / period;
}
