"""Strategy Code Generator - Generate C++ code matching ACTUAL BacktestAgent interface"""

from pathlib import Path
from typing import Dict, List
from strategy_definition import StrategyDefinition, Condition
import json


class CppCodeGenerator:
    """Generate C++ strategy code for BacktestAgent - MATCHES ACTUAL INTERFACE"""

    def generate(self, strategy: StrategyDefinition, output_dir: Path = None) -> Dict[str, str]:
        """Generate C++ strategy files

        Returns:
            Dict with filenames and code content
        """
        files = {}

        # Generate header file
        files[f"{strategy.name.lower()}.h"] = self._generate_header(strategy)

        # Generate implementation file
        files[f"{strategy.name.lower()}.cpp"] = self._generate_implementation(strategy)

        # Generate parameter config JSON
        if hasattr(strategy, 'to_json'):
            files[f"{strategy.name.lower()}_params.json"] = strategy.to_json()
        else:
            # Generate JSON from database Strategy object
            import json
            param_json = {
                "name": strategy.name,
                "description": strategy.description,
                "parameters": strategy.parameters,
                "buy_conditions": strategy.buy_conditions,
                "sell_conditions": strategy.sell_conditions
            }
            files[f"{strategy.name.lower()}_params.json"] = json.dumps(param_json, indent=2)

        # Write to disk if output_dir provided
        if output_dir:
            output_dir = Path(output_dir)
            output_dir.mkdir(parents=True, exist_ok=True)

            for filename, content in files.items():
                filepath = output_dir / filename
                with open(filepath, 'w') as f:
                    f.write(content)
                print(f"✅ Generated: {filepath}")

        return files

    def _generate_header(self, strategy: StrategyDefinition) -> str:
        """Generate C++ header file matching ACTUAL BacktestAgent interface"""
        class_name = strategy.name
        include_guard = f"{strategy.name.upper()}_H"

        # Generate parameter declarations
        param_declarations = []
        for name, param in strategy.parameters.items():
            # Handle both Parameter objects and raw values from database
            if hasattr(param, 'type'):
                param_type = param.type
            else:
                # Infer type from value
                if isinstance(param, bool):
                    param_type = "bool"
                elif isinstance(param, int):
                    param_type = "int"
                elif isinstance(param, float):
                    param_type = "double"
                elif isinstance(param, str):
                    param_type = "string"
                else:
                    param_type = "double"  # default

            cpp_type = self._get_cpp_type(param_type)
            param_declarations.append(f"    {cpp_type} {name}_;")

        params_str = "\n".join(param_declarations) if param_declarations else "    // No parameters"

        header = f'''#ifndef {include_guard}
#define {include_guard}

#include "strategy_interface.hpp"
#include "types.hpp"
#include <vector>
#include <string>

namespace backtest {{

/**
 * {strategy.name} Strategy
 *
 * {strategy.description}
 */
class {class_name} : public StrategyInterface {{
private:
    // Strategy parameters
{params_str}

public:
    {class_name}();

    // StrategyInterface implementation
    std::string GetName() const override {{ return "{class_name}"; }}

    bool ShouldBuy(size_t idx, const MarketData& data, const std::vector<Position>& existing_positions) const override;
    bool ShouldSell(size_t idx, const MarketData& data, const Position& position) const override;

    void SetParameters(const ParameterSet& params) override;
    ParameterSet GetParameters() const override;

    void ComputeIndicators(MarketData& data) const override;

    std::string GetSellReason(size_t idx, const MarketData& data, const Position& position) const override;
}};

}} // namespace backtest

// Factory function for dynamic loading
extern "C" {{
    backtest::StrategyInterface* CreateStrategy_{class_name}();
}}

#endif // {include_guard}
'''
        return header

    def _generate_implementation(self, strategy: StrategyDefinition) -> str:
        """Generate C++ implementation matching ACTUAL types and interface"""
        class_name = strategy.name

        # Generate default parameter initialization
        param_init = []
        for name, param in strategy.parameters.items():
            # Handle both Parameter objects and raw values from database
            if hasattr(param, 'value'):
                value = param.value
                param_type = param.type
            else:
                value = param
                # Infer type from value
                if isinstance(param, bool):
                    param_type = "bool"
                elif isinstance(param, int):
                    param_type = "int"
                elif isinstance(param, float):
                    param_type = "double"
                elif isinstance(param, str):
                    param_type = "string"
                else:
                    param_type = "double"

            formatted_value = self._format_cpp_value(value, param_type)
            param_init.append(f"    {name}_ = {formatted_value};")

        param_init_str = "\n".join(param_init) if param_init else "    // No parameters to initialize"

        # Generate buy/sell logic
        buy_logic = self._generate_buy_logic(strategy)
        sell_logic = self._generate_sell_logic(strategy)

        implementation = f'''#include "{class_name.lower()}.h"
#include <cmath>
#include <algorithm>
#include <numeric>

namespace backtest {{

{class_name}::{class_name}() {{
{param_init_str}
}}

void {class_name}::SetParameters(const ParameterSet& params) {{
    // Update parameters from ParameterSet
    // (Implementation would parse params and update member variables)
}}

ParameterSet {class_name}::GetParameters() const {{
    ParameterSet params;
    // (Implementation would return current parameters)
    return params;
}}

void {class_name}::ComputeIndicators(MarketData& data) const {{
    // Pre-compute indicators if needed
    // For now, we compute indicators on-demand in ShouldBuy/ShouldSell
}}

bool {class_name}::ShouldBuy(size_t idx, const MarketData& data, const std::vector<Position>& existing_positions) const {{
    // Limit to 1 position at a time
    if (!existing_positions.empty()) return false;

{buy_logic}
}}

bool {class_name}::ShouldSell(size_t idx, const MarketData& data, const Position& position) const {{
{sell_logic}
}}

std::string {class_name}::GetSellReason(size_t idx, const MarketData& data, const Position& position) const {{
    double current_price = data.close[idx];
    double profit_pct = ((current_price - position.buy_price) / position.buy_price) * 100.0;

    // Check sell conditions and return reason
    if (profit_pct >= 3.0) {{
        return "profit_target";
    }}

    return "signal";
}}

}} // namespace backtest

// Factory function
extern "C" {{
    backtest::StrategyInterface* CreateStrategy_{class_name}() {{
        return new backtest::{class_name}();
    }}
}}
'''
        return implementation

    def _generate_buy_logic(self, strategy: StrategyDefinition) -> str:
        """Generate buy logic using ACTUAL MarketData structure"""

        # Default logic if no conditions
        if not strategy.buy_conditions:
            return '''    // No buy conditions defined
    if (idx < 50) return false;  // Need minimum data

    // Default: buy on 5% dips only
    double current_price = data.close[idx];
    if (idx >= 20) {{
        double ma20 = 0;
        for (size_t i = idx - 19; i <= idx; i++) {{
            ma20 += data.close[i];
        }}
        ma20 /= 20.0;
        return current_price < ma20 * 0.98;  // 2% below MA20
    }}
    return false;
'''

        logic = []
        logic.append("    // Check if we have enough data")
        logic.append("    if (idx < 50) return false;")
        logic.append("")
        logic.append("    // Get current values")
        logic.append("    double current_price = data.close[idx];")
        logic.append("    double current_volume = data.volume[idx];")
        logic.append("")

        # Generate conditions
        for i, cond in enumerate(strategy.buy_conditions):
            if isinstance(cond, dict):
                # Handle dict format
                cond_type = cond.get('type', cond.get('indicator', ''))
                value = cond.get('value', cond.get('threshold', 0))

                if 'rsi' in cond_type.lower():
                    # Determine comparison operator based on condition type
                    is_below = 'below' in cond_type.lower() or 'oversold' in cond_type.lower()
                    operator = '<' if is_below else '>'
                    condition_desc = 'oversold' if is_below else 'overbought'

                    # Use rsi_period parameter if available, else default to 14
                    rsi_period = "rsi_period_" if hasattr(strategy, 'parameters') and 'rsi_period' in strategy.parameters else "14"

                    logic.append(f"    // RSI {condition_desc} condition: RSI {operator} {value}")
                    logic.append(f"    const int rsi_period = {rsi_period};")
                    logic.append("    double rsi = 50.0;  // Default neutral")
                    logic.append("    ")
                    logic.append("    if (idx >= rsi_period) {")
                    logic.append("        double gains = 0.0, losses = 0.0;")
                    logic.append("        ")
                    logic.append("        // Calculate average gains and losses over RSI period")
                    logic.append("        for (size_t i = idx - rsi_period + 1; i <= idx; i++) {")
                    logic.append("            double change = data.close[i] - data.close[i-1];")
                    logic.append("            if (change > 0) gains += change;")
                    logic.append("            else losses += -change;")
                    logic.append("        }")
                    logic.append("        ")
                    logic.append("        double avg_gain = gains / rsi_period;")
                    logic.append("        double avg_loss = losses / rsi_period;")
                    logic.append("        ")
                    logic.append("        // Calculate RSI")
                    logic.append("        if (avg_loss > 0.000001) {  // Avoid division by zero")
                    logic.append("            double rs = avg_gain / avg_loss;")
                    logic.append("            rsi = 100.0 - (100.0 / (1.0 + rs));")
                    logic.append("        } else if (avg_gain > 0) {")
                    logic.append("            rsi = 100.0;  // All gains, no losses")
                    logic.append("        } else {")
                    logic.append("            rsi = 0.0;  // No movement")
                    logic.append("        }")
                    logic.append("    }")
                    logic.append(f"    ")
                    logic.append(f"    bool condition_{i} = (rsi {operator} {value});")
                    logic.append("")
                elif cond_type.lower() == 'always':
                    # Use MA20 crossunder detection (price crosses below MA20)
                    logic.append(f"    // MA20 pullback condition (price below MA20)")
                    logic.append("    bool condition_{} = false;".format(i))
                    logic.append("    if (idx >= 20) {")
                    logic.append("        double ma20 = 0.0;")
                    logic.append("        for (size_t j = idx - 19; j <= idx; j++) {")
                    logic.append("            ma20 += data.close[j];")
                    logic.append("        }")
                    logic.append("        ma20 /= 20.0;")
                    logic.append("        condition_{} = (current_price < ma20);  // Price below MA20".format(i))
                    logic.append("    }")
                    logic.append("")
                elif 'dip' in cond_type.lower() and 'peak' in cond_type.lower():
                    # Price dip from recent peak (volatility harvesting)
                    lookback = "lookback_period_" if hasattr(strategy, 'parameters') and 'lookback_period' in strategy.parameters else "24"
                    logic.append(f"    // Volatility: Buy on {value}% dip from recent peak")
                    logic.append(f"    const int lookback = {lookback};")
                    logic.append("    bool condition_{} = false;".format(i))
                    logic.append("    ")
                    logic.append("    if (idx >= lookback) {")
                    logic.append("        // Find recent peak")
                    logic.append("        double recent_peak = data.close[idx - lookback];")
                    logic.append("        for (size_t j = idx - lookback + 1; j < idx; j++) {")
                    logic.append("            if (data.close[j] > recent_peak) recent_peak = data.close[j];")
                    logic.append("        }")
                    logic.append("        ")
                    logic.append(f"        // Check if current price is {value}% below peak")
                    logic.append(f"        double dip_threshold = recent_peak * (1.0 - {value} / 100.0);")
                    logic.append("        condition_{} = (current_price <= dip_threshold);".format(i))
                    logic.append("    }")
                    logic.append("")
                else:
                    logic.append(f"    bool condition_{i} = true;  // {cond_type} (simplified)")
                    logic.append("")
            else:
                # Handle Condition object (has .indicator, .threshold attributes)
                if hasattr(cond, 'indicator'):
                    cond_type = cond.indicator
                    value = cond.threshold

                    # Check for volatility dip/peak conditions
                    if 'dip' in cond_type.lower() and 'peak' in cond_type.lower():
                        lookback = "lookback_period_" if hasattr(strategy, 'parameters') and 'lookback_period' in strategy.parameters else "24"
                        logic.append(f"    // Volatility: Buy on {value}% dip from recent peak")
                        logic.append(f"    const int lookback = {lookback};")
                        logic.append("    bool condition_{} = false;".format(i))
                        logic.append("    ")
                        logic.append("    if (idx >= lookback) {")
                        logic.append("        // Find recent peak")
                        logic.append("        double recent_peak = data.close[idx - lookback];")
                        logic.append("        for (size_t j = idx - lookback + 1; j < idx; j++) {")
                        logic.append("            if (data.close[j] > recent_peak) recent_peak = data.close[j];")
                        logic.append("        }")
                        logic.append("        ")
                        logic.append(f"        // Check if current price is {value}% below peak")
                        logic.append(f"        double dip_threshold = recent_peak * (1.0 - {value} / 100.0);")
                        logic.append("        condition_{} = (current_price <= dip_threshold);".format(i))
                        logic.append("    }")
                        logic.append("")
                    else:
                        logic.append(f"    bool condition_{i} = true;  // {cond_type} (not yet implemented)")
                        logic.append("")
                else:
                    logic.append(f"    bool condition_{i} = true;  // Condition (simplified)")
                    logic.append("")

        # Combine conditions
        num_conditions = len(strategy.buy_conditions)
        if num_conditions > 0:
            condition_names = [f"condition_{i}" for i in range(num_conditions)]
            # Default to AND logic if not specified
            combine_op = " && " if getattr(strategy, 'buy_logic', 'AND') == "AND" else " || "
            logic.append(f"    return {combine_op.join(condition_names)};")
        else:
            logic.append("    return false;")

        return "\n".join(logic)

    def _generate_sell_logic(self, strategy: StrategyDefinition) -> str:
        """Generate sell logic using ACTUAL MarketData and Position structure"""

        # Default logic if no conditions
        if not strategy.sell_conditions:
            return '''    // No sell conditions defined
    double current_price = data.close[idx];
    double profit_pct = ((current_price - position.buy_price) / position.buy_price) * 100.0;

    // Default: sell at 3% profit
    return profit_pct >= 3.0;
'''

        logic = []
        logic.append("    // Get current price and calculate profit")
        logic.append("    double current_price = data.close[idx];")
        logic.append("    double profit_pct = ((current_price - position.buy_price) / position.buy_price) * 100.0;")
        logic.append("")

        # Generate conditions
        for i, cond in enumerate(strategy.sell_conditions):
            if isinstance(cond, dict):
                cond_type = cond.get('type', cond.get('indicator', ''))
                value = cond.get('value', cond.get('threshold', 0))

                if 'rsi' in cond_type.lower():
                    # Determine comparison operator based on condition type
                    is_below = 'below' in cond_type.lower() or 'oversold' in cond_type.lower()
                    operator = '<' if is_below else '>'
                    condition_desc = 'oversold' if is_below else 'overbought'

                    # Use rsi_period parameter if available, else default to 14
                    rsi_period = "rsi_period_" if hasattr(strategy, 'parameters') and 'rsi_period' in strategy.parameters else "14"

                    logic.append(f"    // RSI {condition_desc} sell condition: RSI {operator} {value}")
                    logic.append(f"    const int rsi_period = {rsi_period};")
                    logic.append("    double rsi = 50.0;  // Default neutral")
                    logic.append("    ")
                    logic.append("    if (idx >= rsi_period) {")
                    logic.append("        double gains = 0.0, losses = 0.0;")
                    logic.append("        ")
                    logic.append("        // Calculate average gains and losses over RSI period")
                    logic.append("        for (size_t i = idx - rsi_period + 1; i <= idx; i++) {")
                    logic.append("            double change = data.close[i] - data.close[i-1];")
                    logic.append("            if (change > 0) gains += change;")
                    logic.append("            else losses += -change;")
                    logic.append("        }")
                    logic.append("        ")
                    logic.append("        double avg_gain = gains / rsi_period;")
                    logic.append("        double avg_loss = losses / rsi_period;")
                    logic.append("        ")
                    logic.append("        // Calculate RSI")
                    logic.append("        if (avg_loss > 0.000001) {  // Avoid division by zero")
                    logic.append("            double rs = avg_gain / avg_loss;")
                    logic.append("            rsi = 100.0 - (100.0 / (1.0 + rs));")
                    logic.append("        } else if (avg_gain > 0) {")
                    logic.append("            rsi = 100.0;  // All gains, no losses")
                    logic.append("        } else {")
                    logic.append("            rsi = 0.0;  // No movement")
                    logic.append("        }")
                    logic.append("    }")
                    logic.append(f"    ")
                    logic.append(f"    bool condition_{i} = (rsi {operator} {value});")
                    logic.append("")
                elif 'profit' in cond_type.lower():
                    logic.append(f"    bool condition_{i} = (profit_pct >= {value});")
                    logic.append("")
                elif 'rise' in cond_type.lower() and 'entry' in cond_type.lower():
                    # Volatility: Sell when price rises X% from entry
                    logic.append(f"    // Volatility: Sell when price rises {value}% from entry")
                    logic.append(f"    bool condition_{i} = (profit_pct >= {value});")
                    logic.append("")
                else:
                    logic.append(f"    bool condition_{i} = true;  // {cond_type} (simplified)")
                    logic.append("")
            else:
                # Handle Condition object for sell
                if hasattr(cond, 'indicator'):
                    cond_type = cond.indicator
                    value = cond.threshold

                    # Check for volatility rise from entry
                    if 'rise' in cond_type.lower() and 'entry' in cond_type.lower():
                        logic.append(f"    // Volatility: Sell when price rises {value}% from entry")
                        logic.append(f"    bool condition_{i} = (profit_pct >= {value});")
                        logic.append("")
                    elif 'profit' in cond_type.lower():
                        logic.append(f"    bool condition_{i} = (profit_pct >= {value});")
                        logic.append("")
                    else:
                        logic.append(f"    bool condition_{i} = (profit_pct >= 3.0);  // {cond_type} default")
                        logic.append("")
                else:
                    logic.append(f"    bool condition_{i} = (profit_pct >= 3.0);  // Default profit target")
                    logic.append("")

        # Combine conditions
        num_conditions = len(strategy.sell_conditions)
        if num_conditions > 0:
            condition_names = [f"condition_{i}" for i in range(num_conditions)]
            # Default to OR logic for sell conditions (exit on any condition)
            combine_op = " && " if getattr(strategy, 'sell_logic', 'OR') == "AND" else " || "
            logic.append(f"    return {combine_op.join(condition_names)};")
        else:
            logic.append("    return profit_pct >= 3.0;")

        return "\n".join(logic)

    def _get_cpp_type(self, param_type: str) -> str:
        """Map parameter type to C++ type"""
        type_map = {
            "int": "int",
            "float": "double",
            "double": "double",
            "string": "std::string",
            "bool": "bool"
        }
        return type_map.get(param_type, "double")

    def _format_cpp_value(self, value, param_type: str) -> str:
        """Format value for C++ code"""
        if param_type == "string":
            return f'"{value}"'
        elif param_type == "bool":
            return "true" if value else "false"
        elif param_type in ["float", "double"]:
            return f"{float(value)}"
        else:
            return str(value)
