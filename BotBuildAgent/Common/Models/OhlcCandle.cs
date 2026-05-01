using System;

namespace KadirovQuantLab.Common.Models
{
    public class OhlcCandle
    {
        public DateTime Time { get; set; }
        public double Open { get; set; }
        public double High { get; set; }
        public double Low { get; set; }
        public double Close { get; set; }
        public double Volume { get; set; }
        public double CloseBtc { get; set; }
    }
}
