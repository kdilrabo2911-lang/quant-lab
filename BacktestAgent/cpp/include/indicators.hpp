#pragma once

#include <vector>
#include <cmath>

#ifdef __AVX2__
#include <immintrin.h>
#endif

namespace backtest {
namespace indicators {

// Simple Moving Average - SIMD optimized when possible
std::vector<double> sma(const std::vector<double>& prices, int period);

// Exponential Moving Average
std::vector<double> ema(const std::vector<double>& prices, int period);

// Bollinger Bands
struct BollingerBands {
    std::vector<double> upper;
    std::vector<double> middle;
    std::vector<double> lower;
};

BollingerBands bollinger_bands(const std::vector<double>& prices, int period, double std_dev_multiplier = 2.0);

// Rate of Change (Momentum)
std::vector<double> roc(const std::vector<double>& prices, int period);

// Volume Moving Average
std::vector<double> volume_ma(const std::vector<double>& volumes, int period);

// Standard Deviation
std::vector<double> std_dev(const std::vector<double>& prices, int period);

} // namespace indicators
} // namespace backtest
