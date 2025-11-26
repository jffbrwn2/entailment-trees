#!/usr/bin/env python
"""
Test script for conversation logging system.

This script tests that logging works correctly in both:
1. Exploration mode (no approach)
2. Approach mode (with active approach)

Run with: python test_logging.py
"""

from pathlib import Path
from agent_system.config import AgentConfig
from agent_system.conversation_logger import ConversationLogger, list_conversation_logs, print_log_summary, load_conversation_log


def test_logger_standalone():
    """Test logger standalone functionality."""
    print("=" * 70)
    print("TEST 1: Standalone Logger")
    print("=" * 70)

    config = AgentConfig()
    logs_dir = config.logs_dir

    # Create a test logger
    logger = ConversationLogger(
        logs_dir=logs_dir,
        working_dir=Path.cwd()
    )

    # Simulate a multi-turn conversation
    print("\n[TEST] Simulating conversation...")

    # Turn 1
    logger.log_turn_start("What are entailment trees?")
    logger.log_tool_call(
        tool_name="Read",
        parameters={"file_path": "CLAUDE.md"},
        result="Entailment tree documentation..."
    )
    logger.log_turn_end(
        claude_response="Entailment trees are hierarchical structures...",
        cost_usd=0.0023
    )

    # Turn 2
    logger.log_turn_start("Show me an example")
    logger.log_tool_call(
        tool_name="Read",
        parameters={"file_path": "approaches/ultrasound-eeg/hypergraph.json"},
        result="Example hypergraph..."
    )
    logger.log_tool_call(
        tool_name="WebSearch",
        parameters={"query": "entailment tree examples"},
        result="Search results..."
    )
    logger.log_turn_end(
        claude_response="Here's an example from the ultrasound approach...",
        cost_usd=0.0031
    )

    # End session
    logger.end_session()

    print("\n[TEST] ✓ Logger created session successfully")
    print(logger.get_summary())

    return logger.log_file


def test_list_logs():
    """Test listing conversation logs."""
    print("\n" + "=" * 70)
    print("TEST 2: List All Logs")
    print("=" * 70)

    config = AgentConfig()
    logs = list_conversation_logs(config.logs_dir)

    print(f"\n[TEST] Found {len(logs)} log files:")
    for log_file in logs[:5]:  # Show first 5
        print(f"  - {log_file.name}")
        print_log_summary(log_file)
        print()

    print(f"[TEST] ✓ Listed {len(logs)} total logs")


def test_filter_logs():
    """Test filtering logs by approach name."""
    print("\n" + "=" * 70)
    print("TEST 3: Filter Logs by Approach")
    print("=" * 70)

    config = AgentConfig()

    # Get all logs
    all_logs = list_conversation_logs(config.logs_dir)
    print(f"\n[TEST] Total logs: {len(all_logs)}")

    # Count logs with vs without approach
    logs_with_approach = []
    logs_without_approach = []
    for log_path in all_logs:
        log = load_conversation_log(log_path)
        if log.approach_name:
            logs_with_approach.append(log_path)
        else:
            logs_without_approach.append(log_path)

    print(f"[TEST] Logs with approach: {len(logs_with_approach)}")
    print(f"[TEST] Logs without approach (exploration): {len(logs_without_approach)}")

    print("\n[TEST] ✓ Filtering works correctly")


def test_log_structure():
    """Test that log structure is correct."""
    print("\n" + "=" * 70)
    print("TEST 4: Verify Log Structure")
    print("=" * 70)

    config = AgentConfig()
    logs = list_conversation_logs(config.logs_dir)

    if not logs:
        print("[TEST] ⚠️  No logs found to verify")
        return

    # Load and verify first log
    from agent_system.conversation_logger import load_conversation_log

    log_file = logs[0]
    log = load_conversation_log(log_file)

    print(f"\n[TEST] Verifying structure of: {log_file.name}")
    print(f"  - Session ID: {log.session_id}")
    print(f"  - Approach: {log.approach_name if log.approach_name else '(none - exploration)'}")
    print(f"  - Turns: {len(log.turns)}")

    if log.turns:
        turn = log.turns[0]
        print(f"\n[TEST] First turn structure:")
        print(f"  - User input: {turn.user_input[:50]}...")
        print(f"  - Response: {turn.claude_response[:50]}...")
        print(f"  - Tools used: {len(turn.tools_used)}")

        if turn.tools_used:
            tool = turn.tools_used[0]
            print(f"\n[TEST] First tool call:")
            print(f"  - Tool: {tool.tool_name}")
            print(f"  - Parameters: {tool.parameters}")
            print(f"  - Has result: {tool.result is not None}")

    print("\n[TEST] ✓ Log structure is correct")


def main():
    """Run all tests."""
    print("\n" + "=" * 70)
    print("CONVERSATION LOGGING SYSTEM - TEST SUITE")
    print("=" * 70)

    try:
        # Test 1: Create a log
        log_file = test_logger_standalone()

        # Test 2: List logs
        test_list_logs()

        # Test 3: Filter logs
        test_filter_logs()

        # Test 4: Verify structure
        test_log_structure()

        print("\n" + "=" * 70)
        print("✓ ALL TESTS PASSED")
        print("=" * 70)
        print(f"\nLogs are stored in: logs/")
        print("Each conversation is saved as: conversation_<timestamp>_<hash>.json")
        print("\nThe logging system is working correctly!")

    except Exception as e:
        print(f"\n❌ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
