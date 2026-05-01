using System;
using System.Collections.Generic;
using System.Net.WebSockets;
using System.Text;
using System.Text.Json;
using System.Threading;
using System.Threading.Tasks;
using KadirovQuantLab.Common.Models;

namespace KadirovQuantLab.Common.Exchange
{
    public class KrakenWebSocketClient : IKrakenWebSocketClient
    {
        private ClientWebSocket _ws;
        private const string WsUrl = "wss://ws.kraken.com/v2";
        private CancellationTokenSource _cts;
        private bool _isConnected;

        public event Action<TickerUpdateEvent> OnTickerUpdate;
        public event Action<string> OnError;
        public event Action OnConnected;
        public event Action OnDisconnected;

        public bool IsConnected => _isConnected && _ws?.State == WebSocketState.Open;

        public async Task ConnectAsync()
        {
            if (IsConnected)
            {
                Console.WriteLine("[WS] Already connected");
                return;
            }

            try
            {
                _ws = new ClientWebSocket();
                _cts = new CancellationTokenSource();

                Console.WriteLine($"[WS] Connecting to {WsUrl}...");
                await _ws.ConnectAsync(new Uri(WsUrl), _cts.Token);

                _isConnected = true;
                Console.WriteLine("[WS] Connected successfully");
                OnConnected?.Invoke();

                // Start listening task
                _ = Task.Run(ListenAsync, _cts.Token);
            }
            catch (Exception ex)
            {
                Console.WriteLine($"[WS ERROR] Failed to connect: {ex.Message}");
                _isConnected = false;
                OnError?.Invoke($"Connection failed: {ex.Message}");
                throw;
            }
        }

        public async Task SubscribeToTickersAsync(List<string> symbols)
        {
            if (!IsConnected)
            {
                throw new InvalidOperationException("WebSocket is not connected");
            }

            try
            {
                var subscribeMsg = new
                {
                    method = "subscribe",
                    @params = new
                    {
                        channel = "ticker",
                        symbol = symbols,
                        snapshot = false,
                        event_trigger = "trades"
                    },
                    req_id = DateTimeOffset.UtcNow.ToUnixTimeMilliseconds()
                };

                var json = JsonSerializer.Serialize(subscribeMsg);
                Console.WriteLine($"[WS] Subscribing to {symbols.Count} tickers: {string.Join(", ", symbols)}");
                await SendMessageAsync(json);
            }
            catch (Exception ex)
            {
                Console.WriteLine($"[WS ERROR] Failed to subscribe: {ex.Message}");
                OnError?.Invoke($"Subscribe failed: {ex.Message}");
                throw;
            }
        }

        public async Task UnsubscribeFromTickersAsync(List<string> symbols)
        {
            if (!IsConnected)
            {
                return;
            }

            try
            {
                var unsubscribeMsg = new
                {
                    method = "unsubscribe",
                    @params = new
                    {
                        channel = "ticker",
                        symbol = symbols
                    },
                    req_id = DateTimeOffset.UtcNow.ToUnixTimeMilliseconds()
                };

                var json = JsonSerializer.Serialize(unsubscribeMsg);
                await SendMessageAsync(json);
            }
            catch (Exception ex)
            {
                Console.WriteLine($"[WS ERROR] Failed to unsubscribe: {ex.Message}");
                OnError?.Invoke($"Unsubscribe failed: {ex.Message}");
            }
        }

        public async Task DisconnectAsync()
        {
            if (_ws == null || _ws.State != WebSocketState.Open)
            {
                return;
            }

            try
            {
                Console.WriteLine("[WS] Disconnecting...");
                _cts?.Cancel();
                await _ws.CloseAsync(WebSocketCloseStatus.NormalClosure, "Client closing", CancellationToken.None);
                _isConnected = false;
                Console.WriteLine("[WS] Disconnected");
                OnDisconnected?.Invoke();
            }
            catch (Exception ex)
            {
                Console.WriteLine($"[WS ERROR] Disconnect error: {ex.Message}");
            }
            finally
            {
                _ws?.Dispose();
                _cts?.Dispose();
            }
        }

        private async Task SendMessageAsync(string message)
        {
            var bytes = Encoding.UTF8.GetBytes(message);
            await _ws.SendAsync(new ArraySegment<byte>(bytes), WebSocketMessageType.Text, true, _cts.Token);
        }

        private async Task ListenAsync()
        {
            var buffer = new byte[1024 * 16]; // 16KB buffer

            try
            {
                while (_ws.State == WebSocketState.Open && !_cts.Token.IsCancellationRequested)
                {
                    var result = await _ws.ReceiveAsync(new ArraySegment<byte>(buffer), _cts.Token);

                    if (result.MessageType == WebSocketMessageType.Close)
                    {
                        Console.WriteLine("[WS] Server initiated close");
                        await _ws.CloseAsync(WebSocketCloseStatus.NormalClosure, "Server closed", CancellationToken.None);
                        break;
                    }

                    var message = Encoding.UTF8.GetString(buffer, 0, result.Count);
                    ProcessMessage(message);
                }
            }
            catch (OperationCanceledException)
            {
                Console.WriteLine("[WS] Listen task cancelled");
            }
            catch (Exception ex)
            {
                Console.WriteLine($"[WS ERROR] Listen error: {ex.Message}");
                OnError?.Invoke($"Listen error: {ex.Message}");
            }
            finally
            {
                _isConnected = false;
                OnDisconnected?.Invoke();
            }
        }

        private void ProcessMessage(string message)
        {
            try
            {
                var json = JsonDocument.Parse(message);

                // Check if it's a method response (subscription confirmation)
                if (json.RootElement.TryGetProperty("method", out var method))
                {
                    if (method.GetString() == "subscribe" && json.RootElement.TryGetProperty("success", out var success))
                    {
                        if (success.GetBoolean())
                        {
                            Console.WriteLine("[WS] Subscription confirmed");
                        }
                        else
                        {
                            Console.WriteLine($"[WS ERROR] Subscription failed: {message}");
                            OnError?.Invoke($"Subscription failed: {message}");
                        }
                    }
                    return;
                }

                // Check if it's a ticker update
                if (json.RootElement.TryGetProperty("channel", out var channel) &&
                    channel.GetString() == "ticker" &&
                    json.RootElement.TryGetProperty("data", out var dataArray))
                {
                    foreach (var dataItem in dataArray.EnumerateArray())
                    {
                        var tickerEvent = ParseTickerData(dataItem);
                        if (tickerEvent != null)
                        {
                            OnTickerUpdate?.Invoke(tickerEvent);
                        }
                    }
                }
                // Check for heartbeat
                else if (json.RootElement.TryGetProperty("channel", out var hbChannel) &&
                         hbChannel.GetString() == "heartbeat")
                {
                    // Heartbeat - ignore silently
                }
                // Check for status messages
                else if (json.RootElement.TryGetProperty("channel", out var statusChannel) &&
                         statusChannel.GetString() == "status")
                {
                    Console.WriteLine($"[WS STATUS] {message}");
                }
            }
            catch (JsonException jsonEx)
            {
                Console.WriteLine($"[WS ERROR] Failed to parse message: {jsonEx.Message}");
                OnError?.Invoke($"Parse error: {jsonEx.Message}");
            }
            catch (Exception ex)
            {
                Console.WriteLine($"[WS ERROR] Message processing error: {ex.Message}");
                OnError?.Invoke($"Processing error: {ex.Message}");
            }
        }

        private TickerUpdateEvent ParseTickerData(JsonElement data)
        {
            try
            {
                if (!data.TryGetProperty("symbol", out var symbolProp))
                    return null;

                var tickerEvent = new TickerUpdateEvent
                {
                    Symbol = symbolProp.GetString(),
                    Timestamp = DateTime.UtcNow
                };

                // Parse last trade price
                if (data.TryGetProperty("last", out var lastProp))
                {
                    tickerEvent.LastPrice = lastProp.GetDouble();
                }

                // Parse bid price
                if (data.TryGetProperty("bid", out var bidProp))
                {
                    tickerEvent.BidPrice = bidProp.GetDouble();
                }

                // Parse ask price
                if (data.TryGetProperty("ask", out var askProp))
                {
                    tickerEvent.AskPrice = askProp.GetDouble();
                }

                // Parse 24h volume
                if (data.TryGetProperty("volume", out var volumeProp))
                {
                    tickerEvent.Volume24h = volumeProp.GetDouble();
                }

                return tickerEvent;
            }
            catch (Exception ex)
            {
                Console.WriteLine($"[WS ERROR] Failed to parse ticker data: {ex.Message}");
                return null;
            }
        }
    }
}
