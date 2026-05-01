using System;
using System.Collections.Generic;
using System.Linq;
using System.Net.Http;
using System.Security.Cryptography;
using System.Text;
using System.Text.Json;
using System.Threading.Tasks;
using KadirovQuantLab.Common.Models;

namespace KadirovQuantLab.Common.Exchange
{
    public class KrakenClient : IKrakenClient
    {
        private readonly string _apiKey;
        private readonly string _apiSecret;
        private readonly HttpClient _httpClient;
        private readonly bool _dryRun;

        private const string KrakenApiUrl = "https://api.kraken.com";
        private const double MANUAL_BUY_FEE = 0.0025;  // 0.25%
        private const double MANUAL_SELL_FEE = 0.0040; // 0.40%

        public KrakenClient(string apiKey, string apiSecret, HttpClient httpClient, bool dryRun = false)
        {
            _apiKey = apiKey;
            _apiSecret = apiSecret;
            _httpClient = httpClient;
            _dryRun = dryRun;
        }

        public async Task<Dictionary<string, object>> QueryPublicAsync(string method, Dictionary<string, string> parameters = null)
        {
            var url = $"{KrakenApiUrl}/0/public/{method}";

            if (parameters != null && parameters.Count > 0)
            {
                var queryString = string.Join("&", parameters.Select(kvp => $"{kvp.Key}={kvp.Value}"));
                url += $"?{queryString}";
            }

            var response = await _httpClient.GetStringAsync(url);
            return JsonSerializer.Deserialize<Dictionary<string, object>>(response);
        }

        public async Task<Dictionary<string, object>> QueryPrivateAsync(string method, Dictionary<string, string> parameters = null)
        {
            // In dry run mode, only mock AddOrder - fetch real data for everything else
            if (_dryRun && method == "AddOrder")
            {
                // Return mock order response for dry run
                var mockResult = new Dictionary<string, object>
                {
                    ["txid"] = new[] { $"DRY-RUN-{Guid.NewGuid().ToString().Substring(0, 8)}" }
                };

                return new Dictionary<string, object>
                {
                    ["error"] = JsonSerializer.SerializeToElement(new List<string>()),
                    ["result"] = JsonSerializer.SerializeToElement(mockResult)
                };
            }

            // For all other methods (including Balance), fetch real data from Kraken
            var url = $"{KrakenApiUrl}/0/private/{method}";
            var nonce = DateTimeOffset.UtcNow.ToUnixTimeMilliseconds().ToString();

            parameters = parameters ?? new Dictionary<string, string>();
            parameters["nonce"] = nonce;

            var postData = string.Join("&", parameters.Select(kvp => $"{kvp.Key}={kvp.Value}"));
            var path = $"/0/private/{method}";
            var message = nonce + postData;
            var sha256 = SHA256.Create().ComputeHash(Encoding.UTF8.GetBytes(message));
            var pathBytes = Encoding.UTF8.GetBytes(path);
            var combined = pathBytes.Concat(sha256).ToArray();
            var secretBytes = Convert.FromBase64String(_apiSecret);
            var signature = Convert.ToBase64String(new HMACSHA512(secretBytes).ComputeHash(combined));

            var request = new HttpRequestMessage(HttpMethod.Post, url);
            request.Headers.Add("API-Key", _apiKey);
            request.Headers.Add("API-Sign", signature);
            request.Content = new StringContent(postData, Encoding.UTF8, "application/x-www-form-urlencoded");

            var response = await _httpClient.SendAsync(request);
            var content = await response.Content.ReadAsStringAsync();

            // Check if response is valid JSON
            if (!response.IsSuccessStatusCode)
            {
                throw new Exception($"Kraken API HTTP {response.StatusCode}: {content}");
            }

            if (!content.StartsWith("{"))
            {
                throw new Exception($"Kraken API returned non-JSON response: {content}");
            }

            var result = JsonSerializer.Deserialize<Dictionary<string, object>>(content);

            // Check for Kraken API errors in the response
            if (result.ContainsKey("error"))
            {
                var errorElement = result["error"] as JsonElement?;
                if (errorElement.HasValue && errorElement.Value.GetArrayLength() > 0)
                {
                    var errors = new List<string>();
                    foreach (var err in errorElement.Value.EnumerateArray())
                    {
                        errors.Add(err.GetString() ?? "Unknown error");
                    }
                    throw new Exception($"Kraken API error: {string.Join(", ", errors)}");
                }
            }

            return result;
        }

        public async Task<double> GetBtcPriceAsync()
        {
            var response = await QueryPublicAsync("Ticker", new Dictionary<string, string> { ["pair"] = "XBTUSD" });
            var result = JsonSerializer.Deserialize<Dictionary<string, object>>(response["result"].ToString());

            var btcKey = result.Keys.FirstOrDefault(k => k.Contains("XBT"));
            if (btcKey == null) throw new Exception("BTC price not found");

            var tickerData = JsonSerializer.Deserialize<Dictionary<string, object>>(result[btcKey].ToString());
            var closePrice = JsonSerializer.Deserialize<List<string>>(tickerData["c"].ToString());
            return double.Parse(closePrice[0]);
        }

        public async Task<(double priceUsd, double priceBtc)> GetCurrentPriceAsync(string coin)
        {
            var pair = GetKrakenPair(coin);
            var response = await QueryPublicAsync("Ticker", new Dictionary<string, string> { ["pair"] = pair });

            var result = JsonSerializer.Deserialize<Dictionary<string, object>>(response["result"].ToString());
            var pairKey = result.Keys.FirstOrDefault(k => k != "last");

            if (pairKey == null)
                throw new Exception($"Price not found for {coin}");

            var tickerData = JsonSerializer.Deserialize<Dictionary<string, object>>(result[pairKey].ToString());
            var closePrice = JsonSerializer.Deserialize<List<string>>(tickerData["c"].ToString());
            var priceUsd = double.Parse(closePrice[0]);

            var btcPrice = await GetBtcPriceAsync();
            var priceBtc = priceUsd / btcPrice;

            return (priceUsd, priceBtc);
        }

        public async Task<double> FetchBalanceAsync()
        {
            // Fetch real balance even in dry run mode (for accurate testing)
            try
            {
                var response = await QueryPrivateAsync("Balance");
                var errors = response["error"] as JsonElement?;

                if (errors?.GetArrayLength() > 0)
                {
                    Console.WriteLine($"[ERROR] Failed to fetch balance: {errors}");
                    return 0.0;
                }

                var result = JsonSerializer.Deserialize<Dictionary<string, object>>(response["result"].ToString());

                // Get USD balance (ZUSD is Kraken's USD identifier)
                double usdBalance = 0.0;
                if (result.ContainsKey("ZUSD"))
                {
                    usdBalance = double.Parse(result["ZUSD"].ToString());
                }

                Console.WriteLine($"[BALANCE] Kraken USD Balance: ${usdBalance:F2}");
                return usdBalance;
            }
            catch (Exception ex)
            {
                Console.WriteLine($"[ERROR] Failed to fetch balance: {ex.Message}");
                return 0.0;
            }
        }

        public async Task<Dictionary<string, double>> FetchAllCoinBalancesAsync()
        {
            // Fetch real coin balances even in dry run mode (for accurate testing)
            try
            {
                var response = await QueryPrivateAsync("Balance");
                var errors = response["error"] as JsonElement?;

                if (errors?.GetArrayLength() > 0)
                {
                    Console.WriteLine($"[ERROR] Failed to fetch coin balances: {errors}");
                    return new Dictionary<string, double>();
                }

                var result = JsonSerializer.Deserialize<Dictionary<string, object>>(response["result"].ToString());
                var balances = new Dictionary<string, double>();
                var krakenToSymbol = GetKrakenAssetMapping();

                foreach (var kvp in result)
                {
                    var krakenAsset = kvp.Key;
                    var balance = double.Parse(kvp.Value.ToString());

                    if (balance > 0.00000001 && krakenToSymbol.ContainsKey(krakenAsset))
                    {
                        var symbol = krakenToSymbol[krakenAsset];
                        balances[symbol] = balance;
                    }
                }

                return balances;
            }
            catch (Exception ex)
            {
                Console.WriteLine($"[ERROR] Failed to fetch coin balances: {ex.Message}");
                return new Dictionary<string, double>();
            }
        }

        public async Task<List<Dictionary<string, object>>> FetchTradesHistoryAsync(string coin = null)
        {
            // Fetch real trade history even in dry run mode (for manual trade detection)
            try
            {
                var parameters = new Dictionary<string, string>
                {
                    ["trades"] = "true"
                };

                if (coin != null)
                {
                    var pair = GetKrakenPair(coin);
                    parameters["asset"] = pair;
                }

                var response = await QueryPrivateAsync("TradesHistory", parameters);
                var errors = response["error"] as JsonElement?;

                if (errors?.GetArrayLength() > 0)
                {
                    Console.WriteLine($"[ERROR] Failed to fetch trades history: {errors}");
                    return new List<Dictionary<string, object>>();
                }

                var resultElement = (JsonElement)response["result"];
                var result = JsonSerializer.Deserialize<Dictionary<string, object>>(resultElement.GetRawText());

                if (!result.ContainsKey("trades"))
                    return new List<Dictionary<string, object>>();

                var tradesDict = JsonSerializer.Deserialize<Dictionary<string, object>>(result["trades"].ToString());
                var trades = new List<Dictionary<string, object>>();

                foreach (var kvp in tradesDict)
                {
                    var tradeData = JsonSerializer.Deserialize<Dictionary<string, object>>(kvp.Value.ToString());
                    tradeData["txid"] = kvp.Key;
                    trades.Add(tradeData);
                }

                return trades;
            }
            catch (Exception ex)
            {
                Console.WriteLine($"[ERROR] Failed to fetch trades history: {ex.Message}");
                return new List<Dictionary<string, object>>();
            }
        }

        public async Task<(double price, double priceBtc, DateTime time)?> GetLastBuyTradeAsync(string coin)
        {
            try
            {
                var trades = await FetchTradesHistoryAsync();
                var pair = GetKrakenPair(coin);

                var buyTrades = trades
                    .Where(t => t.ContainsKey("type") && t["type"].ToString() == "buy")
                    .Where(t => t.ContainsKey("pair") && t["pair"].ToString().Contains(coin.ToUpper()))
                    .OrderByDescending(t => double.Parse(t["time"].ToString()))
                    .ToList();

                if (!buyTrades.Any())
                    return null;

                var lastBuy = buyTrades.First();
                var price = double.Parse(lastBuy["price"].ToString());
                var timestamp = double.Parse(lastBuy["time"].ToString());
                var time = DateTimeOffset.FromUnixTimeSeconds((long)timestamp).DateTime;

                var btcPrice = await GetBtcPriceAsync();
                var priceBtc = price / btcPrice;

                return (price, priceBtc, time);
            }
            catch (Exception ex)
            {
                Console.WriteLine($"[ERROR] Failed to get last buy trade for {coin}: {ex.Message}");
                return null;
            }
        }

        public async Task<List<OhlcCandle>> FetchOhlcDataAsync(string coin, int periodMinutes)
        {
            var pair = GetKrakenPair(coin);
            var intervalMinutes = 1;

            // Fetch last 7 days
            var since = new DateTimeOffset(DateTime.Now.AddDays(-7)).ToUnixTimeSeconds();

            var parameters = new Dictionary<string, string>
            {
                ["pair"] = pair,
                ["interval"] = intervalMinutes.ToString(),
                ["since"] = since.ToString()
            };

            var response = await QueryPublicAsync("OHLC", parameters);
            var result = JsonSerializer.Deserialize<Dictionary<string, object>>(response["result"].ToString());

            var dataKey = result.Keys.FirstOrDefault(k => k != "last");
            if (dataKey == null)
            {
                return new List<OhlcCandle>();
            }

            var ohlcData = JsonSerializer.Deserialize<List<List<object>>>(result[dataKey].ToString());
            var btcPrice = await GetBtcPriceAsync();

            var candles = new List<OhlcCandle>();
            foreach (var row in ohlcData)
            {
                var time = DateTimeOffset.FromUnixTimeSeconds(long.Parse(row[0].ToString())).DateTime;
                var close = double.Parse(row[4].ToString());

                candles.Add(new OhlcCandle
                {
                    Time = time,
                    Open = double.Parse(row[1].ToString()),
                    High = double.Parse(row[2].ToString()),
                    Low = double.Parse(row[3].ToString()),
                    Close = close,
                    Volume = double.Parse(row[6].ToString()),
                    CloseBtc = close / btcPrice
                });
            }

            return candles;
        }

        public async Task<string> PlaceMarketOrderAsync(string coin, string side, double quantity)
        {
            if (_dryRun)
            {
                return $"DRY_RUN_{Guid.NewGuid()}";
            }

            try
            {
                var pair = GetKrakenPair(coin);
                var orderParams = new Dictionary<string, string>
                {
                    ["pair"] = pair,
                    ["type"] = side,
                    ["ordertype"] = "market",
                    ["volume"] = quantity.ToString("F8")
                };

                var orderResponse = await QueryPrivateAsync("AddOrder", orderParams);
                var errors = orderResponse["error"] as JsonElement?;

                if (errors?.GetArrayLength() > 0)
                {
                    throw new Exception($"Order placement failed: {errors}");
                }

                var resultElement = (JsonElement)orderResponse["result"];
                var result = JsonSerializer.Deserialize<Dictionary<string, object>>(resultElement.GetRawText());

                if (!result.ContainsKey("txid"))
                    throw new Exception("Order ID not returned");

                var txidArray = JsonSerializer.Deserialize<List<string>>(result["txid"].ToString());
                return txidArray.First();
            }
            catch (Exception ex)
            {
                Console.WriteLine($"[ERROR] Failed to place {side} order for {coin}: {ex.Message}");
                throw;
            }
        }

        public async Task<(double cost, double fee, double quantity)?> QueryOrderDetailsAsync(string orderId, int maxRetries = 3)
        {
            for (int attempt = 0; attempt < maxRetries; attempt++)
            {
                await Task.Delay(attempt == 0 ? 2000 : 1500);

                try
                {
                    var orderQuery = await QueryPrivateAsync("QueryOrders", new Dictionary<string, string>
                    {
                        ["txid"] = orderId
                    });

                    var errors = orderQuery["error"] as JsonElement?;
                    if (errors?.GetArrayLength() > 0)
                    {
                        Console.WriteLine($"[WARNING] QueryOrders attempt {attempt + 1} returned error: {errors}");
                        continue;
                    }

                    var resultElement = (JsonElement)orderQuery["result"];
                    var result = JsonSerializer.Deserialize<Dictionary<string, object>>(resultElement.GetRawText());

                    if (!result.ContainsKey(orderId))
                    {
                        Console.WriteLine($"[WARNING] QueryOrders attempt {attempt + 1}: Order ID not found in response");
                        continue;
                    }

                    var orderInfo = JsonSerializer.Deserialize<Dictionary<string, object>>(result[orderId].ToString());

                    if (orderInfo.ContainsKey("cost") && orderInfo.ContainsKey("fee") && orderInfo.ContainsKey("vol_exec"))
                    {
                        var cost = double.Parse(orderInfo["cost"].ToString());
                        var fee = double.Parse(orderInfo["fee"].ToString());
                        var quantity = double.Parse(orderInfo["vol_exec"].ToString());
                        return (cost, fee, quantity);
                    }
                }
                catch (Exception queryEx)
                {
                    Console.WriteLine($"[WARNING] QueryOrders attempt {attempt + 1} failed: {queryEx.Message}");
                }
            }

            // Fallback: return null to signal failure
            return null;
        }

        private string GetKrakenPair(string coin)
        {
            var mapping = new Dictionary<string, string>
            {
                ["BTC"] = "XBTUSD",
                ["ETH"] = "ETHUSD",
                ["SOL"] = "SOLUSD",
                ["ADA"] = "ADAUSD",
                ["DOT"] = "DOTUSD",
                ["LINK"] = "LINKUSD",
                ["UNI"] = "UNIUSD",
                ["ATOM"] = "ATOMUSD",
                ["AAVE"] = "AAVEUSD",
                ["SNX"] = "SNXUSD",
                ["CRV"] = "CRVUSD",
                ["GRT"] = "GRTUSD",
                ["FIL"] = "FILUSD",
                ["ICP"] = "ICPUSD",
                ["NEAR"] = "NEARUSD",
                ["FET"] = "FETUSD",
                ["RENDER"] = "RENDERUSD",
                ["OP"] = "OPUSD",
                ["STX"] = "STXUSD",
                ["MINA"] = "MINAUSD",
                ["FLOW"] = "FLOWUSD",
                ["ENJ"] = "ENJUSD",
                ["BAT"] = "BATUSD",
                ["STORJ"] = "STORJUSD",
                ["TRX"] = "TRXUSD",
                ["TON"] = "TONUSD",
                ["SUI"] = "SUIUSD",
                ["ONDO"] = "ONDOUSD",
                ["PAXG"] = "PAXGUSD",
                ["USDT"] = "USDTUSD",
                ["DAI"] = "DAIUSD"
            };

            return mapping.ContainsKey(coin) ? mapping[coin] : $"{coin}USD";
        }

        private Dictionary<string, string> GetKrakenAssetMapping()
        {
            return new Dictionary<string, string>
            {
                ["XXBT"] = "BTC",
                ["XETH"] = "ETH",
                ["SOL"] = "SOL",
                ["ADA"] = "ADA",
                ["DOT"] = "DOT",
                ["LINK"] = "LINK",
                ["UNI"] = "UNI",
                ["ATOM"] = "ATOM",
                ["AAVE"] = "AAVE",
                ["SNX"] = "SNX",
                ["CRV"] = "CRV",
                ["GRT"] = "GRT",
                ["FIL"] = "FIL",
                ["ICP"] = "ICP",
                ["NEAR"] = "NEAR",
                ["FET"] = "FET",
                ["RENDER"] = "RENDER",
                ["OP"] = "OP",
                ["STX"] = "STX",
                ["MINA"] = "MINA",
                ["FLOW"] = "FLOW",
                ["ENJ"] = "ENJ",
                ["BAT"] = "BAT",
                ["STORJ"] = "STORJ",
                ["TRX"] = "TRX",
                ["TON"] = "TON",
                ["SUI"] = "SUI",
                ["ONDO"] = "ONDO",
                ["PAXG"] = "PAXG",
                ["USDT"] = "USDT",
                ["DAI"] = "DAI"
            };
        }
    }
}
