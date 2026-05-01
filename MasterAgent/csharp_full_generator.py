"""
Full C# Code Generator - Generates complete, working C# trading bot code
"""

from pathlib import Path
from typing import Dict
from strategy_definition import StrategyDefinition


class FullCSharpGenerator:
    """Generates complete, production-ready C# code for custom strategies"""

    def generate(self, strategy: StrategyDefinition, output_dir: Path = None) -> Dict[str, str]:
        """Generate all required C# files for a strategy

        Returns:
            Dict with filenames and complete code content
        """
        files = {}

        # 1. Program.cs - Entry point
        files["Program.cs"] = self._generate_program(strategy)

        # 2. TradingBot.cs - Main bot logic
        files["TradingBot.cs"] = self._generate_trading_bot(strategy)

        # 3. Models/{Strategy}Parameters.cs
        files[f"Models/{strategy.name}Parameters.cs"] = self._generate_parameters_class(strategy)

        # 4. Signals/IBuySignalGenerator.cs
        files["Signals/IBuySignalGenerator.cs"] = self._generate_buy_interface(strategy.name)

        # 5. Signals/ISellSignalGenerator.cs
        files["Signals/ISellSignalGenerator.cs"] = self._generate_sell_interface(strategy.name)

        # 6. Signals/BuySignalGenerator.cs
        files["Signals/BuySignalGenerator.cs"] = self._generate_buy_signal_generator(strategy)

        # 7. Signals/SellSignalGenerator.cs
        files["Signals/SellSignalGenerator.cs"] = self._generate_sell_signal_generator(strategy)

        # Write to disk if output_dir provided
        if output_dir:
            output_dir = Path(output_dir)
            output_dir.mkdir(parents=True, exist_ok=True)

            for filename, content in files.items():
                filepath = output_dir / filename

                # Create subdirectories if needed
                filepath.parent.mkdir(parents=True, exist_ok=True)

                with open(filepath, 'w') as f:
                    f.write(content)
                print(f"✅ Generated: {filepath}")

        return files

    def _generate_program(self, strategy: StrategyDefinition) -> str:
        """Generate Program.cs - Entry point"""
        return f'''using System;
using System.Collections.Generic;
using System.IO;
using System.Net.Http;
using System.Threading.Tasks;
using KadirovQuantLab.Common.Exchange;
using KadirovQuantLab.Common.Execution;
using KadirovQuantLab.Common.Portfolio;
using KadirovQuantLab.Common.Utilization;
using KadirovQuantLab.Common.DataAgent;
using KadirovQuantLab.Common.Models;
using KadirovQuantLab.Strategies.{strategy.name}.Signals;
using KadirovQuantLab.Strategies.{strategy.name}.Models;

namespace KadirovQuantLab.Strategies.{strategy.name}
{{
    class Program
    {{
        static async Task Main(string[] args)
        {{
            Console.WriteLine("Kadirov Quant Lab - {strategy.name} Strategy");
            Console.WriteLine("===========================================\\n");

            // Load API credentials
            var secretsFile = "secrets.env";
            if (File.Exists(secretsFile))
            {{
                foreach (var line in File.ReadAllLines(secretsFile))
                {{
                    var trimmed = line.Trim();
                    if (string.IsNullOrEmpty(trimmed) || trimmed.StartsWith("#"))
                        continue;

                    var parts = trimmed.Split('=', 2);
                    if (parts.Length == 2)
                    {{
                        Environment.SetEnvironmentVariable(parts[0].Trim(), parts[1].Trim().Trim('"'));
                    }}
                }}
            }}

            var apiKey = Environment.GetEnvironmentVariable("KRAKEN_API_KEY") ?? "";
            var apiSecret = Environment.GetEnvironmentVariable("KRAKEN_API_SECRET") ?? "";

            // Determine mode
            var dryRun = true;
            if (args.Length > 0 && args[0] == "--live")
            {{
                Console.Write("WARNING: Live trading mode will place real orders.\\nType 'YES' to confirm: ");
                var confirm = Console.ReadLine();
                if (confirm == "YES")
                {{
                    dryRun = false;
                    Console.WriteLine("Live trading enabled.\\n");
                }}
                else
                {{
                    Console.WriteLine("Cancelled. Running in dry-run mode.\\n");
                }}
            }}
            else
            {{
                Console.WriteLine("Running in DRY RUN mode (use --live for real trading)\\n");
            }}

            // Load parameters
            var coinParameters = LoadParameters();
            Console.WriteLine($"Loaded parameters for {{coinParameters.Count}} coins");

            // Initialize dependencies
            var httpClient = new HttpClient();
            var krakenClient = new KrakenClient(apiKey, apiSecret, httpClient, dryRun);
            var krakenWs = new KrakenWebSocketClient();
            var dataAgent = new DataAgentClient();

            // Initialize portfolio
            var portfolioState = await dataAgent.LoadPortfolioStateAsync();
            var portfolio = new PortfolioTracker(portfolioState, dryRun);

            // Initialize services
            var buySignals = new BuySignalGenerator(coinParameters);
            var sellSignals = new SellSignalGenerator(coinParameters);
            var capitalAllocator = new CapitalAllocator();
            var orderExecutor = new OrderExecutor(krakenClient, portfolio, dataAgent, dryRun);

            // Create and start bot
            var bot = new TradingBot(
                krakenClient,
                krakenWs,
                buySignals,
                sellSignals,
                orderExecutor,
                portfolio,
                capitalAllocator,
                dataAgent,
                coinParameters,
                dryRun);

            // Graceful shutdown
            Console.CancelKeyPress += async (sender, e) =>
            {{
                e.Cancel = true;
                await bot.StopAsync();
                Environment.Exit(0);
            }};

            await bot.StartAsync();
        }}

        static Dictionary<string, {strategy.name}Parameters> LoadParameters()
        {{
            // Default parameters
            var parameters = new Dictionary<string, {strategy.name}Parameters>();

            // Load from environment or use defaults
            var coins = (Environment.GetEnvironmentVariable("COINS") ?? "BTC").Split(',');

            foreach (var coin in coins)
            {{
                parameters[coin.Trim()] = new {strategy.name}Parameters
                {{
                    Coin = coin.Trim()
                    // Add default parameter values here
                }};
            }}

            return parameters;
        }}
    }}
}}
'''

    def _generate_trading_bot(self, strategy: StrategyDefinition) -> str:
        """Generate TradingBot.cs - Main bot logic"""
        return f'''using System;
using System.Collections.Generic;
using System.Linq;
using System.Threading;
using System.Threading.Tasks;
using KadirovQuantLab.Common.Exchange;
using KadirovQuantLab.Common.Execution;
using KadirovQuantLab.Common.Models;
using KadirovQuantLab.Common.Portfolio;
using KadirovQuantLab.Common.Utilization;
using KadirovQuantLab.Common.DataAgent;
using KadirovQuantLab.Strategies.{strategy.name}.Signals;
using KadirovQuantLab.Strategies.{strategy.name}.Models;

namespace KadirovQuantLab.Strategies.{strategy.name}
{{
    public class TradingBot
    {{
        private const string STRATEGY_NAME = "{strategy.name}";

        // Dependencies
        private readonly IKrakenClient _krakenClient;
        private readonly IKrakenWebSocketClient _krakenWs;
        private readonly IBuySignalGenerator _buySignals;
        private readonly ISellSignalGenerator _sellSignals;
        private readonly IOrderExecutor _orderExecutor;
        private readonly IPortfolioTracker _portfolio;
        private readonly ICapitalAllocator _capitalAllocator;
        private readonly IDataAgentClient _dataAgent;

        // State
        private List<Position> _positions = new List<Position>();
        private readonly Dictionary<string, {strategy.name}Parameters> _coinParameters;
        private double _btcPrice;
        private readonly bool _dryRun;
        private readonly SemaphoreSlim _tradeLock = new SemaphoreSlim(1, 1);

        // Candle history cache
        private readonly Dictionary<string, List<OhlcCandle>> _historicalCandles = new Dictionary<string, List<OhlcCandle>>();

        public TradingBot(
            IKrakenClient krakenClient,
            IKrakenWebSocketClient krakenWs,
            IBuySignalGenerator buySignals,
            ISellSignalGenerator sellSignals,
            IOrderExecutor orderExecutor,
            IPortfolioTracker portfolio,
            ICapitalAllocator capitalAllocator,
            IDataAgentClient dataAgent,
            Dictionary<string, {strategy.name}Parameters> coinParameters,
            bool dryRun = false)
        {{
            _krakenClient = krakenClient;
            _krakenWs = krakenWs;
            _buySignals = buySignals;
            _sellSignals = sellSignals;
            _orderExecutor = orderExecutor;
            _portfolio = portfolio;
            _capitalAllocator = capitalAllocator;
            _dataAgent = dataAgent;
            _coinParameters = coinParameters;
            _dryRun = dryRun;
        }}

        public async Task StartAsync()
        {{
            Console.WriteLine("==============================================");
            Console.WriteLine($"   {{STRATEGY_NAME.ToUpper()}} BOT");
            Console.WriteLine("==============================================");
            Console.WriteLine($"Mode: {{(_dryRun ? "DRY RUN" : "LIVE TRADING")}}");
            Console.WriteLine($"Coins: {{_coinParameters.Count}}");
            Console.WriteLine("==============================================\\n");

            // Load positions for this strategy
            _positions = await _dataAgent.LoadPositionsAsync(STRATEGY_NAME);
            _positions = _positions.Where(p => p.StrategyName == STRATEGY_NAME).ToList();
            Console.WriteLine($"[INIT] Loaded {{_positions.Count}} positions for {{STRATEGY_NAME}}");

            // Load portfolio state
            var portfolioState = await _dataAgent.LoadPortfolioStateAsync();
            _portfolio.UpdateBalance(_dryRun ? portfolioState.TotalBalanceDryRun : portfolioState.TotalBalance);
            Console.WriteLine($"[INIT] Portfolio Balance: ${{_portfolio.TotalBalance:F2}}");

            // Fetch initial BTC price
            _btcPrice = await _krakenClient.GetBtcPriceAsync();
            Console.WriteLine($"[INIT] BTC Price: ${{_btcPrice:F2}}\\n");

            // Load historical data
            Console.WriteLine("[INIT] Loading historical data...");
            foreach (var coin in _coinParameters.Keys)
            {{
                var candles = await _dataAgent.LoadHistoricalCandlesAsync(coin);
                if (candles.Count > 0)
                {{
                    _historicalCandles[coin] = candles;
                    Console.WriteLine($"  {{coin}}: {{candles.Count}} candles loaded");
                }}
            }}

            // Subscribe to WebSocket
            Console.WriteLine("\\n[WS] Subscribing to WebSocket...");
            _krakenWs.OnTickerUpdate += HandleTickerUpdate;
            await _krakenWs.ConnectAsync();
            await _krakenWs.SubscribeToTickersAsync(_coinParameters.Keys.ToList());

            Console.WriteLine($"\\n[{{STRATEGY_NAME}}] Bot running. Press Ctrl+C to stop.\\n");

            // Keep alive
            await Task.Delay(Timeout.Infinite);
        }}

        private async void HandleTickerUpdate(TickerUpdateEvent ticker)
        {{
            await _tradeLock.WaitAsync();
            try
            {{
                var coin = ticker.Symbol.Replace("/USD", "").Replace("/USDT", "");

                if (!_coinParameters.ContainsKey(coin))
                    return;

                // Update historical candles (append ticker as new candle)
                if (!_historicalCandles.ContainsKey(coin))
                {{
                    _historicalCandles[coin] = new List<OhlcCandle>();
                }}

                var newCandle = new OhlcCandle
                {{
                    Time = ticker.Timestamp,
                    Open = ticker.LastPrice,
                    High = ticker.LastPrice,
                    Low = ticker.LastPrice,
                    Close = ticker.LastPrice,
                    Volume = ticker.Volume24h,
                    CloseBtc = ticker.LastPrice / _btcPrice
                }};

                _historicalCandles[coin].Add(newCandle);

                // Keep only last 500 candles (memory limit)
                if (_historicalCandles[coin].Count > 500)
                {{
                    _historicalCandles[coin].RemoveAt(0);
                }}

                // Check sell signals first
                await CheckSellSignals(coin, ticker.LastPrice, newCandle.CloseBtc);

                // Check buy signals
                await CheckBuySignals(coin, ticker.LastPrice, newCandle.CloseBtc);

            }}
            finally
            {{
                _tradeLock.Release();
            }}
        }}

        private async Task CheckSellSignals(string coin, double currentPriceUsd, double currentPriceBtc)
        {{
            var coinPositions = _positions.Where(p => p.Coin == coin && p.StrategyName == STRATEGY_NAME).ToList();

            foreach (var position in coinPositions)
            {{
                // Update highest profit
                double profitPct = ((currentPriceUsd - position.BuyPrice) / position.BuyPrice) * 100.0;
                position.HighestProfitPct = Math.Max(position.HighestProfitPct, profitPct);

                var (shouldSell, reason) = await _sellSignals.ShouldSellAsync(position, currentPriceBtc, _historicalCandles[coin]);

                if (shouldSell)
                {{
                    Console.WriteLine($"[{{STRATEGY_NAME}}] [{{coin}}] SELL SIGNAL: {{reason}}");

                    // Execute sell
                    var trade = await _orderExecutor.ExecuteSellAsync(STRATEGY_NAME, position, currentPriceUsd, reason);

                    // Remove position
                    _positions.Remove(position);

                    // Save updated positions
                    await _dataAgent.SavePositionsAsync(STRATEGY_NAME, _positions);

                    Console.WriteLine($"[{{STRATEGY_NAME}}] [{{coin}}] Position closed. P/L: ${{trade.NetProfitUsd:F2}} ({{trade.ProfitPct:F2}}%)");
                }}
            }}
        }}

        private async Task CheckBuySignals(string coin, double currentPriceUsd, double currentPriceBtc)
        {{
            var shouldBuy = await _buySignals.ShouldBuyAsync(coin, currentPriceBtc, _positions, _historicalCandles[coin]);

            if (shouldBuy)
            {{
                Console.WriteLine($"[{{STRATEGY_NAME}}] [{{coin}}] BUY SIGNAL detected");

                // Calculate position size
                var availableCapital = _portfolio.GetAvailableBalance(_positions);
                var positionSize = _capitalAllocator.CalculatePositionSize(_portfolio.InitialBalance, availableCapital, _coinParameters.Count);

                if (positionSize < 10.0)
                {{
                    Console.WriteLine($"[{{STRATEGY_NAME}}] [{{coin}}] Insufficient capital: ${{availableCapital:F2}}");
                    return;
                }}

                // Execute buy
                var position = await _orderExecutor.ExecuteBuyAsync(STRATEGY_NAME, coin, currentPriceUsd, currentPriceBtc, positionSize);

                // Add position
                _positions.Add(position);

                // Save updated positions
                await _dataAgent.SavePositionsAsync(STRATEGY_NAME, _positions);

                Console.WriteLine($"[{{STRATEGY_NAME}}] [{{coin}}] Position opened: ${{positionSize:F2}}");
            }}
        }}

        public async Task StopAsync()
        {{
            Console.WriteLine($"\\n[{{STRATEGY_NAME}}] Stopping bot...");
            await _krakenWs.DisconnectAsync();
            Console.WriteLine($"[{{STRATEGY_NAME}}] Bot stopped.");
        }}
    }}
}}
'''

    def _generate_parameters_class(self, strategy: StrategyDefinition) -> str:
        """Generate Parameters class"""
        # Generate properties from strategy parameters
        properties = ["        public string Coin { get; set; } = string.Empty;"]

        for name, param in strategy.parameters.items():
            csharp_type = self._get_csharp_type(param.type)
            prop_name = self._to_pascal_case(name)
            properties.append(f"        public {csharp_type} {prop_name} {{ get; set; }} = {self._format_csharp_value(param.value, param.type)};")

        props_str = "\n".join(properties)

        return f'''using System;

namespace KadirovQuantLab.Strategies.{strategy.name}.Models
{{
    /// <summary>
    /// Configurable parameters for {strategy.name} strategy
    /// {strategy.description}
    /// </summary>
    public class {strategy.name}Parameters
    {{
{props_str}
    }}
}}
'''

    def _generate_buy_interface(self, strategy_name: str = "MA_Dip_Buyer") -> str:
        """Generate IBuySignalGenerator interface"""
        return f'''using System.Collections.Generic;
using System.Threading.Tasks;
using KadirovQuantLab.Common.Models;

namespace KadirovQuantLab.Strategies.{strategy_name}.Signals
{{
    public interface IBuySignalGenerator
    {{
        Task<bool> ShouldBuyAsync(string coin, double currentPriceBtc, List<Position> existingPositions, List<OhlcCandle> historicalCandles);
    }}
}}
'''

    def _generate_sell_interface(self, strategy_name: str = "MA_Dip_Buyer") -> str:
        """Generate ISellSignalGenerator interface"""
        return f'''using System.Collections.Generic;
using System.Threading.Tasks;
using KadirovQuantLab.Common.Models;

namespace KadirovQuantLab.Strategies.{strategy_name}.Signals
{{
    public interface ISellSignalGenerator
    {{
        Task<(bool shouldSell, string reason)> ShouldSellAsync(Position position, double currentPriceBtc, List<OhlcCandle> historicalCandles);
    }}
}}
'''

    def _generate_buy_signal_generator(self, strategy: StrategyDefinition) -> str:
        """Generate BuySignalGenerator with strategy-specific logic"""

        # For MA Dip Buyer strategy: Buy when price is below MA
        buy_logic = '''
            // Calculate moving average
            var ma = CalculateMA(historicalCandles, param.MaPeriod);
            if (double.IsNaN(ma))
                return Task.FromResult(false);

            // BUY SIGNAL: Price is below MA (dip detected)
            bool isPriceBelowMA = currentPriceBtc < ma;

            // Check if enough distance from last position (avoid buying too close)
            if (coinPositions.Any())
            {
                var lastPosition = coinPositions.Last();
                double distanceFromLast = ((currentPriceBtc - lastPosition.BuyPriceBtc) / lastPosition.BuyPriceBtc) * 100.0;

                // Only buy if price dropped at least DipThreshold% from last position
                if (distanceFromLast > -param.DipThresholdPct)
                    return Task.FromResult(false);
            }

            return Task.FromResult(isPriceBelowMA);'''

        return f'''using System;
using System.Collections.Generic;
using System.Linq;
using System.Threading.Tasks;
using KadirovQuantLab.Common.Models;
using KadirovQuantLab.Strategies.{strategy.name}.Models;

namespace KadirovQuantLab.Strategies.{strategy.name}.Signals
{{
    public class BuySignalGenerator : IBuySignalGenerator
    {{
        private readonly Dictionary<string, {strategy.name}Parameters> _parameters;
        private const int CANDLE_INTERVAL_MINUTES = 5;

        public BuySignalGenerator(Dictionary<string, {strategy.name}Parameters> parameters)
        {{
            _parameters = parameters;
        }}

        public Task<bool> ShouldBuyAsync(string coin, double currentPriceBtc, List<Position> existingPositions, List<OhlcCandle> historicalCandles)
        {{
            if (!_parameters.ContainsKey(coin))
                return Task.FromResult(false);

            var param = _parameters[coin];
            var coinPositions = existingPositions.Where(p => p.Coin == coin && p.StrategyName == "{strategy.name}").ToList();

            // Strategy-specific buy logic
{buy_logic}
        }}

        private double CalculateMA(List<OhlcCandle> candles, int periodMinutes)
        {{
            var periodsNeeded = periodMinutes / CANDLE_INTERVAL_MINUTES;

            if (candles.Count < periodsNeeded)
                return double.NaN;

            var recentCandles = candles.TakeLast(periodsNeeded);
            return recentCandles.Average(c => c.CloseBtc);
        }}
    }}
}}
'''

    def _generate_sell_signal_generator(self, strategy: StrategyDefinition) -> str:
        """Generate SellSignalGenerator with strategy-specific logic"""

        # For MA Dip Buyer: Sell at profit target
        sell_logic = '''
            var param = _parameters[position.Coin];

            // Calculate current profit
            double profitPct = ((currentPriceBtc - position.BuyPriceBtc) / position.BuyPriceBtc) * 100.0;

            // SELL SIGNAL: Hit profit target
            if (profitPct >= param.ProfitTargetPct)
            {
                return Task.FromResult((true, $"Profit target hit: {profitPct:F2}%"));
            }

            return Task.FromResult((false, ""));'''

        return f'''using System;
using System.Collections.Generic;
using System.Linq;
using System.Threading.Tasks;
using KadirovQuantLab.Common.Models;
using KadirovQuantLab.Strategies.{strategy.name}.Models;

namespace KadirovQuantLab.Strategies.{strategy.name}.Signals
{{
    public class SellSignalGenerator : ISellSignalGenerator
    {{
        private readonly Dictionary<string, {strategy.name}Parameters> _parameters;

        public SellSignalGenerator(Dictionary<string, {strategy.name}Parameters> parameters)
        {{
            _parameters = parameters;
        }}

        public Task<(bool shouldSell, string reason)> ShouldSellAsync(Position position, double currentPriceBtc, List<OhlcCandle> historicalCandles)
        {{
            if (!_parameters.ContainsKey(position.Coin))
                return Task.FromResult((false, ""));

            // Strategy-specific sell logic
{sell_logic}
        }}
    }}
}}
'''

    def _get_csharp_type(self, param_type: str) -> str:
        """Map parameter type to C# type"""
        type_map = {
            "int": "int",
            "float": "double",
            "string": "string",
            "bool": "bool"
        }
        return type_map.get(param_type, "double")

    def _format_csharp_value(self, value, param_type: str) -> str:
        """Format value for C# code"""
        if param_type == "string":
            return f'"{value}"'
        elif param_type == "bool":
            return "true" if value else "false"
        elif param_type == "float":
            return f"{value}"
        else:
            return str(value)

    def _to_pascal_case(self, snake_str: str) -> str:
        """Convert snake_case to PascalCase"""
        components = snake_str.split('_')
        return ''.join(x.title() for x in components)
