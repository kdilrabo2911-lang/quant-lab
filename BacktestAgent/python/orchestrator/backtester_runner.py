"""
Python wrapper to run C++ backtester.
Falls back to Python implementation if C++ binary not available.
"""

import subprocess
import os
import json
from pathlib import Path
from typing import Dict, List, Optional


class BacktesterRunner:
    def __init__(self, cpp_binary_path: Optional[str] = None):
        if cpp_binary_path is None:
            # Default: look for compiled binary
            repo_root = Path(__file__).parent.parent.parent
            cpp_binary_path = repo_root / "build" / "backtester_cli"

        self.cpp_binary = Path(cpp_binary_path)
        self.use_cpp = self.cpp_binary.exists()

        if not self.use_cpp:
            print(f"[WARNING] C++ backtester not found at {self.cpp_binary}")
            print("[WARNING] Using Python fallback (slower)")

    def run(self,
            strategy: str,
            data_file: str,
            coin: str,
            parameters: Optional[Dict] = None) -> Dict:
        """
        Run backtest for a single strategy/coin combination.

        Args:
            strategy: Strategy name (ma_trailing, ma, volatility, sentiment)
            data_file: Path to CSV data file
            coin: Coin name (BTC, ETH, etc.)
            parameters: Strategy parameters (optional)

        Returns:
            Backtest results as dictionary
        """

        if self.use_cpp:
            return self._run_cpp(strategy, data_file, coin, parameters)
        else:
            return self._run_python_fallback(strategy, data_file, coin, parameters)

    def _run_cpp(self, strategy: str, data_file: str, coin: str, parameters: Optional[Dict]) -> Dict:
        """Run C++ backtester via subprocess"""

        # Create temp file for JSON output
        import tempfile
        json_output = tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False)
        json_output_path = json_output.name
        json_output.close()

        try:
            cmd = [str(self.cpp_binary), strategy, data_file, coin, "--json", json_output_path]

            # Add parameters if provided
            if parameters:
                for key, value in parameters.items():
                    cmd.extend(["--param", f"{key}={value}"])

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=60
            )

            # Print C++ console output (for user visibility)
            if result.stdout:
                print(result.stdout)

            if result.returncode != 0:
                raise RuntimeError(f"C++ backtester failed: {result.stderr}")

            # Read JSON output
            with open(json_output_path, 'r') as f:
                return json.load(f)

        except subprocess.TimeoutExpired:
            raise RuntimeError("Backtest timeout (60s)")
        except Exception as e:
            raise RuntimeError(f"Failed to run C++ backtester: {e}")
        finally:
            # Clean up temp file
            if os.path.exists(json_output_path):
                os.remove(json_output_path)

    def _parse_cpp_output(self, output: str) -> Dict:
        """Parse C++ backtester console output"""
        # TODO: Make C++ output JSON for easy parsing
        # For now, extract key metrics from text output

        lines = output.split('\n')
        results = {
            "strategy_name": "",
            "coin": "",
            "total_return_pct": 0.0,
            "num_trades": 0,
            "win_rate": 0.0,
            "sharpe_ratio": 0.0
        }

        for line in lines:
            if "Total Return:" in line:
                results["total_return_pct"] = float(line.split(":")[1].strip().replace("%", ""))
            elif "Number of Trades:" in line:
                results["num_trades"] = int(line.split(":")[1].strip())
            elif "Win Rate:" in line:
                results["win_rate"] = float(line.split(":")[1].strip().replace("%", "")) / 100.0
            elif "Sharpe Ratio:" in line:
                results["sharpe_ratio"] = float(line.split(":")[1].strip())

        return results

    def _run_python_fallback(self, strategy: str, data_file: str, coin: str, parameters: Optional[Dict]) -> Dict:
        """Python fallback (stub - returns dummy data)"""

        print(f"[PYTHON FALLBACK] Running {strategy} on {coin}")
        print(f"[PYTHON FALLBACK] Data: {data_file}")

        # TODO: Implement actual Python backtest engine
        # For now, return dummy results

        return {
            "strategy_name": strategy,
            "coin": coin,
            "total_return_pct": 0.0,
            "num_trades": 0,
            "win_rate": 0.0,
            "sharpe_ratio": 0.0,
            "note": "Python fallback - not real results"
        }


if __name__ == "__main__":
    # Test
    runner = BacktesterRunner()
    print(f"Using C++: {runner.use_cpp}")

    # results = runner.run(
    #     strategy="ma_trailing",
    #     data_file="data/BTC_BTC_OHLC.csv",
    #     coin="BTC"
    # )
    # print(json.dumps(results, indent=2))
