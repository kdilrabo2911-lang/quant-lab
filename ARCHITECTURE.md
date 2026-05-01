# Complete System Architecture

Kadirov Quant Lab is a hierarchical multi-agent framework that transforms static trading models into self-evolving strategies through a continuous improvement cycle. Specialized AI agents autonomously audit live performance against deep historical data, self-correcting logic in real-time to navigate shifting market regimes. A Human-in-the-Loop layer translates qualitative insights into rigorous mathematical constraints, allowing the AI and manager to co-evolve. By unifying research, backtesting, code generation, and live execution into a single agentic workflow, the Lab ensures every iteration remains mathematically precise and risk-compliant.

---

## Agent Overview

The system consists of 7 specialized AI agents, each with distinct responsibilities:

### **1. DataAgent - Market Data Infrastructure**

**Role**: Single source of truth for all market data (historical and live)

**Capabilities:**
- Stores 11M+ OHLC candles across 40 cryptocurrencies
- Provides REST API for historical data queries
- Streams real-time prices via WebSocket
- Fetches from Kraken every 5 minutes with auto-deduplication
- Maintains PostgreSQL database in cloud (DigitalOcean)

**Used By**: All agents - provides data foundation for backtesting, live trading, and analysis

---

### **2. CommunicationAgent - User Interface**

**Role**: Natural language interface between human manager and the system

**Capabilities:**
- Telegram bot with Claude-powered natural language understanding
- Translates manager requests into system actions
- Self-healing: Auto-debugs errors with 5-minute retry loop
- Routes commands to appropriate agents
- Provides real-time status updates and alerts

**Key Feature**: Manager can control entire system via simple Telegram messages

---

### **3. MasterAgent - Central Orchestrator & AI Brain**

**Role**: Core intelligence coordinating all system operations

**Capabilities:**
- **Strategy Management**: Stores and versions all strategies in PostgreSQL (single source of truth)
- **AI Code Generation**: Translates human ideas into executable code (Python → C++/C#)
- **Deployment Pipeline**: Validates, compiles, and deploys strategies automatically
- **Parameter Optimization**: Grid search across 27+ parameter combinations to find optimal settings
- **Portfolio Coordination**: Manages capital allocation across multiple strategies
- **Decision Intelligence**: Analyzes market events, evaluates risk, recommends actions
- **Learning System**: Stores every decision, outcome, and lesson learned for future pattern recognition

**Key Feature**: Acts as the "brain" - coordinates all other agents and makes strategic decisions

---

### **4. MarketMonitor - Real-Time Market Watcher**

**Role**: 24/7 market surveillance and anomaly detection

**Capabilities:**
- **Continuous Analysis**:
  - Price movements (BTC, altcoins)
  - Volume spikes and drops
  - Volatility regime changes
  - Cross-asset correlations
  - Portfolio health metrics
  - Strategy performance tracking

- **Event Detection**:
  - Flash crashes and rapid drawdowns
  - Major rallies and breakouts
  - Correlation breaks (e.g., BTC/ETH decoupling)
  - Strategy failures (consecutive losses)
  - Profit opportunities (lag patterns, mean reversion)

- **Intelligent Alerting**:
  - Classifies events by severity (LOW/MEDIUM/HIGH/CRITICAL)
  - Alerts manager via Telegram with AI analysis
  - Auto-executes in critical situations if manager unavailable
  - Provides confidence scores and recommendations

- **Autonomous Actions**:
  - **Non-Critical**: Alert and wait for manager decision
  - **Critical**: Act immediately (e.g., -20% drawdown + broken strategy = auto-exit)
  - **Learning**: Every decision logged - builds pattern recognition over time

**Key Feature**: The system's "eyes and ears" - never sleeps, always watching the market

---

### **5. BacktestAgent - High-Performance Validation Engine**

**Role**: Validates strategies on historical data before live deployment

**Capabilities:**
- **C++ Engine**: 100x faster than Python (SIMD-optimized indicator calculations)
- **Comprehensive Testing**: Runs strategies on months/years of historical data
- **Metrics Calculation**:
  - Total return, Sharpe ratio, win rate
  - Maximum drawdown, average profit/loss
  - Trade count, hold duration distribution
- **Grid Search Optimization**: Tests 27+ parameter combinations to find best settings
- **Database Storage**: All results saved to PostgreSQL for comparison and analysis

**Workflow**:
1. Receives strategy from MasterAgent
2. Generates optimized C++ code
3. Runs on historical data (e.g., TRX 90 days = 21,559 candles)
4. Calculates performance metrics
5. Returns results for manager approval

**Key Feature**: Ensures strategies are profitable BEFORE risking real money

---

### **6. BotBuildAgent - Live Trading Deployment**

**Role**: Generates and deploys live trading bots for approved strategies

**Capabilities:**
- **C# Bot Generation**: Creates production-ready .NET trading bots
- **Dual-Mode Deployment**:
  - **Paper Trading** (Dry-run): Simulates trades without real money, same logic
  - **Live Trading**: Real money execution on Kraken exchange
- **Order Execution**: Unified OrderExecutor handles buy/sell for all strategies
- **Risk Management**:
  - Position limits (max 1 position per coin per strategy)
  - Capital allocation (configurable % per strategy)
  - Stop-loss and profit targets
- **Strategy Attribution**: Every trade tagged with strategy name for performance tracking
- **Safety Features**:
  - Dry-run by default
  - Explicit `--live` flag + "YES" confirmation required
  - Separate data files for paper vs live (no confusion possible)

**Workflow**:
1. Receives approved strategy from MasterAgent
2. Generates C# bot with strategy-specific signal logic
3. Deploys to paper trading for validation (7+ days)
4. Manager approves → Switches to live trading
5. Logs every trade to PostgreSQL

**Key Feature**: Bridge between backtest validation and real money execution

---

### **7. Decision Logger - Learning System**

**Role**: Memory and pattern recognition engine

**Capabilities:**
- **Comprehensive Logging**: Stores every event, decision, and outcome
  - Market events (flash crashes, rallies, drawdowns)
  - AI suggestions (with confidence scores)
  - Manager decisions (agrees, overrides, silent)
  - Outcomes (win/loss, P/L, duration)
  - Lessons learned (what worked, what didn't)

- **Pattern Recognition**:
  - After 3+ similar events, recognizes patterns
  - Proactive suggestions: "I've seen this before, here's what worked..."
  - Learns from manager overrides: "Last time you were right, applying same logic now"

- **Context Retrieval**:
  - AI references past decisions in real-time
  - Example: "Flash crash detected (similar to April 15). Last time we held and were right. Hold again?"

**Key Feature**: The system gets smarter over time - every decision improves future performance

---

## Complete System Workflow

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         KADIROV QUANT LAB                               │
│                   Autonomous Hedge Fund System                          │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                    ┌───────────────┴───────────────┐
                    │                               │
            ┌───────▼────────┐            ┌────────▼────────┐
            │  DataAgent     │            │CommunicationAgent│
            │  (Data Layer)  │            │ (User Interface) │
            │                │            │                  │
            │ • 11M+ Candles │            │ • Telegram Bot   │
            │ • 40 Coins     │            │ • Claude NLU     │
            │ • REST API     │            │ • Self-Healing   │
            │ • WebSocket    │            │ • Auto-Debug     │
            └───────┬────────┘            └────────┬─────────┘
                    │                              │
       ┌────────────┼──────────────────────────────┼──────────────┐
       │            │                              │              │
       │   ┌────────▼────────┐                     │              │
       │   │  PostgreSQL DB  │◄────────────────────┤              │
       │   │  (Cloud)        │                     │              │
       │   │                 │                     │              │
       │   │ • Strategies    │                     │              │
       │   │ • Backtests     │                     │              │
       │   │ • Live Trades   │              ┌──────▼──────┐       │
       │   │ • Decisions Log │              │  Manager    │       │
       │   └────────┬────────┘              │ (Telegram)  │       │
       │            │                       └──────┬──────┘       │
       │   ┌────────▼────────┐                     │              │
       │   │  Kraken API     │                     │              │
       │   │  (Live Feed)    │                     │              │
       │   └────────┬────────┘                     │              │
       │            │                              │              │
       │            │         ┌────────────────────▼──────────────▼─────┐
       │            │         │          MasterAgent                     │
       │            │         │       (Central Orchestrator)             │
       │            │         │                                          │
       │            │         │  • Strategy Management                   │
       │            │         │  • Code Generation                       │
       │            │         │  • Deployment Pipeline                   │
       │            │         │  • Optimization Engine                   │
       │            │         │  • Portfolio Management                  │
       │            │         └────┬─────────────┬─────────────┬─────────┘
       │            │              │             │             │
       │            │    ┌─────────▼──┐   ┌──────▼──────┐   ┌─▼───────────────┐
       │            │    │MarketMonitor│  │BacktestAgent│   │  BotBuildAgent  │
       │            │    │             │  │(C++ Engine) │   │  (C# Bots)      │
       │            │    │             │  │             │   │                 │
       │            └───►│• 24/7 Watch │  │• Validate   │   │ • Deploy Paper  │
       │                 │• Detect     │  │• Optimize   │   │ • Deploy Live   │
       │                 │  Events     │  │• 100x Speed │   │ • Execute Trades│
       │                 │• Alert Mgr  │  │• SIMD       │   │ • Track P/L     │
       │                 │• Auto-Act   │  │             │   │                 │
       │                 │• Learn      │  │             │   │                 │
       │                 └──────┬──────┘  └──────┬──────┘   └─────┬───────────┘
       │                        │                │                │
       │                        │                │                │
       │         ┌──────────────┘                │                │
       │         │                               │                │
       │         │  ┌────────────────────────────┘                │
       │         │  │                                             │
       │         │  │                                      ┌──────▼──────┐
       │         │  │                                      │   Kraken    │
       │         │  │                                      │  Exchange   │
       │         │  │                                      │   (Live)    │
       │         │  │                                      └─────────────┘
       │         │  │
       │         ▼  ▼
       │   ┌──────────────────────┐
       │   │  Decision Logger     │
       │   │  (Learning System)   │
       │   │                      │
       │   │  Stores:             │
       │   │  • Market events     │
       │   │  • AI suggestions    │
       │   │  • Manager decisions │
       │   │  • Outcomes          │
       │   │  • Lessons learned   │
       │   └──────────────────────┘
       │
       └─────────────────────► Feeds back into MasterAgent
```

---

## Key Workflows

### **1. Strategy Development & Deployment**

```
Manager Idea (via Telegram)
    ↓
CommunicationAgent (translates to system command)
    ↓
MasterAgent (generates Python strategy code)
    ↓
Store in PostgreSQL Database
    ↓
Generate C++ Code for Backtesting
    ↓
BacktestAgent (validate on historical data)
    ├─► FAIL → Reject → Refine → Retry
    └─► PASS → Continue
         ↓
Optimization Engine (grid search 27+ parameter combos)
    ↓
Find Best Parameters
    ↓
Manager Approval?
    ├─► NO → Back to refinement
    └─► YES → Continue
         ↓
BotBuildAgent (generate C# trading bot)
    ↓
Deploy to Paper Trading (dry-run mode, 7+ days)
    ↓
Paper Trading Success?
    ├─► NO → Pause, analyze, refine
    └─► YES → Continue
         ↓
Manager Approval for Live?
    ├─► NO → Keep on paper
    └─► YES → Deploy Live
         ↓
Live Trading (real money on Kraken)
    ↓
Performance Tracking (every trade logged)
    ↓
Decision Logger (stores outcomes)
    ↓
Feedback Loop → Strategy Refinement
```

---

### **2. Real-Time Market Monitoring & Response**

```
Kraken API (live prices, volume, order books)
    ↓
DataAgent (store + stream)
    ↓
MarketMonitor (AI analysis every 5 minutes + real-time WebSocket)
    ↓
Event Detection & Classification
    ├─► Pattern Spotted (e.g., BTC leads alts by 2 hours)
    ├─► Major Drawdown (e.g., portfolio -15%)
    ├─► Flash Crash (e.g., -20% in 10 minutes)
    ├─► Strategy Failing (e.g., 5 consecutive losses)
    └─► Profit Opportunity (e.g., dip buying chance)
         ↓
Severity Analysis
    ├─► LOW: Alert manager, log event
    ├─► MEDIUM: Alert + AI suggestion, wait for manager
    ├─► HIGH: Urgent alert + AI evaluates cause
    └─► CRITICAL: Auto-act immediately, notify manager
         ↓
Manager Response?
    ├─► ACTIVE: Manager decides (AI gives opinion, manager final say)
    └─► SILENT: AI acts autonomously (if critical) OR monitors (if low risk)
         ↓
Execute Action
    • Buy/Sell orders
    • Adjust strategy parameters
    • Emergency exits
    • Take profits
         ↓
Decision Logger (stores event, decision, outcome)
    ↓
Pattern Recognition (learns for future events)
    ↓
Proactive Suggestions (e.g., "Create flash crash buyer strategy?")
    ↓
Feeds back to Strategy Development Workflow
```

---

### **3. The Recursive Learning Loop**

The system continuously improves through a feedback loop:

```
LIVE MARKET EVENT
    │
    ├─► MarketMonitor detects event (e.g., flash crash)
    ├─► AI analyzes and responds (e.g., holds positions)
    ├─► Outcome logged (e.g., market recovered, no losses)
    └─► Pattern recognized (e.g., "flash crashes recover in 15min")
         │
         ▼
INSIGHT GENERATED
    │
    ├─► AI suggests new strategy (e.g., "Create FlashCrashBuyer")
    ├─► Manager approves
    └─► MasterAgent generates strategy
         │
         ▼
STRATEGY DEVELOPMENT
    │
    ├─► BacktestAgent validates on historical data
    ├─► Optimization finds best parameters
    ├─► BotBuildAgent deploys to paper trading
    └─► Success → Deploy to live
         │
         ▼
IMPROVED PERFORMANCE
    │
    ├─► Next flash crash: New bot buys the dip
    ├─► Makes +18% profit in 20 minutes
    └─► Outcome logged, strategy refined further
         │
         └──► Loop repeats: Better strategies → Better performance → More learning
```

This cycle runs 24/7, making the system smarter with every market event.

---

## Decision Points & Autonomy Levels

### **Event Severity Classification**

| Severity | Example | Manager Alert | Auto-Execute |
|----------|---------|---------------|--------------|
| **LOW** | Pattern spotted, BTC rally | Yes (info only) | No |
| **MEDIUM** | -10% drawdown, strategy underperforming | Yes (suggestion) | No |
| **HIGH** | -15% drawdown with broken strategy | Yes (urgent) | After 30min silence |
| **CRITICAL** | -20% drawdown, flash crash defense | Yes (immediate) | Yes (notify after) |

### **Manager Availability States**

| Status | AI Behavior | Example |
|--------|-------------|---------|
| **ACTIVE** | AI gives opinion, manager decides | "BTC crashing. I think hold. Your call?" → Manager: "Exit!" → AI exits |
| **SILENT (Low Risk)** | AI monitors and logs | Pattern detected → Log it, alert manager later |
| **SILENT (High Risk)** | AI evaluates and auto-acts | -18% + broken strategy → Auto-exit, notify manager |

### **Strategy Approval Gates**

| Gate | Pass Criteria | Fail Action |
|------|---------------|-------------|
| **Backtest** | Return > 0%, Sharpe > 1.0, Trades > 5 | Reject → Refine logic |
| **Optimization** | Best params found, improved return | Use optimal settings |
| **Paper Trading** | 7+ days, Return > 0%, No errors | Deploy to live |
| **Live Trading** | Manager types "YES" + confirms | Require explicit approval |

---

## Safety Features

- **Dry-Run Default**: All bots start in simulation mode
- **Explicit Confirmation**: Live trading requires typing "YES"
- **Strategy Attribution**: Every trade tagged with strategy name
- **Placeholder Detection**: Validates generated code before deployment
- **Auto-Fix with Timeout**: 5-minute retry limit prevents infinite loops
- **Database Audit Trail**: All decisions, backtests, and trades logged
- **Position Limits**: Configurable per-strategy and per-coin limits
- **Capital Allocation**: Unified portfolio management prevents overexposure
- **Multi-Strategy Isolation**: Each strategy independent, clear separation

---

## Technology Stack

| Component | Technology | Purpose |
|-----------|-----------|---------|
| DataAgent | Python + FastAPI | Async I/O for WebSocket streams |
| BacktestAgent | C++ + Python | Speed-critical validation (100x faster) |
| BotBuildAgent | C# (.NET) | Production reliability, strong typing |
| MasterAgent | Python + Claude Opus 4.7 | Code generation, orchestration |
| CommunicationAgent | Python + Telegram Bot API | Natural language interface |
| MarketMonitor | Python + Claude Opus 4.7 | Real-time analysis, pattern recognition |
| Database | PostgreSQL (DigitalOcean) | Cloud-based, ACID compliance |
| Exchange | Kraken API | Live trading, historical data |

---

**Built by Dilrabo Kadirov**
*The first fully autonomous, collaborative "Hedge Fund in a Box"*
