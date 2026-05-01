-- Backtest Results Database Schema
-- Stores comprehensive backtest data including parameters, trades, and metrics

-- 1. Backtest Runs (portfolio-level)
CREATE TABLE IF NOT EXISTS backtest_runs (
    id SERIAL PRIMARY KEY,
    run_timestamp TIMESTAMP NOT NULL DEFAULT NOW(),
    strategy_name VARCHAR(100) NOT NULL,
    coins TEXT[] NOT NULL,  -- Array of coins tested
    start_date TIMESTAMP NOT NULL,
    end_date TIMESTAMP NOT NULL,
    period_days INTEGER NOT NULL,

    -- Portfolio-level metrics
    portfolio_total_return_pct DECIMAL(10, 4),
    portfolio_sharpe_ratio DECIMAL(10, 4),
    portfolio_max_drawdown_pct DECIMAL(10, 4),
    total_trades INTEGER,

    -- Strategy parameters (JSON)
    strategy_parameters JSONB,

    -- Metadata
    created_at TIMESTAMP DEFAULT NOW(),
    notes TEXT,

    CONSTRAINT backtest_runs_unique UNIQUE (run_timestamp, strategy_name, coins)
);

-- Index for faster queries
CREATE INDEX IF NOT EXISTS idx_backtest_runs_strategy ON backtest_runs(strategy_name);
CREATE INDEX IF NOT EXISTS idx_backtest_runs_timestamp ON backtest_runs(run_timestamp);
CREATE INDEX IF NOT EXISTS idx_backtest_runs_coins ON backtest_runs USING GIN(coins);


-- 2. Coin-level Results (individual coin performance within a backtest run)
CREATE TABLE IF NOT EXISTS backtest_coin_results (
    id SERIAL PRIMARY KEY,
    backtest_run_id INTEGER REFERENCES backtest_runs(id) ON DELETE CASCADE,
    coin VARCHAR(20) NOT NULL,

    -- Performance metrics
    total_return_pct DECIMAL(10, 4) NOT NULL,
    num_trades INTEGER NOT NULL,
    win_rate DECIMAL(5, 4) NOT NULL,
    avg_profit_pct DECIMAL(10, 4),
    avg_loss_pct DECIMAL(10, 4),
    max_drawdown_pct DECIMAL(10, 4),
    sharpe_ratio DECIMAL(10, 4),

    -- Equity curve (JSON array)
    equity_curve JSONB,

    -- Metadata
    created_at TIMESTAMP DEFAULT NOW(),

    CONSTRAINT backtest_coin_results_unique UNIQUE (backtest_run_id, coin)
);

-- Index for faster queries
CREATE INDEX IF NOT EXISTS idx_coin_results_run ON backtest_coin_results(backtest_run_id);
CREATE INDEX IF NOT EXISTS idx_coin_results_coin ON backtest_coin_results(coin);
CREATE INDEX IF NOT EXISTS idx_coin_results_return ON backtest_coin_results(total_return_pct);


-- 3. Trade Logs (individual trades from backtests)
CREATE TABLE IF NOT EXISTS backtest_trades (
    id SERIAL PRIMARY KEY,
    backtest_run_id INTEGER REFERENCES backtest_runs(id) ON DELETE CASCADE,
    coin_result_id INTEGER REFERENCES backtest_coin_results(id) ON DELETE CASCADE,
    coin VARCHAR(20) NOT NULL,

    -- Trade details
    buy_time TIMESTAMP NOT NULL,
    sell_time TIMESTAMP NOT NULL,
    buy_price DECIMAL(20, 8) NOT NULL,
    sell_price DECIMAL(20, 8) NOT NULL,

    -- Performance
    profit_pct DECIMAL(10, 4) NOT NULL,
    peak_profit_pct DECIMAL(10, 4),
    hold_duration INTEGER,  -- in candles/periods

    -- Trade metadata
    sell_reason VARCHAR(100),

    created_at TIMESTAMP DEFAULT NOW()
);

-- Indexes for faster queries
CREATE INDEX IF NOT EXISTS idx_trades_run ON backtest_trades(backtest_run_id);
CREATE INDEX IF NOT EXISTS idx_trades_coin_result ON backtest_trades(coin_result_id);
CREATE INDEX IF NOT EXISTS idx_trades_coin ON backtest_trades(coin);
CREATE INDEX IF NOT EXISTS idx_trades_profit ON backtest_trades(profit_pct);
CREATE INDEX IF NOT EXISTS idx_trades_buy_time ON backtest_trades(buy_time);


-- 4. View: Quick Summary of All Backtests
CREATE OR REPLACE VIEW backtest_summary AS
SELECT
    br.id,
    br.run_timestamp,
    br.strategy_name,
    br.coins,
    br.period_days,
    br.portfolio_total_return_pct,
    br.portfolio_sharpe_ratio,
    br.total_trades,
    COUNT(DISTINCT bcr.id) as num_coins,
    AVG(bcr.total_return_pct) as avg_coin_return_pct,
    MAX(bcr.total_return_pct) as best_coin_return_pct,
    MIN(bcr.total_return_pct) as worst_coin_return_pct
FROM backtest_runs br
LEFT JOIN backtest_coin_results bcr ON br.id = bcr.backtest_run_id
GROUP BY br.id, br.run_timestamp, br.strategy_name, br.coins,
         br.period_days, br.portfolio_total_return_pct,
         br.portfolio_sharpe_ratio, br.total_trades
ORDER BY br.run_timestamp DESC;


-- Comments
COMMENT ON TABLE backtest_runs IS 'Portfolio-level backtest runs with overall performance metrics';
COMMENT ON TABLE backtest_coin_results IS 'Individual coin performance within each backtest run';
COMMENT ON TABLE backtest_trades IS 'Detailed trade logs from backtests';
COMMENT ON COLUMN backtest_runs.strategy_parameters IS 'JSON object containing strategy-specific parameters';
COMMENT ON COLUMN backtest_coin_results.equity_curve IS 'JSON array of equity values over time';
