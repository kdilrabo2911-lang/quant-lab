using System;
using System.Collections.Generic;
using System.Threading.Tasks;
using KadirovQuantLab.Common.Models;

namespace KadirovQuantLab.Common.Exchange
{
    public interface IKrakenWebSocketClient
    {
        event Action<TickerUpdateEvent> OnTickerUpdate;
        event Action<string> OnError;
        event Action OnConnected;
        event Action OnDisconnected;

        Task ConnectAsync();
        Task SubscribeToTickersAsync(List<string> symbols);
        Task UnsubscribeFromTickersAsync(List<string> symbols);
        Task DisconnectAsync();
        bool IsConnected { get; }
    }
}
