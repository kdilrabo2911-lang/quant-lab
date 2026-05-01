#ifndef RNDR_DIPBUYER_H
#define RNDR_DIPBUYER_H

#include "../include/strategy_interface.h"
#include "../include/types.h"
#include <vector>
#include <string>
#include <nlohmann/json.hpp>

/**
 * RNDR_DipBuyer Strategy
 *
 * Description:
 * Buy when price is below the 1-day moving average AND price has dropped 2.5% from the previous closed position. Allow multiple concurrent positions only if price drops another 2.5% from the previous open position. Sell when price reaches 2.5% profit target. Never sell at a loss. MA line is the moving average for the last 1 day (optimizable later). Coin: RNDR.
 */
class RNDR_DipBuyer : public StrategyInterface {
private:
    // Configurable parameters


    // Indicators cache
    std::vector<double> rsi_values_;
    std::vector<double> sma_values_;
    std::vector<double> volume_avg_;

    // Helper methods
    void ComputeIndicators(const std::vector<Candle>& candles);
    double ComputeRSI(const std::vector<Candle>& candles, int period);
    double ComputeSMA(const std::vector<Candle>& candles, int period);
    double ComputeVolumeAvg(const std::vector<Candle>& candles, int period);

public:
    RNDR_DipBuyer(const nlohmann::json& params);

    bool ShouldBuy(const MarketData& data) override;
    bool ShouldSell(const Position& position, const MarketData& data) override;

    std::string GetName() const override { return "RNDR_DipBuyer"; }
};

#endif // RNDR_DIPBUYER_H
