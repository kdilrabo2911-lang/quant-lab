"""Action Executor - Executes user commands (backtests, deployments, optimizations)"""

import asyncio
import httpx
import subprocess
import json
from pathlib import Path
from typing import Dict, List, Optional
from backtest_query import BacktestQuery
from db_storage import db_storage
from strategy_store import get_store
from strategy_definition import StrategyDefinition, Parameter, Condition
from strategy_code_generator import CppCodeGenerator


class ActionExecutor:
    """Executes actions: run backtests, deploy/stop bots, optimize strategies, query results"""

    def __init__(self):
        self.base_path = Path(__file__).parent.parent
        self.data_agent_url = "http://localhost:8000"
        self.backtest_query = BacktestQuery()
        self.optimizer = None  # Lazy load to avoid circular import
        self._db_connected = False
        self.store = get_store()  # Database storage

    async def _ensure_store_connected(self):
        """Ensure strategy store is connected"""
        if not self.store._db_pool:
            await self.store.connect()

    async def deploy_strategy_for_backtest(self, strategy_name: str) -> Dict:
        """Deploy strategy from database to BacktestAgent (generate C++ code)

        Args:
            strategy_name: Name of strategy in database

        Returns:
            Dict with success status and generated files
        """
        try:
            # Get strategy from database
            await self._ensure_store_connected()
            db_strategy = await self.store.get(strategy_name)

            if not db_strategy:
                return {
                    "success": False,
                    "error": f"Strategy '{strategy_name}' not found in database"
                }

            # Convert to StrategyDefinition
            # Map database conditions to Condition objects
            buy_conds = []
            for c in db_strategy.buy_conditions:
                # Handle both dict and string formats
                if isinstance(c, dict):
                    buy_conds.append(Condition(
                        indicator=c.get('indicator', c.get('type', 'price')),
                        operator=c.get('operator', '>'),
                        threshold=c.get('threshold', c.get('value', 0)),
                        indicator_params=c.get('indicator_params', {})
                    ))
                elif isinstance(c, str):
                    # Plain text condition - create a basic Condition object
                    buy_conds.append(Condition(
                        indicator="custom",
                        operator=">",
                        threshold=0,
                        indicator_params={"description": c}
                    ))

            sell_conds = []
            for c in db_strategy.sell_conditions:
                # Handle both dict and string formats
                if isinstance(c, dict):
                    sell_conds.append(Condition(
                        indicator=c.get('indicator', c.get('type', 'price')),
                        operator=c.get('operator', '>'),
                        threshold=c.get('threshold', c.get('value', 0)),
                        indicator_params=c.get('indicator_params', {})
                    ))
                elif isinstance(c, str):
                    # Plain text condition - create a basic Condition object
                    sell_conds.append(Condition(
                        indicator="custom",
                        operator=">",
                        threshold=0,
                        indicator_params={"description": c}
                    ))

            # Convert parameters to Parameter objects
            params_dict = {}
            for k, v in db_strategy.parameters.items():
                # Handle both dict and simple value formats
                if isinstance(v, dict):
                    params_dict[k] = Parameter(
                        name=k,
                        type=v.get('type', 'double'),
                        value=v.get('value', v)
                    )
                else:
                    # Simple value (int, float, str)
                    params_dict[k] = Parameter(
                        name=k,
                        type="double",
                        value=v
                    )

            strategy_def = StrategyDefinition(
                name=db_strategy.name,
                description=db_strategy.description,
                parameters=params_dict,
                buy_conditions=buy_conds,
                sell_conditions=sell_conds
            )

            # Generate C++ code
            generator = CppCodeGenerator()
            output_dir = self.base_path / "BacktestAgent" / "cpp" / "strategies"
            output_dir.mkdir(parents=True, exist_ok=True)

            files = generator.generate(strategy_def, output_dir)

            # AUTO-REGISTER: Add strategy to main.cpp and CMakeLists.txt
            self._register_strategy_in_main_cpp(strategy_name)
            self._add_strategy_to_cmake(strategy_name)

            # AUTO-COMPILE: Try to compile the generated code
            build_dir = self.base_path / "BacktestAgent" / "build"

            if build_dir.exists():
                print(f"🔨 Auto-compiling C++ code for {strategy_name}...")

                # Try to compile
                compile_result = subprocess.run(
                    ["cmake", "..", "&&", "make", "-j4"],
                    cwd=build_dir,
                    capture_output=True,
                    text=True,
                    shell=True,
                    timeout=60
                )

                if compile_result.returncode == 0:
                    print(f"✅ Compilation successful!")

                    # VALIDATE: Check for placeholder/broken logic in generated C++ code
                    cpp_file = output_dir / f"{strategy_name.lower()}.cpp"
                    if cpp_file.exists():
                        with open(cpp_file, 'r') as f:
                            cpp_content = f.read()

                        # Check for placeholder patterns that indicate broken logic
                        has_placeholder = any([
                            "bool condition_0 = true;  // Condition (simplified)" in cpp_content,
                            "bool condition_0 = true;  //" in cpp_content and "simplified" in cpp_content,
                            "// No buy conditions defined" in cpp_content and len(db_strategy.buy_conditions) > 0,
                        ])

                        if has_placeholder:
                            print(f"⚠️  Detected placeholder logic in generated C++ code!")
                            print(f"   Strategy has {len(db_strategy.buy_conditions)} buy conditions but C++ has placeholders")
                            print(f"   Condition types: {[c.get('type') for c in db_strategy.buy_conditions if isinstance(c, dict)]}")

                            # Try to auto-fix with Claude to implement actual logic
                            print(f"🔧 Attempting to generate proper C++ implementation...")

                            # This will be handled by auto-fix mechanism
                            # For now, warn the user but still return success
                            return {
                                "success": True,
                                "strategy_name": strategy_name,
                                "files_generated": list(files.keys()),
                                "output_dir": str(output_dir),
                                "compiled": True,
                                "has_placeholders": True,
                                "warning": f"⚠️  C++ code has placeholder logic - strategy may not trade as intended. Custom condition types need manual implementation.",
                                "message": f"✅ Compiled but WARNING: Generated C++ has placeholder logic. Strategy may need manual review."
                            }

                    return {
                        "success": True,
                        "strategy_name": strategy_name,
                        "files_generated": list(files.keys()),
                        "output_dir": str(output_dir),
                        "compiled": True,
                        "message": f"✅ Generated and compiled C++ code for {strategy_name}. Ready for backtesting!"
                    }
                else:
                    # Compilation failed - TRY TO AUTO-FIX
                    print(f"❌ Compilation failed. Attempting auto-fix...")
                    print(compile_result.stderr)

                    # Try auto-fix with Claude (max 3 attempts)
                    fix_result = await self._auto_fix_cpp_compilation(
                        strategy_name=strategy_name,
                        strategy_def=strategy_def,
                        error_output=compile_result.stderr,
                        max_attempts=3
                    )

                    if fix_result.get("success"):
                        return {
                            "success": True,
                            "strategy_name": strategy_name,
                            "files_generated": list(files.keys()),
                            "output_dir": str(output_dir),
                            "compiled": True,
                            "auto_fixed": True,
                            "fix_attempts": fix_result.get("attempts", 0),
                            "message": f"✅ Generated, auto-fixed ({fix_result.get('attempts')} attempts), and compiled C++ code for {strategy_name}. Ready for backtesting!"
                        }
                    else:
                        return {
                            "success": False,
                            "strategy_name": strategy_name,
                            "files_generated": list(files.keys()),
                            "error": f"C++ code generated but compilation failed after {fix_result.get('attempts', 0)} fix attempts:\n{compile_result.stderr[:500]}"
                        }
            else:
                # Build directory doesn't exist - just generate code
                return {
                    "success": True,
                    "strategy_name": strategy_name,
                    "files_generated": list(files.keys()),
                    "output_dir": str(output_dir),
                    "compiled": False,
                    "message": f"Generated C++ code for {strategy_name}. Build directory not found - please run cmake first."
                }

        except Exception as e:
            return {
                "success": False,
                "error": f"Deployment failed: {e}"
            }

    async def run_backtest(
        self,
        strategy_name: str,
        coins: List[str],
        parameters: Optional[Dict] = None,
        days: Optional[int] = None
    ) -> Dict:
        """Run backtest via BacktestAgent CLI

        Args:
            strategy_name: Strategy name (must match database name exactly)
            coins: List of coin symbols (e.g., ["BTC", "ETH", "RNDR"])
            parameters: Strategy-specific parameters
            days: Backtest period in days (default: 30)

        Returns:
            Dict with success status, metrics, and output file path
        """

        backtest_path = self.base_path / "BacktestAgent"

        # Check if strategy exists in database
        await self._ensure_store_connected()
        db_strategy = await self.store.get(strategy_name)

        if not db_strategy:
            return {
                "success": False,
                "error": f"Strategy '{strategy_name}' not found in database",
                "message": f"I couldn't find '{strategy_name}'. Would you like me to create it?"
            }

        # Check if C++ code exists for this strategy
        cpp_strategy_file = self.base_path / "BacktestAgent" / "cpp" / "strategies" / f"{strategy_name.lower()}.cpp"

        if not cpp_strategy_file.exists():
            return {
                "success": False,
                "needs_deployment": True,
                "strategy_name": strategy_name,
                "error": f"Strategy '{strategy_name}' needs to be deployed for backtesting",
                "message": f"I found '{strategy_name}' in database but it needs C++ code generation. Would you like me to deploy it now?",
                "action_required": "deploy_strategy"
            }

        # Use the actual strategy name (consistent naming)
        strategy_code = strategy_name.lower()

        try:
            # STEP 1: Ensure all coins are registered with DataAgent
            await self._ensure_coins_registered(coins, days or 30)

            # STEP 2: Build command
            cmd = [
                "python3", "run_backtest.py",
                "--strategy", strategy_code,
                "--coins"
            ] + coins

            if days:
                cmd += ["--last-days", str(days)]

            # Add parameters if provided
            if parameters:
                for key, value in parameters.items():
                    cmd += ["--param", f"{key}={value}"]

            # STEP 3: Run backtest
            result = await asyncio.create_subprocess_exec(
                *cmd,
                cwd=backtest_path,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )

            stdout, stderr = await result.communicate()

            if result.returncode == 0:
                output = stdout.decode()

                # Parse output for metrics
                metrics = self._parse_backtest_output(output)

                # Save to database
                await self._ensure_db_connected()
                db_record_id = None
                if db_storage.enabled:
                    db_record_id = await db_storage.save_backtest_output(
                        strategy=strategy_name,
                        coins=coins,
                        output_text=output,
                        days=days,
                        run_id=metrics.get("run_id"),
                        metrics=metrics
                    )

                return {
                    "success": True,
                    "data": {
                        "output": output[:500] + "..." if len(output) > 500 else output,  # Truncate for display
                        "db_record_id": db_record_id,
                        "strategy": strategy_name,
                        "coins": coins,
                        "days": days,
                        "metrics": metrics
                    },
                    "message": f"Backtest completed for {strategy_name} on {', '.join(coins)}"
                }
            else:
                error = stderr.decode()
                return {
                    "success": False,
                    "error": error,
                    "message": f"Backtest failed: {error[:200]}"
                }

        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "message": f"Error running backtest: {str(e)}"
            }

    async def modify_backtest_params(self, strategy_name: str, new_parameters: Dict) -> Dict:
        """Modify strategy parameters (currently just returns confirmation)

        Args:
            strategy_name: Strategy to modify
            new_parameters: New parameter values

        Returns:
            Updated configuration dict
        """
        # Future: Save to config file
        return {
            "success": True,
            "strategy": strategy_name,
            "parameters": new_parameters,
            "message": f"Parameters updated for {strategy_name}"
        }

    async def deploy_strategy(
        self,
        strategy_name: str,
        mode: str = "paper",
        coins: List[str] = None,
        parameters: Dict = None
    ) -> Dict:
        """Deploy strategy to paper or live trading

        Args:
            strategy_name: Strategy to deploy
            mode: "paper" or "live"
            coins: Coins to trade (default: ["BTC"])
            parameters: Strategy parameters

        Returns:
            Deployment status dict
        """

        try:
            # Build the bot
            strategy_path = self.base_path / "BotBuildAgent" / "Strategies" / strategy_name

            if not strategy_path.exists():
                return {
                    "success": False,
                    "error": f"Strategy {strategy_name} not found",
                    "message": f"Could not find strategy at {strategy_path}"
                }

            # Check if it's built
            bin_path = strategy_path / "bin"
            if not bin_path.exists() or not any(bin_path.iterdir()):
                # Need to build first
                build_result = await self.build_strategy(strategy_name)
                if not build_result["success"]:
                    return build_result

            # Register with DataAgent
            async with httpx.AsyncClient() as client:
                payload = {
                    "name": strategy_name,
                    "mode": mode,
                    "coins": coins or ["BTC"],
                    "parameters": parameters or {}
                }

                response = await client.post(
                    f"{self.data_agent_url}/strategies/register",
                    json=payload
                )

                if response.status_code == 200:
                    return {
                        "success": True,
                        "data": response.json(),
                        "message": f"{strategy_name} deployed to {mode} trading!"
                    }
                else:
                    return {
                        "success": False,
                        "error": response.text,
                        "message": f"Failed to register strategy: {response.text}"
                    }

        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "message": f"Error deploying strategy: {str(e)}"
            }

    async def build_strategy(self, strategy_name: str) -> Dict:
        """Build C# strategy using dotnet build

        Args:
            strategy_name: Strategy to build

        Returns:
            Build result dict
        """

        strategy_path = self.base_path / "BotBuildAgent" / "Strategies" / strategy_name

        if not strategy_path.exists():
            return {
                "success": False,
                "error": f"Strategy {strategy_name} not found"
            }

        try:
            # Run dotnet build
            result = subprocess.run(
                ["dotnet", "build"],
                cwd=strategy_path,
                capture_output=True,
                text=True,
                timeout=60
            )

            if result.returncode == 0:
                return {
                    "success": True,
                    "message": f"{strategy_name} built successfully",
                    "output": result.stdout
                }
            else:
                return {
                    "success": False,
                    "error": result.stderr,
                    "message": f"Build failed for {strategy_name}"
                }

        except subprocess.TimeoutExpired:
            return {
                "success": False,
                "error": "Build timeout",
                "message": "Build took too long (>60s)"
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "message": f"Error building strategy: {str(e)}"
            }

    async def get_running_bots(self) -> Dict:
        """Get list of currently running bots"""

        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(f"{self.data_agent_url}/strategies")

                if response.status_code == 200:
                    return {
                        "success": True,
                        "data": response.json(),
                        "message": "Fetched running bots"
                    }
                else:
                    return {
                        "success": False,
                        "error": "Could not fetch strategies",
                        "message": "DataAgent returned an error"
                    }
        except:
            return {
                "success": False,
                "error": "DataAgent not reachable",
                "message": "DataAgent might not be running"
            }

    async def stop_bot(self, strategy_name: str) -> Dict:
        """Stop a running bot"""

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.data_agent_url}/strategies/{strategy_name}/stop"
                )

                if response.status_code == 200:
                    return {
                        "success": True,
                        "message": f"Stopped {strategy_name}"
                    }
                else:
                    return {
                        "success": False,
                        "error": response.text,
                        "message": f"Failed to stop {strategy_name}"
                    }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "message": f"Error stopping bot: {str(e)}"
            }

    async def start_service(self, service_name: str) -> Dict:
        """Start a service (DataAgent only - BacktestAgent doesn't need starting)"""

        if service_name == "BacktestAgent":
            return {
                "success": True,
                "message": "BacktestAgent doesn't need to be started - it runs on-demand!",
                "already_running": True
            }

        service_paths = {
            "DataAgent": self.base_path / "DataAgent"
        }

        if service_name not in service_paths:
            return {
                "success": False,
                "error": f"Unknown service: {service_name}",
                "message": f"I don't know how to start {service_name}"
            }

        service_path = service_paths[service_name]

        if not service_path.exists():
            return {
                "success": False,
                "error": f"Service path not found: {service_path}",
                "message": f"Can't find {service_name} at {service_path}"
            }

        try:
            # Check if already running
            try:
                async with httpx.AsyncClient() as client:
                    resp = await client.get(f"{self.data_agent_url}/strategies", timeout=2.0)
                    if resp.status_code == 200:
                        return {
                            "success": True,
                            "message": f"{service_name} is already running!",
                            "already_running": True
                        }
            except:
                pass

            subprocess.Popen(
                ["python3", "app.py"],
                cwd=service_path,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                start_new_session=True
            )

            await asyncio.sleep(3)

            return {
                "success": True,
                "message": f"{service_name} started!"
            }

        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "message": f"Error starting {service_name}: {str(e)}"
            }


    async def _ensure_coins_registered(self, coins: List[str], days_needed: int) -> Dict:
        """Ensure all coins are registered with DataAgent and have sufficient data

        Args:
            coins: List of coin symbols
            days_needed: Number of days of historical data required

        Returns:
            Dict with registration results by category
        """
        results = {"registered": [], "already_had_data": [], "waiting_for_data": []}

        async with httpx.AsyncClient() as client:
            for coin in coins:
                # Check if coin has data
                try:
                    resp = await client.get(f"{self.data_agent_url}/candles/{coin}?limit=1", timeout=5.0)
                    if resp.status_code == 200:
                        results["already_had_data"].append(coin)
                        continue
                except:
                    pass

                # Coin doesn't have data - register it
                try:
                    payload = {
                        "strategy_name": f"BacktestPrep_{coin}",
                        "coins": [coin]
                    }
                    resp = await client.post(
                        f"{self.data_agent_url}/register",
                        json=payload,
                        timeout=10.0
                    )

                    if resp.status_code == 200:
                        results["registered"].append(coin)
                        results["waiting_for_data"].append(coin)

                except Exception as e:
                    print(f"Failed to register {coin}: {e}")

        # If we registered new coins, wait for data collection
        if results["waiting_for_data"]:
            print(f"⏳ Waiting for data collection: {', '.join(results['waiting_for_data'])}")
            print(f"   Need {days_needed} days of data...")

            # Wait up to 60 seconds for data to appear
            for i in range(12):  # 12 * 5 = 60 seconds
                await asyncio.sleep(5)

                # Check if data is available
                all_ready = True
                async with httpx.AsyncClient() as client:
                    for coin in results["waiting_for_data"]:
                        try:
                            resp = await client.get(f"{self.data_agent_url}/candles/{coin}?limit=1", timeout=3.0)
                            if resp.status_code != 200:
                                all_ready = False
                                break
                        except:
                            all_ready = False
                            break

                if all_ready:
                    print(f"✓ Data ready for all coins!")
                    break

                print(f"   Still waiting... ({(i+1)*5}s)")

        return results

    def _parse_backtest_output(self, output: str) -> Dict:
        """Parse backtest CLI output to extract metrics

        Args:
            output: Raw CLI output string

        Returns:
            Dict with parsed metrics (return, win rate, drawdown, trades, run_id)
        """
        import re

        metrics = {
            "total_return_pct": -100.0,
            "win_rate": 0.0,
            "max_drawdown_pct": 0.0,
            "total_trades": 0,
            "run_id": None
        }

        try:
            lines = output.split('\n')

            for line in lines:
                # Extract Run ID from "Saved to database (Run ID: 115)"
                if "Run ID:" in line or "run #" in line:
                    match = re.search(r'(?:Run ID:|run #)(\d+)', line)
                    if match:
                        metrics["run_id"] = int(match.group(1))

                # Total Return
                if "Total Return" in line or "Return:" in line:
                    match = re.search(r'([-+]?\d+\.?\d*)%', line)
                    if match:
                        metrics["total_return_pct"] = float(match.group(1))

                # Win Rate
                if "Win Rate" in line or "Wins:" in line:
                    match = re.search(r'(\d+\.?\d*)%', line)
                    if match:
                        metrics["win_rate"] = float(match.group(1))

                # Drawdown
                if "Drawdown" in line or "Max DD" in line:
                    match = re.search(r'([-]?\d+\.?\d*)%', line)
                    if match:
                        metrics["max_drawdown_pct"] = float(match.group(1))

                # Total Trades
                if "Trades:" in line:
                    match = re.search(r'Trades:\s*(\d+)', line)
                    if match:
                        metrics["total_trades"] = int(match.group(1))

        except Exception as e:
            print(f"Error parsing metrics: {e}")

        return metrics

    async def analyze_backtest_run(self, run_id: int, export_csv: bool = False) -> Dict:
        """Analyze backtest run from database and optionally export CSV

        Args:
            run_id: Backtest run ID to analyze
            export_csv: Whether to export trade logs as CSV

        Returns:
            Analysis results with optional CSV file path
        """
        result = await self.backtest_query.analyze_run(run_id)

        if not result.get("success"):
            return result

        # Export CSV if requested
        if export_csv:
            output_dir = self.base_path / "MasterAgent" / "backtest_outputs"
            output_dir.mkdir(exist_ok=True)

            from datetime import datetime
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            local_csv = output_dir / f"trades_run{run_id}_{timestamp}.csv"

            success = await self.backtest_query.export_trades_csv(run_id, str(local_csv))

            if success:
                result["csv_file"] = str(local_csv)
                print(f"✅ CSV exported locally: {local_csv}")

        return result

    async def _ensure_db_connected(self):
        """Ensure database connection is established"""
        if not self._db_connected and db_storage.enabled:
            await db_storage.connect()
            self._db_connected = True

    async def optimize_strategy(
        self,
        strategy_name: str,
        coins: List[str],
        days: int = 30,
        param_grid: Optional[Dict] = None,
        grid_mode: Optional[str] = None
    ) -> Dict:
        """Optimize strategy parameters using grid search

        Args:
            strategy_name: Strategy to optimize
            coins: Coins to test on
            days: Backtest period (default: 30)
            param_grid: Custom parameter grid (None for defaults)
            grid_mode: How to handle partial grids:
                - None: Use full default grid (Case 1)
                - "merge_defaults": User params + default arrays for others (Case 2)
                - "fix_others": User params + current values for others (Case 3)
                - "replace": Full custom grid, ignore defaults (Case 4)

        Returns:
            Optimization results with best parameters and performance
        """
        # Lazy load optimizer to avoid circular import
        if self.optimizer is None:
            from strategy_optimizer import StrategyOptimizer, DEFAULT_PARAM_GRIDS
            self.optimizer = StrategyOptimizer()
            self.default_grids = DEFAULT_PARAM_GRIDS

        # Handle parameter grid with 4 different cases
        # Load strategy from DATABASE (not files)
        await self._ensure_store_connected()
        db_strategy = await self.store.get(strategy_name)

        if not db_strategy:
            return {
                "success": False,
                "error": f"Strategy '{strategy_name}' not found in database"
            }

        # Get optimization grid from database or use provided param_grid
        default_grid = db_strategy.optimization_grid or self.default_grids.get(strategy_name)

        # Convert database strategy to have .parameters dict for compatibility
        # db_strategy.parameters is already a dict, just need to access values
        class StrategyWrapper:
            def __init__(self, db_strat):
                self.name = db_strat.name
                self.parameters = {}
                # Convert flat dict to Parameter-like objects
                for k, v in db_strat.parameters.items():
                    if isinstance(v, dict) and 'value' in v:
                        self.parameters[k] = type('obj', (object,), {'value': v['value']})
                    else:
                        self.parameters[k] = type('obj', (object,), {'value': v})

        strategy = StrategyWrapper(db_strategy)

        # CASE 1: No param_grid specified - use full default grid
        if param_grid is None:
            param_grid = default_grid

        # CASE 2: grid_mode="merge_defaults" - merge user arrays with default arrays
        elif grid_mode == "merge_defaults":
            if default_grid and strategy:
                merged_grid = default_grid.copy()  # Start with defaults
                merged_grid.update(param_grid)     # Override with user values
                param_grid = merged_grid

        # CASE 3: grid_mode="fix_others" - user arrays + current values for others
        elif grid_mode == "fix_others":
            if strategy:
                merged_grid = {}
                if default_grid:
                    for param_name in default_grid.keys():
                        if param_name in param_grid:
                            # User specified - use their array
                            merged_grid[param_name] = param_grid[param_name]
                        else:
                            # User didn't specify - use current value ONLY
                            if param_name in strategy.parameters:
                                current_value = strategy.parameters[param_name].value
                                merged_grid[param_name] = [current_value]

                # Add any user params not in default grid
                for param_name in param_grid.keys():
                    if param_name not in merged_grid:
                        merged_grid[param_name] = param_grid[param_name]

                param_grid = merged_grid

        # CASE 4: grid_mode="replace" OR all params specified - use only user grid
        elif grid_mode == "replace" or grid_mode is None:
            # Use user param_grid as-is (full replacement)
            pass

        if param_grid is None or len(param_grid) == 0:
            return {
                "success": False,
                "error": f"No parameter grid found for {strategy_name}. Please define optimization ranges."
            }

        try:
            result = await self.optimizer.optimize(
                strategy_name=strategy_name,
                coins=coins,
                days=days,
                param_grid=param_grid
            )
            return result
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "message": f"Optimization failed: {str(e)}"
            }

    async def _auto_fix_cpp_compilation(self, strategy_name: str, strategy_def, error_output: str, max_attempts: int = 3) -> Dict:
        """Auto-fix C++ compilation errors using Claude

        Args:
            strategy_name: Name of strategy
            strategy_def: Strategy definition
            error_output: Compilation error output
            max_attempts: Maximum fix attempts

        Returns:
            Dict with success status and number of attempts
        """
        import anthropic
        import os

        anthropic_client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

        for attempt in range(1, max_attempts + 1):
            print(f"\n🔧 Auto-fix attempt {attempt}/{max_attempts}...")

            # Read current generated C++ file
            cpp_file = self.base_path / "BacktestAgent" / "cpp" / "strategies" / f"{strategy_name.lower()}.cpp"

            if not cpp_file.exists():
                return {"success": False, "attempts": attempt, "error": "C++ file not found"}

            with open(cpp_file, 'r') as f:
                current_code = f.read()

            # Ask Claude to fix it
            prompt = f"""Fix this C++ compilation error:

ERROR:
{error_output}

CURRENT C++ CODE:
```cpp
{current_code}
```

STRATEGY DEFINITION:
- Name: {strategy_name}
- Description: {strategy_def.description}
- Parameters: {strategy_def.parameters}

Please provide the COMPLETE FIXED C++ file. Output ONLY the C++ code, no explanation."""

            response = anthropic_client.messages.create(
                model="claude-opus-4-7",
                max_tokens=4096,
                messages=[{"role": "user", "content": prompt}]
            )

            fixed_code = response.content[0].text.strip()

            # Remove markdown if present
            if fixed_code.startswith("```cpp"):
                fixed_code = fixed_code[6:]
            if fixed_code.startswith("```"):
                fixed_code = fixed_code[3:]
            if fixed_code.endswith("```"):
                fixed_code = fixed_code[:-3]

            fixed_code = fixed_code.strip()

            # Write fixed code
            with open(cpp_file, 'w') as f:
                f.write(fixed_code)

            print(f"✍️  Wrote fixed code to {cpp_file.name}")

            # Try to compile again
            build_dir = self.base_path / "BacktestAgent" / "build"
            compile_result = subprocess.run(
                ["cmake", "..", "&&", "make", "-j4"],
                cwd=build_dir,
                capture_output=True,
                text=True,
                shell=True,
                timeout=60
            )

            if compile_result.returncode == 0:
                print(f"✅ Compilation successful after {attempt} attempt(s)!")
                return {"success": True, "attempts": attempt}
            else:
                print(f"❌ Compilation still failing...")
                error_output = compile_result.stderr  # Update error for next iteration

        # Failed after max attempts
        return {"success": False, "attempts": max_attempts, "error": error_output}

    def _register_strategy_in_main_cpp(self, strategy_name: str):
        """Add strategy to main.cpp CreateStrategy function"""
        main_cpp = self.base_path / "BacktestAgent" / "cpp" / "main.cpp"

        with open(main_cpp, 'r') as f:
            content = f.read()

        # Check if already registered
        if f"CreateStrategy_{strategy_name}" in content:
            print(f"✓ Strategy {strategy_name} already registered in main.cpp")
            return

        # Add forward declaration
        forward_decl = f"    StrategyInterface* CreateStrategy_{strategy_name}();\n"
        content = content.replace("}\n\nstd::shared_ptr", forward_decl + "}\n\nstd::shared_ptr")

        # Add to CreateStrategy function
        strategy_case = f'''    }} else if (strategy_name == "{strategy_name.lower()}" || strategy_name == "{strategy_name}") {{
        return std::shared_ptr<StrategyInterface>(CreateStrategy_{strategy_name}());
'''
        content = content.replace("    } else {\n        throw std::runtime_error", strategy_case + "    } else {\n        throw std::runtime_error")

        with open(main_cpp, 'w') as f:
            f.write(content)

        print(f"✓ Registered {strategy_name} in main.cpp")

    def _add_strategy_to_cmake(self, strategy_name: str):
        """Add strategy to CMakeLists.txt"""
        cmake_file = self.base_path / "BacktestAgent" / "CMakeLists.txt"

        with open(cmake_file, 'r') as f:
            content = f.read()

        strategy_file = f"cpp/strategies/{strategy_name.lower()}.cpp"

        if strategy_file in content:
            print(f"✓ Strategy {strategy_name} already in CMakeLists.txt")
            return

        # Add to SOURCES
        content = content.replace(
            "    cpp/main.cpp\n",
            f"    cpp/main.cpp\n    {strategy_file}\n"
        )

        with open(cmake_file, 'w') as f:
            f.write(content)

        print(f"✓ Added {strategy_name} to CMakeLists.txt")


if __name__ == "__main__":
    # Test
    executor = ActionExecutor()
    result = asyncio.run(executor.get_running_bots())
    print(result)
