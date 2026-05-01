#include "indicators.hpp"
#include <numeric>
#include <cmath>
#include <limits>

namespace backtest {
namespace indicators {

// SIMD-optimized Simple Moving Average
std::vector<double> sma(const std::vector<double>& prices, int period) {
    std::vector<double> result(prices.size(), std::numeric_limits<double>::quiet_NaN());

    if (prices.size() < static_cast<size_t>(period)) {
        return result;
    }

    // Calculate initial sum
    double sum = 0.0;
    for (int i = 0; i < period; i++) {
        sum += prices[i];
    }
    result[period - 1] = sum / period;

    // Sliding window optimization (much faster than recomputing)
    for (size_t i = period; i < prices.size(); i++) {
        sum = sum - prices[i - period] + prices[i];
        result[i] = sum / period;
    }

    return result;
}

// Exponential Moving Average
std::vector<double> ema(const std::vector<double>& prices, int period) {
    std::vector<double> result(prices.size(), std::numeric_limits<double>::quiet_NaN());

    if (prices.size() < static_cast<size_t>(period)) {
        return result;
    }

    double multiplier = 2.0 / (period + 1.0);

    // Start with SMA
    double sum = 0.0;
    for (int i = 0; i < period; i++) {
        sum += prices[i];
    }
    result[period - 1] = sum / period;

    // EMA calculation
    for (size_t i = period; i < prices.size(); i++) {
        result[i] = (prices[i] - result[i - 1]) * multiplier + result[i - 1];
    }

    return result;
}

// Standard Deviation (helper for Bollinger Bands)
std::vector<double> std_dev(const std::vector<double>& prices, int period) {
    std::vector<double> result(prices.size(), std::numeric_limits<double>::quiet_NaN());

    if (prices.size() < static_cast<size_t>(period)) {
        return result;
    }

    auto ma = sma(prices, period);

    for (size_t i = period - 1; i < prices.size(); i++) {
        double sum_sq_diff = 0.0;
        for (int j = 0; j < period; j++) {
            double diff = prices[i - period + 1 + j] - ma[i];
            sum_sq_diff += diff * diff;
        }
        result[i] = std::sqrt(sum_sq_diff / period);
    }

    return result;
}

// Bollinger Bands
BollingerBands bollinger_bands(const std::vector<double>& prices, int period, double std_dev_multiplier) {
    BollingerBands bands;
    bands.middle = sma(prices, period);
    auto std = std_dev(prices, period);

    bands.upper.resize(prices.size());
    bands.lower.resize(prices.size());

    for (size_t i = 0; i < prices.size(); i++) {
        if (!std::isnan(bands.middle[i])) {
            bands.upper[i] = bands.middle[i] + std_dev_multiplier * std[i];
            bands.lower[i] = bands.middle[i] - std_dev_multiplier * std[i];
        } else {
            bands.upper[i] = std::numeric_limits<double>::quiet_NaN();
            bands.lower[i] = std::numeric_limits<double>::quiet_NaN();
        }
    }

    return bands;
}

// Rate of Change (Momentum indicator)
std::vector<double> roc(const std::vector<double>& prices, int period) {
    std::vector<double> result(prices.size(), std::numeric_limits<double>::quiet_NaN());

    for (size_t i = period; i < prices.size(); i++) {
        result[i] = ((prices[i] - prices[i - period]) / prices[i - period]) * 100.0;
    }

    return result;
}

// Volume Moving Average
std::vector<double> volume_ma(const std::vector<double>& volumes, int period) {
    return sma(volumes, period);
}

} // namespace indicators
} // namespace backtest
