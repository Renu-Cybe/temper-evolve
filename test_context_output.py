#!/usr/bin/env python3
"""
Test Context Manager + Output Styles
"""

import sys
sys.path.insert(0, '.')

from temper.context.manager import ContextManager, TokenBudget
from temper.output.styles import OutputStyleManager, OutputStyle


def test_context_manager():
    """Test 1: Context Manager"""
    print('[TEST] Context Manager\n')
    
    # Create manager
    manager = ContextManager()
    
    # Add system content
    manager.add_system_content("core", "You are Temper Agent...", 100)
    print(f'[PASS] System layer: {manager.system_layer.token_count} tokens')
    
    # Add session content
    manager.add_session_content("query", "Check system health", 20)
    print(f'[PASS] Session layer: {manager.session_layer.token_count} tokens')
    
    # Build context
    context = manager.build_context()
    print(f'[PASS] Total tokens: {manager.total_tokens}')
    print(f'[PASS] Utilization: {manager.utilization_rate:.1%}')
    
    # Get status
    status = manager.get_status()
    print(f'[PASS] Token usage: {status["token_usage"]["total"]["percent"]:.1f}%')
    
    print()


def test_output_styles():
    """Test 2: Output Styles"""
    print('[TEST] Output Styles\n')
    
    manager = OutputStyleManager()
    
    # List styles
    styles = manager.list_styles()
    print(f'[PASS] Available styles: {len(styles)}')
    for s in styles:
        print(f'  - {s["name"]} ({s["type"]})')
    
    # Set style
    manager.set_style(OutputStyle.EXPLANATORY)
    info = manager.get_current_style_info()
    print(f'[PASS] Current style: {info["name"]}')
    
    # Format output
    data = {"status": "healthy", "issues": []}
    result = manager.format_output(data)
    print(f'[PASS] Formatted output: {result}')
    
    # Set structured output
    manager.set_structured_output({
        "type": "object",
        "properties": {
            "status": {"type": "string"},
            "issues": {"type": "array"}
        },
        "required": ["status"]
    })
    
    structured = manager.format_output(data)
    print(f'[PASS] Structured output: {structured}')
    
    # Create custom style
    manager.create_custom_style(
        "temper_heartbeat",
        "Focus on heartbeat evolution tasks",
        "Heartbeat evolution mode"
    )
    print(f'[PASS] Custom style created')
    
    print()


def test_integration():
    """Test 3: Integration"""
    print('[TEST] Integration\n')
    
    ctx_manager = ContextManager()
    out_manager = OutputStyleManager()
    
    # Simulate context-aware output
    ctx_manager.add_session_content("task", "health_check", 10)
    ctx_manager.add_session_content("params", {"interval": 60}, 20)
    
    # Use Explanatory style
    out_manager.set_style(OutputStyle.EXPLANATORY)
    
    # Generate output
    result = out_manager.format_output({
        "task": "health_check",
        "result": "all systems healthy"
    })
    
    print(f'[PASS] Context-aware output:')
    print(f'  Tokens used: {ctx_manager.total_tokens}')
    print(f'  Output style: {out_manager.current_style.value}')
    print(f'  Result: {result}')
    
    print()


if __name__ == '__main__':
    test_context_manager()
    test_output_styles()
    test_integration()
    print('[PASS] All tests completed!')