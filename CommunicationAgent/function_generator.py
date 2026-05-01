#!/usr/bin/env python3
"""
Function Generator with Self-Testing
Generates new functions when needed, tests them, and adds to bot_actions.py
"""

import os
import sys
import anthropic
import json
import ast
from typing import Dict, Optional
from pathlib import Path


class FunctionGenerator:
    """Generates and tests new functions dynamically"""

    def __init__(self):
        self.api_key = os.getenv("ANTHROPIC_API_KEY")
        if not self.api_key:
            raise ValueError("ANTHROPIC_API_KEY not set")

        self.client = anthropic.Anthropic(api_key=self.api_key)
        self.bot_actions_file = Path(__file__).parent / "bot_actions.py"
        self.test_file = Path(__file__).parent / "test_bot_actions.py"

    async def generate_and_test_function(self, user_request: str) -> Dict:
        """
        Generate a new function based on user request, test it, and save if it works.

        Args:
            user_request: What the user wants to do (e.g., "optimize strategy parameters")

        Returns:
            Dict with success, function_name, and message
        """

        print(f"\n🔧 Generating new function for: {user_request}")

        # Step 1: Generate function code
        function_code = await self._generate_function_code(user_request)
        if not function_code:
            return {"success": False, "error": "Failed to generate function code"}

        print(f"✓ Generated function code ({len(function_code)} chars)")

        # Step 2: Generate test code
        test_code = await self._generate_test_code(function_code, user_request)
        if not test_code:
            return {"success": False, "error": "Failed to generate test code"}

        print(f"✓ Generated test code ({len(test_code)} chars)")

        # Step 3: Run the test
        test_result = await self._run_test(function_code, test_code)

        if not test_result["success"]:
            return {
                "success": False,
                "error": f"Test failed: {test_result.get('error')}",
                "function_code": function_code,
                "test_code": test_code
            }

        print(f"✓ Test passed!")

        # Step 4: Save function to bot_actions.py
        function_name = self._extract_function_name(function_code)
        self._add_function_to_bot_actions(function_code)

        print(f"✓ Saved function '{function_name}' to bot_actions.py")

        # Step 5: Save test to test_bot_actions.py
        self._add_test_to_test_file(test_code, function_name)

        print(f"✓ Saved test to test_bot_actions.py")

        return {
            "success": True,
            "function_name": function_name,
            "message": f"Created and tested new function: {function_name}"
        }

    async def _generate_function_code(self, user_request: str) -> Optional[str]:
        """Generate function code using Claude"""

        prompt = f"""Generate a Python async function for BotActions class that handles this user request:
"{user_request}"

Available resources in BotActions:
- self.store (StrategyStore) - database operations for strategies
- self.executor (ActionExecutor) - has methods like:
  - run_backtest(strategy_name, coins, days)
  - optimize_strategy(strategy_name, coins, days) - optimization grid should be set on strategy first
  - deploy_strategy_for_backtest(strategy_name)
  - deploy_bot(strategy_name, coins, ...)

The ActionExecutor communicates with:
- BacktestAgent (C++ backtester) - for backtests and optimizations
- BotBuildAgent (C# deployer) - for live bots

Requirements:
1. Must be an async method of BotActions class
2. Use self.store and self.executor to access agents
3. Return a string that can be sent to the user in Telegram
4. Follow the same pattern as existing functions in bot_actions.py
5. Use proper error handling
6. Include docstring
7. For optimization: update strategy.optimization_grid first, then call executor.optimize_strategy()

Example existing function:
```python
async def list_all_strategies(self) -> str:
    \"\"\"List all strategies from database\"\"\"
    await self._ensure_connected()
    strategies = await self.store.list_all()

    if not strategies:
        return "📋 No strategies in database yet."

    result = f"📋 **{{len(strategies)}} Strategies:**\\n\\n"
    for s in strategies:
        result += f"• **{{s.name}}** v{{s.version}} ({{s.type}})\\n"
    return result
```

Generate ONLY the function code (no explanations, no imports):
"""

        try:
            response = self.client.messages.create(
                model="claude-opus-4-7",
                max_tokens=2000,
                messages=[{"role": "user", "content": prompt}]
            )

            code = response.content[0].text.strip()

            # Remove markdown code blocks if present
            if code.startswith("```python"):
                code = code[len("```python"):].strip()
            if code.endswith("```"):
                code = code[:-3].strip()

            return code

        except Exception as e:
            print(f"Error generating function: {e}")
            return None

    async def _generate_test_code(self, function_code: str, user_request: str) -> Optional[str]:
        """Generate test code for the function"""

        function_name = self._extract_function_name(function_code)

        prompt = f"""Generate a test function for this BotActions method:

```python
{function_code}
```

User request was: "{user_request}"

Requirements:
1. Test function should be named test_{function_name}
2. Should be async
3. Should test the main functionality
4. Should verify the result is a non-empty string
5. Use BotActions() instance
6. Follow pytest async pattern

Example test:
```python
async def test_list_all_strategies():
    actions = BotActions()
    result = await actions.list_all_strategies()
    assert isinstance(result, str)
    assert len(result) > 0
    assert "Strategies" in result or "No strategies" in result
```

Generate ONLY the test function code (no explanations, no imports):
"""

        try:
            response = self.client.messages.create(
                model="claude-opus-4-7",
                max_tokens=2000,
                messages=[{"role": "user", "content": prompt}]
            )

            code = response.content[0].text.strip()

            # Remove markdown code blocks if present
            if code.startswith("```python"):
                code = code[len("```python"):].strip()
            if code.endswith("```"):
                code = code[:-3].strip()

            return code

        except Exception as e:
            print(f"Error generating test: {e}")
            return None

    async def _run_test(self, function_code: str, test_code: str) -> Dict:
        """Run the test in an isolated environment"""

        try:
            # Create isolated namespace with necessary imports
            test_namespace = {
                "__name__": "__main__",
                "asyncio": __import__("asyncio"),
            }

            # Add bot_actions module to path
            sys.path.insert(0, str(Path(__file__).parent.parent))

            # Import required modules
            from bot_actions import BotActions

            test_namespace["BotActions"] = BotActions

            # Execute function code in namespace (add to BotActions)
            # We'll inject it temporarily for testing
            exec(f"""
import types

# Extract function from code
{function_code}

# Get function name
import re
func_name = re.search(r'async def (\\w+)', '''{function_code}''').group(1)

# Add to BotActions
setattr(BotActions, func_name, locals()[func_name])
""", test_namespace)

            # Execute test code
            exec(test_code, test_namespace)

            # Find and run the test function
            import asyncio
            test_func = None
            for name, obj in test_namespace.items():
                if name.startswith("test_") and callable(obj):
                    test_func = obj
                    break

            if not test_func:
                return {"success": False, "error": "No test function found"}

            # Run the test
            asyncio.run(test_func())

            return {"success": True}

        except AssertionError as e:
            return {"success": False, "error": f"Assertion failed: {e}"}
        except Exception as e:
            return {"success": False, "error": f"Test execution failed: {e}"}
        finally:
            # Clean up sys.path
            if str(Path(__file__).parent.parent) in sys.path:
                sys.path.remove(str(Path(__file__).parent.parent))

    def _extract_function_name(self, function_code: str) -> str:
        """Extract function name from code"""
        import re
        match = re.search(r'async def (\w+)', function_code)
        if match:
            return match.group(1)
        return "unknown_function"

    def _add_function_to_bot_actions(self, function_code: str):
        """Add function to bot_actions.py"""

        # Read current file
        with open(self.bot_actions_file, 'r') as f:
            content = f.read()

        # Find the last method in BotActions class
        # Add new function before the last closing brace

        # Simple approach: add before the final lines
        lines = content.split('\n')

        # Find where to insert (before last non-empty line)
        insert_index = len(lines) - 1
        while insert_index > 0 and not lines[insert_index].strip():
            insert_index -= 1

        # Add function with proper indentation
        function_lines = function_code.split('\n')
        indented_function = '\n'.join('    ' + line if line.strip() else line
                                       for line in function_lines)

        lines.insert(insert_index, '\n' + indented_function + '\n')

        # Write back
        with open(self.bot_actions_file, 'w') as f:
            f.write('\n'.join(lines))

    def _add_test_to_test_file(self, test_code: str, function_name: str):
        """Add test to test_bot_actions.py"""

        # Create test file if it doesn't exist
        if not self.test_file.exists():
            with open(self.test_file, 'w') as f:
                f.write("""#!/usr/bin/env python3
\"\"\"
Tests for bot_actions.py - dynamically generated and manually written tests
\"\"\"

import asyncio
import pytest
from bot_actions import BotActions


""")

        # Read current file
        with open(self.test_file, 'r') as f:
            content = f.read()

        # Check if test already exists
        if f"def test_{function_name}" in content:
            print(f"Test for {function_name} already exists, skipping")
            return

        # Add test at the end
        with open(self.test_file, 'a') as f:
            f.write('\n\n')
            f.write(test_code)
            f.write('\n')


if __name__ == "__main__":
    # Test the generator
    import asyncio

    async def test():
        generator = FunctionGenerator()
        result = await generator.generate_and_test_function(
            "Show me the best performing strategy based on backtests"
        )
        print(json.dumps(result, indent=2))

    asyncio.run(test())
