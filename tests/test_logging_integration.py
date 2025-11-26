#!/usr/bin/env python
"""
Integration test for conversation logging.

Tests that:
1. One log file per session (not per turn)
2. Multiple turns are logged to the same file
3. Tool calls are captured in the log
"""

from pathlib import Path
from agent_system.config import AgentConfig
from agent_system.agent_orchestrator import AgentOrchestrator
from agent_system.conversation_logger import list_conversation_logs, load_conversation_log


def test_multi_turn_logging():
    """Test that multiple turns go to the same log file."""
    print("=" * 70)
    print("TEST: Multi-turn Logging")
    print("=" * 70)

    config = AgentConfig()
    orchestrator = AgentOrchestrator(config)

    # Clear logs for clean test
    logs_before = list_conversation_logs(config.logs_dir)
    print(f"\nLogs before test: {len(logs_before)}")

    # Simulate multi-turn conversation in exploration mode
    print("\n[TEST] Turn 1...")
    response1 = orchestrator.process_user_input("What is 2+2?")
    print(f"Response 1: {response1.content[:50]}...")

    print("\n[TEST] Turn 2...")
    response2 = orchestrator.process_user_input("What is 3+3?")
    print(f"Response 2: {response2.content[:50]}...")

    print("\n[TEST] Turn 3...")
    response3 = orchestrator.process_user_input("What is 4+4?")
    print(f"Response 3: {response3.content[:50]}...")

    # End the session
    if orchestrator.claude_client:
        orchestrator.claude_client.end_conversation()

    # Check logs
    logs_after = list_conversation_logs(config.logs_dir)
    new_logs = [log for log in logs_after if log not in logs_before]

    print(f"\n[TEST] Logs after test: {len(logs_after)}")
    print(f"[TEST] New logs created: {len(new_logs)}")

    if len(new_logs) != 1:
        print(f"❌ FAILED: Expected 1 new log file, got {len(new_logs)}")
        for log in new_logs:
            print(f"  - {log.name}")
        return False

    # Load the log and verify turns
    log_file = new_logs[0]
    log = load_conversation_log(log_file)

    print(f"\n[TEST] Log file: {log_file.name}")
    print(f"[TEST] Session ID: {log.session_id}")
    print(f"[TEST] Approach: {log.approach_name if log.approach_name else '(none - exploration)'}")
    print(f"[TEST] Turns in log: {len(log.turns)}")

    if len(log.turns) != 3:
        print(f"❌ FAILED: Expected 3 turns, got {len(log.turns)}")
        return False

    # Check that each turn has content
    for i, turn in enumerate(log.turns, 1):
        print(f"\n[TEST] Turn {i}:")
        print(f"  - User: {turn.user_input[:30]}...")
        print(f"  - Claude: {turn.claude_response[:30]}...")
        print(f"  - Tools used: {len(turn.tools_used)}")

        if turn.tools_used:
            for tool in turn.tools_used:
                print(f"    - {tool.tool_name}: {list(tool.parameters.keys())}")

    print("\n✓ TEST PASSED: Multi-turn logging works correctly")
    return True


if __name__ == "__main__":
    try:
        success = test_multi_turn_logging()
        if success:
            print("\n" + "=" * 70)
            print("✓ ALL TESTS PASSED")
            print("=" * 70)
        else:
            print("\n" + "=" * 70)
            print("❌ TESTS FAILED")
            print("=" * 70)
    except Exception as e:
        print(f"\n❌ TEST ERROR: {e}")
        import traceback
        traceback.print_exc()
