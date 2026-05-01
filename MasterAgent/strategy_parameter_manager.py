"""Strategy Parameter Manager - Modify, optimize, and version strategy parameters"""

import json
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from datetime import datetime
from strategy_definition import StrategyDefinition, Parameter
import asyncio


class ParameterManager:
    """Manage strategy parameters: modify, optimize, version"""

    def __init__(self, strategies_dir: Path = None):
        self.strategies_dir = strategies_dir or Path("strategies")
        self.strategies_dir.mkdir(exist_ok=True)

    def save_strategy(self, strategy: StrategyDefinition) -> Path:
        """Save strategy definition to JSON file

        Returns:
            Path to saved file
        """
        strategy_dir = self.strategies_dir / strategy.name
        strategy_dir.mkdir(exist_ok=True)

        # Save with version
        filename = f"{strategy.name}_v{strategy.version}.json"
        filepath = strategy_dir / filename

        with open(filepath, 'w') as f:
            f.write(strategy.to_json())

        # Also save as "latest"
        latest_path = strategy_dir / f"{strategy.name}_latest.json"
        with open(latest_path, 'w') as f:
            f.write(strategy.to_json())

        print(f"✅ Saved strategy: {filepath}")
        return filepath

    def load_strategy(self, strategy_name: str, version: str = "latest") -> Optional[StrategyDefinition]:
        """Load strategy definition from file

        Args:
            strategy_name: Name of strategy
            version: Version number or "latest"

        Returns:
            StrategyDefinition or None if not found
        """
        strategy_dir = self.strategies_dir / strategy_name

        if version == "latest":
            filepath = strategy_dir / f"{strategy_name}_latest.json"
        else:
            filepath = strategy_dir / f"{strategy_name}_v{version}.json"

        if not filepath.exists():
            print(f"❌ Strategy not found: {filepath}")
            return None

        with open(filepath, 'r') as f:
            data = json.load(f)

        return StrategyDefinition.from_dict(data)

    def modify_parameters(self, strategy: StrategyDefinition,
                         param_changes: Dict[str, any]) -> StrategyDefinition:
        """Modify strategy parameters

        Args:
            strategy: Current strategy
            param_changes: Dict of parameter name -> new value

        Returns:
            New strategy with updated parameters and incremented version
        """
        # Create new version
        new_version = self._increment_version(strategy.version)
        new_strategy = StrategyDefinition(
            name=strategy.name,
            description=strategy.description,
            buy_conditions=strategy.buy_conditions,
            sell_conditions=strategy.sell_conditions,
            buy_logic=strategy.buy_logic,
            sell_logic=strategy.sell_logic,
            version=new_version
        )

        # Copy all parameters
        for name, param in strategy.parameters.items():
            new_strategy.parameters[name] = Parameter(
                name=param.name,
                value=param.value,
                type=param.type,
                min_value=param.min_value,
                max_value=param.max_value,
                optimizable=param.optimizable,
                description=param.description
            )

        # Apply changes
        changes_log = []
        for param_name, new_value in param_changes.items():
            if param_name in new_strategy.parameters:
                old_value = new_strategy.parameters[param_name].value
                new_strategy.parameters[param_name].value = new_value
                changes_log.append(f"{param_name}: {old_value} → {new_value}")
                print(f"✅ Updated {param_name}: {old_value} → {new_value}")
            else:
                print(f"⚠️ Parameter '{param_name}' not found in strategy")

        # Save changelog
        self._save_changelog(strategy.name, new_version, changes_log)

        # Save new version
        self.save_strategy(new_strategy)

        return new_strategy

    def optimize_parameters(self, strategy_name: str,
                           param_ranges: Dict[str, List],
                           backtest_callback) -> Dict:
        """Optimize parameters using grid search

        Args:
            strategy_name: Name of strategy to optimize
            param_ranges: Dict of param_name -> [list of values to test]
            backtest_callback: Async function to run backtest

        Returns:
            Dict with best parameters and results
        """
        print(f"🔬 Optimizing {strategy_name}...")
        print(f"Parameters to optimize: {list(param_ranges.keys())}")

        # Load current strategy
        strategy = self.load_strategy(strategy_name)
        if not strategy:
            return {"success": False, "error": "Strategy not found"}

        # Generate parameter combinations
        combinations = self._generate_combinations(param_ranges)
        total_combinations = len(combinations)

        print(f"Testing {total_combinations} parameter combinations...")

        results = []

        for i, params in enumerate(combinations, 1):
            print(f"Testing combination {i}/{total_combinations}: {params}")

            # Modify parameters
            test_strategy = self.modify_parameters(strategy, params)

            # Run backtest (user provides this callback)
            result = backtest_callback(test_strategy)

            results.append({
                "params": params,
                "return": result.get("return_pct", -100),
                "sharpe": result.get("sharpe_ratio", 0),
                "win_rate": result.get("win_rate", 0)
            })

        # Find best by return
        best_result = max(results, key=lambda x: x["return"])

        print(f"\n🏆 Best parameters found:")
        for param_name, param_value in best_result["params"].items():
            print(f"  {param_name}: {param_value}")
        print(f"  Return: {best_result['return']:.2f}%")

        return {
            "success": True,
            "best_params": best_result["params"],
            "best_return": best_result["return"],
            "all_results": sorted(results, key=lambda x: x["return"], reverse=True)
        }

    def compare_versions(self, strategy_name: str,
                        version1: str, version2: str) -> Dict:
        """Compare two versions of a strategy

        Returns:
            Dict with parameter differences
        """
        v1 = self.load_strategy(strategy_name, version1)
        v2 = self.load_strategy(strategy_name, version2)

        if not v1 or not v2:
            return {"success": False, "error": "One or both versions not found"}

        differences = []

        # Compare parameters
        all_params = set(v1.parameters.keys()) | set(v2.parameters.keys())

        for param_name in all_params:
            val1 = v1.parameters[param_name].value if param_name in v1.parameters else None
            val2 = v2.parameters[param_name].value if param_name in v2.parameters else None

            if val1 != val2:
                differences.append({
                    "parameter": param_name,
                    f"version_{version1}": val1,
                    f"version_{version2}": val2
                })

        return {
            "success": True,
            "strategy": strategy_name,
            "version1": version1,
            "version2": version2,
            "differences": differences
        }

    def list_versions(self, strategy_name: str) -> List[Dict]:
        """List all versions of a strategy

        Returns:
            List of version info dicts
        """
        strategy_dir = self.strategies_dir / strategy_name

        if not strategy_dir.exists():
            return []

        versions = []

        for filepath in sorted(strategy_dir.glob(f"{strategy_name}_v*.json")):
            with open(filepath, 'r') as f:
                data = json.load(f)

            versions.append({
                "version": data["version"],
                "file": filepath.name,
                "modified": datetime.fromtimestamp(filepath.stat().st_mtime).isoformat()
            })

        return versions

    def _increment_version(self, version: str) -> str:
        """Increment version number (e.g., 1.0 -> 1.1)"""
        parts = version.split('.')
        major, minor = int(parts[0]), int(parts[1])
        minor += 1
        return f"{major}.{minor}"

    def _generate_combinations(self, param_ranges: Dict[str, List]) -> List[Dict]:
        """Generate all parameter combinations for grid search"""
        from itertools import product

        param_names = list(param_ranges.keys())
        param_values = [param_ranges[name] for name in param_names]

        combinations = []
        for values in product(*param_values):
            combination = {name: value for name, value in zip(param_names, values)}
            combinations.append(combination)

        return combinations

    def _save_changelog(self, strategy_name: str, version: str, changes: List[str]):
        """Save changelog for version"""
        strategy_dir = self.strategies_dir / strategy_name
        changelog_path = strategy_dir / "CHANGELOG.md"

        entry = f"\n## Version {version} - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
        for change in changes:
            entry += f"- {change}\n"

        # Append to changelog
        with open(changelog_path, 'a') as f:
            f.write(entry)


if __name__ == "__main__":
    from strategy_definition import StrategyParser

    # Create manager
    manager = ParameterManager(strategies_dir=Path("test_strategies"))

    # Parse a strategy
    parser = StrategyParser()
    description = """
    Create RSI strategy:
    - Buy when: RSI(14) < 30 AND volume > 2x average
    - Sell when: RSI(14) > 70 OR profit > 5%
    - Position size: 10% of portfolio
    - Max 1 position per coin
    """

    strategy = parser.parse(description, "RSI_Momentum")

    print("=" * 60)
    print("1. Saving initial strategy...")
    print("=" * 60)
    manager.save_strategy(strategy)

    print("\n" + "=" * 60)
    print("2. Modifying parameters...")
    print("=" * 60)
    modified_strategy = manager.modify_parameters(strategy, {
        "rsi_period": 21,
        "rsi_oversold": 25,
        "volume_multiplier": 2.5
    })

    print("\n" + "=" * 60)
    print("3. Modifying again...")
    print("=" * 60)
    modified_strategy2 = manager.modify_parameters(modified_strategy, {
        "profit_target_pct": 7.0
    })

    print("\n" + "=" * 60)
    print("4. Listing versions...")
    print("=" * 60)
    versions = manager.list_versions("RSI_Momentum")
    for v in versions:
        print(f"  Version {v['version']}: {v['file']} (modified: {v['modified']})")

    print("\n" + "=" * 60)
    print("5. Comparing versions...")
    print("=" * 60)
    comparison = manager.compare_versions("RSI_Momentum", "1.0", "1.2")
    if comparison["success"]:
        print(f"Differences between v{comparison['version1']} and v{comparison['version2']}:")
        for diff in comparison["differences"]:
            v1_key = f"version_{comparison['version1']}"
            v2_key = f"version_{comparison['version2']}"
            print(f"  {diff['parameter']}: {diff[v1_key]} → {diff[v2_key]}")

    print("\n✅ Parameter manager test complete!")
