using System;

namespace KadirovQuantLab.Common.Models
{
    public class TickerUpdateEvent
    {
        public string Symbol { get; set; }
        public double BidPrice { get; set; }
        public double AskPrice { get; set; }
        public double LastPrice { get; set; }
        public double Volume24h { get; set; }
        public DateTime Timestamp { get; set; }
    }
}
