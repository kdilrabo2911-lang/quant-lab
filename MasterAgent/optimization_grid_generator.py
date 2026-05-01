"""
Optimization Grid Generator - Auto-generate parameter grids for custom strategies
"""

from typing import Dict, List, Any, Optional
from strategy_definition import StrategyDefinition, Parameter
import json
from pathlib import Path


class OptimizationGridGenerator:
    """Automatically generates optimization grids for strategy parameters"""

    # Default grid sizes for different parameter types
    DEFAULT_GRIDS = {
        "ma_period": [144, 288, 576, 1152],  # 12h, 1d, 2d, 4d in 5-min candles
        "profit_target_pct": [1.5, 2.0, 2.5, 3.0, 4.0],
        "dip_threshold_pct": [1.5, 2.0, 2.5, 3.0, 4.0],
        "stop_loss_pct": [2.0, 3.0, 5.0, 7.0],
        "rsi_period": [7, 14, 21, 28],
        "rsi_oversold": [20, 25, 30, 35],
        "rsi_overbought": [65, 70, 75, 80],
        "bb_period": [15, 20, 25, 30],
        "bb_std_dev": [1.5, 2.0, 2.5, 3.0],
        "volume_multiplier": [1.5, 2.0, 2.5, 3.0],
        "position_size_value": [2.0, 3.0, 5.0],
        "max_positions_per_coin": [1, 2, 3, 5]
    }

    def __init__(self):
        pass

    def generate_grid(
        self,
        strategy: StrategyDefinition,
        custom_ranges: Optional[Dict[str, List[Any]]] = None
    ) -> Dict[str, List[Any]]:
        """
        Generate optimization grid for a strategy

        Args:
            strategy: Strategy definition with parameters
            custom_ranges: User-defined custom ranges that override defaults
                          e.g., {"ma_period": [72, 144, 288], "profit_target_pct": [2.0, 3.0]}

        Returns:
            Dictionary mapping parameter names to lists of values to test

        Example:
            {
                "ma_period": [144, 288, 576, 1152],
                "profit_target_pct": [2.0, 2.5, 3.0]
            }
        """
        grid = {}

        for param_name, param in strategy.parameters.items():
            # Skip non-optimizable parameters
            if not param.optimizable:
                continue

            # Use custom range if provided
            if custom_ranges and param_name in custom_ranges:
                grid[param_name] = custom_ranges[param_name]
                continue

            # Use default grid if available
            if param_name in self.DEFAULT_GRIDS:
                grid[param_name] = self.DEFAULT_GRIDS[param_name]
                continue

            # Auto-generate grid based on parameter type and bounds
            if param.type == "int":
                grid[param_name] = self._generate_int_grid(param)
            elif param.type == "float":
                grid[param_name] = self._generate_float_grid(param)
            elif param.type == "bool":
                grid[param_name] = [True, False]
            # Skip string and other types

        return grid

    def _generate_int_grid(self, param: Parameter) -> List[int]:
        """Generate grid for integer parameters"""
        if param.min_value is not None and param.max_value is not None:
            # Create 4-5 evenly spaced values
            min_val = int(param.min_value)
            max_val = int(param.max_value)
            step = max(1, (max_val - min_val) // 4)

            values = []
            current = min_val
            while current <= max_val:
                values.append(current)
                current += step

            # Ensure we include max_value
            if values[-1] != max_val:
                values.append(max_val)

            return values[:5]  # Max 5 values

        # Fallback: use current value with variations
        base = int(param.value)
        return [
            max(1, base // 2),
            base,
            base * 2
        ]

    def _generate_float_grid(self, param: Parameter) -> List[float]:
        """Generate grid for float parameters"""
        if param.min_value is not None and param.max_value is not None:
            # Create 4-5 evenly spaced values
            min_val = float(param.min_value)
            max_val = float(param.max_value)
            step = (max_val - min_val) / 4.0

            values = []
            current = min_val
            for _ in range(5):
                values.append(round(current, 2))
                current += step

            return values

        # Fallback: use current value with variations
        base = float(param.value)
        return [
            round(base * 0.5, 2),
            round(base * 0.75, 2),
            base,
            round(base * 1.5, 2),
            round(base * 2.0, 2)
        ]

    def save_grid(
        self,
        strategy_name: str,
        grid: Dict[str, List[Any]],
        strategies_dir: Path = None
    ) -> Path:
        """
        Save optimization grid to strategy folder

        Args:
            strategy_name: Name of strategy
            grid: Parameter grid dictionary
            strategies_dir: Base strategies directory

        Returns:
            Path to saved grid file
        """
        if strategies_dir is None:
            strategies_dir = Path("strategies")

        strategy_dir = strategies_dir / strategy_name
        strategy_dir.mkdir(parents=True, exist_ok=True)

        grid_file = strategy_dir / "optimization_grid.json"

        with open(grid_file, 'w') as f:
            json.dump(grid, f, indent=2)

        return grid_file

    def load_grid(
        self,
        strategy_name: str,
        strategies_dir: Path = None
    ) -> Optional[Dict[str, List[Any]]]:
        """
        Load optimization grid from strategy folder

        Args:
            strategy_name: Name of strategy
            strategies_dir: Base strategies directory

        Returns:
            Parameter grid dictionary or None if not found
        """
        if strategies_dir is None:
            strategies_dir = Path("strategies")

        grid_file = strategies_dir / strategy_name / "optimization_grid.json"

        if not grid_file.exists():
            return None

        with open(grid_file, 'r') as f:
            return json.load(f)


# Global instance
grid_generator = OptimizationGridGenerator()


if __name__ == "__main__":
    # Test grid generation
    from strategy_definition import StrategyParser

    parser = StrategyParser()
    description = """
    Buy when price is below the 1-day moving average AND price has dropped 2.5%
    from the previous closed position. Sell when price reaches 2.5% profit target.
    """

    strategy = parser.parse(description, "TestStrategy")

    print(f"Strategy: {strategy.name}")
    print(f"Parameters: {list(strategy.parameters.keys())}")

    grid = grid_generator.generate_grid(strategy)
    print(f"\nGenerated Grid:")
    for param, values in grid.items():
        print(f"  {param}: {values}")

    # Test with custom ranges
    custom = {
        "ma_period": [72, 144, 288, 576, 1152],  # 6h, 12h, 1d, 2d, 4d
        "profit_target_pct": [2.0, 3.0, 5.0]
    }

    grid_custom = grid_generator.generate_grid(strategy, custom)
    print(f"\nGenerated Grid (with custom ranges):")
    for param, values in grid_custom.items():
        print(f"  {param}: {values}")
