#!/bin/bash
# Build all strategy bots

set -e  # Exit on first error

echo "=========================================="
echo "  Building BotBuildAgent Strategies"
echo "=========================================="
echo ""

echo "[1/4] Building Common module..."
dotnet build Common/Common.csproj
echo "✓ Common built successfully"
echo ""

echo "[2/4] Building MovingAverages bot..."
dotnet build Strategies/MovingAverages/bot.csproj
echo "✓ MovingAverages built successfully"
echo ""

echo "[3/4] Building VolatilityHarvesting bot..."
dotnet build Strategies/VolatilityHarvesting/bot.csproj
echo "✓ VolatilityHarvesting built successfully"
echo ""

echo "[4/4] Building SentimentMomentum bot..."
dotnet build Strategies/SentimentMomentum/bot.csproj
echo "✓ SentimentMomentum built successfully"
echo ""

echo "=========================================="
echo "  All strategies built successfully!"
echo "=========================================="
echo ""
echo "To run a strategy:"
echo "  cd Strategies/MovingAverages && dotnet run"
echo "  cd Strategies/VolatilityHarvesting && dotnet run"
echo "  cd Strategies/SentimentMomentum && dotnet run"
echo ""
echo "For live trading (use with caution):"
echo "  dotnet run -- --live"
echo ""
