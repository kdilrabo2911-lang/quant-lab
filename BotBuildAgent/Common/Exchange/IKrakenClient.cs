using System;
using System.Collections.Generic;
using System.Threading.Tasks;
using KadirovQuantLab.Common.Models;

namespace KadirovQuantLab.Common.Exchange
{
    public interface IKrakenClient
    {
        Task<Dictionary<string, object>> QueryPublicAsync(string method, Dictionary<string, string> parameters = null);
        Task<Dictionary<string, object>> QueryPrivateAsync(string method, Dictionary<string, string> parameters = null);
        Task<double> GetBtcPriceAsync();
        Task<(double priceUsd, double priceBtc)> GetCurrentPriceAsync(string coin);
        Task<double> FetchBalanceAsync();
        Task<Dictionary<string, double>> FetchAllCoinBalancesAsync();
        Task<List<Dictionary<string, object>>> FetchTradesHistoryAsync(string coin = null);
        Task<(double price, double priceBtc, DateTime time)?> GetLastBuyTradeAsync(string coin);
        Task<List<OhlcCandle>> FetchOhlcDataAsync(string coin, int periodMinutes);
        Task<string> PlaceMarketOrderAsync(string coin, string side, double quantity);
        Task<(double cost, double fee, double quantity)?> QueryOrderDetailsAsync(string orderId, int maxRetries = 3);
    }
}
