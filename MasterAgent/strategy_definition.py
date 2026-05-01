"""Strategy Definition System - Parse natural language strategy descriptions"""

import re
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field, asdict
from enum import Enum
import json


class IndicatorType(Enum):
    """Supported technical indicators"""
    SMA = "sma"
    EMA = "ema"
    RSI = "rsi"
    MACD = "macd"
    BOLLINGER = "bollinger"
    ATR = "atr"
    VOLUME = "volume"
    STOCHASTIC = "stochastic"
    ADX = "adx"
    ROC = "roc"
    PRICE = "price"


class ConditionOperator(Enum):
    """Comparison operators"""
    GREATER = ">"
    LESS = "<"
    GREATER_EQUAL = ">="
    LESS_EQUAL = "<="
    EQUAL = "=="
    CROSSES_ABOVE = "crosses_above"
    CROSSES_BELOW = "crosses_below"
    BREAKS_ABOVE = "breaks_above"
    BREAKS_BELOW = "breaks_below"


class LogicOperator(Enum):
    """Logic operators for combining conditions"""
    AND = "AND"
    OR = "OR"


@dataclass
class Parameter:
    """Represents a configurable strategy parameter"""
    name: str
    value: Any
    type: str  # "int", "float", "string", "bool"
    min_value: Optional[float] = None
    max_value: Optional[float] = None
    optimizable: bool = True
    description: str = ""

    def to_dict(self) -> Dict:
        return {k: v for k, v in asdict(self).items() if v is not None}


@dataclass
class Condition:
    """Represents a buy/sell condition"""
    indicator: str
    operator: str
    threshold: Any
    indicator_params: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict:
        return asdict(self)


@dataclass
class StrategyDefinition:
    """Complete strategy definition with all parameters"""
    name: str
    description: str
    buy_conditions: List[Condition] = field(default_factory=list)
    sell_conditions: List[Condition] = field(default_factory=list)
    buy_logic: str = "AND"  # AND or OR
    sell_logic: str = "AND"
    parameters: Dict[str, Parameter] = field(default_factory=dict)
    version: str = "1.0"

    def add_parameter(self, name: str, value: Any, param_type: str,
                     min_val: float = None, max_val: float = None,
                     optimizable: bool = True, description: str = ""):
        """Add a configurable parameter"""
        self.parameters[name] = Parameter(
            name=name,
            value=value,
            type=param_type,
            min_value=min_val,
            max_value=max_val,
            optimizable=optimizable,
            description=description
        )

    def to_dict(self) -> Dict:
        return {
            "name": self.name,
            "description": self.description,
            "version": self.version,
            "buy_conditions": [c.to_dict() for c in self.buy_conditions],
            "sell_conditions": [c.to_dict() for c in self.sell_conditions],
            "buy_logic": self.buy_logic,
            "sell_logic": self.sell_logic,
            "parameters": {k: v.to_dict() for k, v in self.parameters.items()}
        }

    def to_json(self, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), indent=indent)

    @classmethod
    def from_dict(cls, data: Dict) -> 'StrategyDefinition':
        strategy = cls(
            name=data["name"],
            description=data["description"],
            version=data.get("version", "1.0"),
            buy_logic=data.get("buy_logic", "AND"),
            sell_logic=data.get("sell_logic", "AND")
        )

        # Reconstruct conditions
        strategy.buy_conditions = [
            Condition(**c) for c in data.get("buy_conditions", [])
        ]
        strategy.sell_conditions = [
            Condition(**c) for c in data.get("sell_conditions", [])
        ]

        # Reconstruct parameters
        strategy.parameters = {
            k: Parameter(**v) for k, v in data.get("parameters", {}).items()
        }

        return strategy


class StrategyParser:
    """Parse natural language strategy descriptions into StrategyDefinition"""

    # Pattern matching rules
    INDICATOR_PATTERNS = {
        r'(\d+)[-\s]day\s+sma': ('sma', 'sma_period'),
        r'(\d+)[-\s]period\s+sma': ('sma', 'sma_period'),
        r'sma\s*\(?\s*(\d+)\s*\)?': ('sma', 'sma_period'),
        r'(\d+)[-\s]day\s+ema': ('ema', 'ema_period'),
        r'ema\s*\(?\s*(\d+)\s*\)?': ('ema', 'ema_period'),
        r'rsi\s*\(?\s*(\d+)\s*\)?': ('rsi', 'rsi_period'),
        r'(\d+)[-\s]period\s+rsi': ('rsi', 'rsi_period'),
        r'bollinger\s+bands?\s*\(?\s*(\d+)\s*,?\s*(\d+\.?\d*)\s*\)?': ('bollinger', 'bb_period'),
        r'atr\s*\(?\s*(\d+)\s*\)?': ('atr', 'atr_period'),
    }

    THRESHOLD_PATTERNS = {
        r'rsi\s*<\s*(\d+)': ('rsi_oversold', 'float'),
        r'rsi\s*>\s*(\d+)': ('rsi_overbought', 'float'),
        r'volume\s*>\s*(\d+\.?\d*)\s*x\s+average': ('volume_multiplier', 'float'),
        r'profit\s*>\s*(\d+\.?\d*)%': ('profit_target_pct', 'float'),
        r'drops?\s*(\d+\.?\d*)%': ('stop_loss_pct', 'float'),
    }

    POSITION_PATTERNS = {
        r'(\d+)%\s+of\s+portfolio': ('position_size_value', 'fixed_pct'),
        r'max\s+(\d+)\s+position[s]?\s+per\s+coin': ('max_positions_per_coin', 'int'),
        r'position\s+size:\s*(\d+\.?\d*)%': ('position_size_value', 'fixed_pct'),
    }

    def __init__(self):
        pass

    def parse(self, description: str, strategy_name: str = None) -> StrategyDefinition:
        """Parse natural language description into StrategyDefinition

        Args:
            description: Natural language strategy description
            strategy_name: Optional strategy name (auto-generated if not provided)

        Returns:
            StrategyDefinition with all extracted parameters and conditions
        """
        # Create strategy definition
        if not strategy_name:
            strategy_name = self._generate_name(description)

        strategy = StrategyDefinition(
            name=strategy_name,
            description=description.strip()
        )

        # Split into buy and sell sections
        buy_section, sell_section = self._split_buy_sell(description)

        # Parse buy conditions
        strategy.buy_conditions, buy_params = self._parse_conditions(buy_section, "buy")
        strategy.buy_logic = self._extract_logic_operator(buy_section)

        # Parse sell conditions
        strategy.sell_conditions, sell_params = self._parse_conditions(sell_section, "sell")
        strategy.sell_logic = self._extract_logic_operator(sell_section)

        # Merge parameters
        all_params = {**buy_params, **sell_params}

        # Extract position management parameters
        position_params = self._extract_position_params(description)
        all_params.update(position_params)

        # Add all parameters to strategy
        for name, (value, param_type, min_val, max_val, desc) in all_params.items():
            strategy.add_parameter(name, value, param_type, min_val, max_val, True, desc)

        return strategy

    def _generate_name(self, description: str) -> str:
        """Generate strategy name from description"""
        # Extract key words
        words = description.lower().split()
        keywords = []

        for word in words:
            if word in ['rsi', 'sma', 'ema', 'macd', 'bollinger', 'momentum', 'volatility', 'trend']:
                keywords.append(word.upper())

        if not keywords:
            return "CustomStrategy"

        return "_".join(keywords[:3])

    def _split_buy_sell(self, description: str) -> tuple:
        """Split description into buy and sell sections"""
        lines = description.lower().split('\n')

        buy_section = []
        sell_section = []
        current_section = None

        for line in lines:
            line = line.strip()
            if not line or line.startswith('#'):
                continue

            # Buy/entry triggers
            if 'buy when' in line or 'buy' in line.split()[0:1] or 'entry' in line or 'open' in line:
                current_section = 'buy'
                buy_section.append(line)
            # Sell/exit triggers
            elif 'sell when' in line or 'sell' in line.split()[0:1] or 'exit' in line or 'close' in line:
                current_section = 'sell'
                sell_section.append(line)
            elif current_section == 'buy':
                buy_section.append(line)
            elif current_section == 'sell':
                sell_section.append(line)
            else:
                # If no section yet, treat as buy by default (unless it mentions sell/profit/exit)
                if 'sell' in line or 'profit' in line or 'exit' in line or 'close' in line:
                    sell_section.append(line)
                    current_section = 'sell'
                else:
                    buy_section.append(line)
                    current_section = 'buy'

        return '\n'.join(buy_section), '\n'.join(sell_section)

    def _parse_conditions(self, section: str, condition_type: str) -> tuple:
        """Parse conditions and extract parameters

        Returns:
            (conditions, parameters)
        """
        conditions = []
        parameters = {}

        # Extract RSI conditions
        if 'rsi' in section:
            # RSI period
            period_match = re.search(r'rsi\s*\(?(\d+)\)?', section)
            rsi_period = int(period_match.group(1)) if period_match else 14
            parameters['rsi_period'] = (rsi_period, 'int', 5, 30, "RSI calculation period")

            # RSI thresholds
            if '<' in section:
                threshold_match = re.search(r'rsi\s*<\s*(\d+)', section)
                if threshold_match:
                    threshold = float(threshold_match.group(1))
                    parameters['rsi_oversold'] = (threshold, 'float', 10.0, 40.0, "RSI oversold threshold")
                    conditions.append(Condition('rsi', '<', threshold, {'period': rsi_period}))

            if '>' in section:
                threshold_match = re.search(r'rsi\s*>\s*(\d+)', section)
                if threshold_match:
                    threshold = float(threshold_match.group(1))
                    parameters['rsi_overbought'] = (threshold, 'float', 60.0, 90.0, "RSI overbought threshold")
                    conditions.append(Condition('rsi', '>', threshold, {'period': rsi_period}))

        # Extract SMA/MA conditions (handles "sma", "moving average", "MA", "ma")
        if 'sma' in section or 'moving average' in section or re.search(r'\bma\b', section):
            # Try multiple patterns
            period_match = (
                re.search(r'(\d+)[-\s]day\s+(?:sma|moving average|ma)\b', section) or
                re.search(r'(\d+)[-\s]day\s+ma(?:\.|$| )', section) or
                re.search(r'(?:sma|moving average|ma)\s+(?:for\s+)?(?:the\s+)?last\s+(\d+)\s+day', section) or
                re.search(r'(\d+)[-\s](?:day|hour)\s+(?:sma|moving average|ma)', section)
            )
            if period_match:
                period = int(period_match.group(1))
                parameters[f'ma_period'] = (period, 'int', 5, 200, f"MA period in days")

                if 'above' in section or 'crosses above' in section or 'breaks above' in section:
                    operator = 'crosses_above' if 'crosses' in section else '>'
                    conditions.append(Condition('price', operator, 'ma', {'ma_period': period}))
                elif 'below' in section or 'crosses below' in section:
                    operator = 'crosses_below' if 'crosses' in section else '<'
                    conditions.append(Condition('price', operator, 'ma', {'ma_period': period}))

        # Extract volume conditions
        if 'volume' in section:
            volume_match = re.search(r'volume\s*>\s*(\d+\.?\d*)\s*x', section)
            if volume_match:
                multiplier = float(volume_match.group(1))
                parameters['volume_multiplier'] = (multiplier, 'float', 1.0, 5.0, "Volume multiplier vs average")

                # Volume average period
                avg_match = re.search(r'(\d+)[-\s]period\s+average', section)
                avg_period = int(avg_match.group(1)) if avg_match else 50
                parameters['volume_avg_period'] = (avg_period, 'int', 10, 100, "Volume average period")

                conditions.append(Condition('volume', '>', multiplier, {'avg_period': avg_period}))

        # Extract profit target (handles "profit target", "reaches X% profit", "profit reaches X%")
        if 'profit' in section:
            profit_match = (
                re.search(r'profit\s+target[:\s]+(\d+\.?\d*)%', section) or
                re.search(r'reaches?\s+(\d+\.?\d*)%\s+profit', section) or
                re.search(r'profit\s+reaches?\s+(\d+\.?\d*)%', section) or
                re.search(r'(\d+\.?\d*)%\s+profit\s+target', section) or
                re.search(r'profit\s*(?:>|>=|=)\s*(\d+\.?\d*)%', section)
            )
            if profit_match:
                profit_target = float(profit_match.group(1))
                parameters['profit_target_pct'] = (profit_target, 'float', 1.0, 50.0, "Profit target percentage")
                conditions.append(Condition('profit', '>', profit_target, {}))

        # Extract dip/drop threshold (handles "dropped X%", "X% drop", "dip X%")
        if 'drop' in section or 'dip' in section or 'fell' in section or 'fallen' in section:
            drop_match = (
                re.search(r'drops?\s+(\d+\.?\d*)%', section) or
                re.search(r'dip[s]?\s+(\d+\.?\d*)%', section) or
                re.search(r'dropped\s+(\d+\.?\d*)%', section) or
                re.search(r'(\d+\.?\d*)%\s+(?:drop|dip|from)', section) or
                re.search(r'fell\s+(\d+\.?\d*)%', section)
            )
            if drop_match:
                dip_threshold = float(drop_match.group(1))
                parameters['dip_threshold_pct'] = (dip_threshold, 'float', 1.0, 20.0, "Dip threshold percentage")
                conditions.append(Condition('price_drop', '>', dip_threshold, {}))

        return conditions, parameters

    def _extract_logic_operator(self, section: str) -> str:
        """Extract AND/OR logic operator"""
        section_upper = section.upper()

        # Count AND vs OR
        and_count = section_upper.count(' AND ')
        or_count = section_upper.count(' OR ')

        return "OR" if or_count > and_count else "AND"

    def _extract_position_params(self, description: str) -> Dict:
        """Extract position management parameters"""
        params = {}

        # Position size
        size_match = re.search(r'(\d+\.?\d*)%\s+of\s+portfolio', description.lower())
        if size_match:
            size = float(size_match.group(1))
            params['position_size_value'] = (size, 'float', 1.0, 100.0, "Position size as % of portfolio")
            params['position_size_type'] = ('fixed_pct', 'string', None, None, "Position sizing method")

        # Max positions per coin
        pos_match = re.search(r'max\s+(\d+)\s+position[s]?\s+per\s+coin', description.lower())
        if pos_match:
            max_pos = int(pos_match.group(1))
            params['max_positions_per_coin'] = (max_pos, 'int', 1, 10, "Max positions per coin")

        return params


if __name__ == "__main__":
    # Test the parser
    parser = StrategyParser()

    # Example 1: RSI + Volume strategy
    description1 = """
    Create a momentum strategy:
    - Buy when: RSI(14) < 30 AND volume > 2x average
    - Sell when: RSI(14) > 70 OR profit > 5%
    - Position size: 10% of portfolio
    - Max 1 position per coin
    """

    strategy1 = parser.parse(description1, "RSI_Momentum")
    print("=" * 60)
    print("Strategy 1: RSI Momentum")
    print("=" * 60)
    print(strategy1.to_json())

    # Example 2: SMA Crossover
    description2 = """
    - Buy when: Price breaks above 20-day SMA AND volume > 1.5x average
    - Sell when: Price drops 3% from entry OR crosses below 20-day SMA
    - Position size: 5% of portfolio
    - Max 1 position per coin
    """

    strategy2 = parser.parse(description2)
    print("\n" + "=" * 60)
    print("Strategy 2: SMA Crossover")
    print("=" * 60)
    print(strategy2.to_json())
