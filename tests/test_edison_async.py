"""
Test async Edison task submission and logging.
"""

import asyncio
import json
from pathlib import Path
import sys
import os

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from agent_system.claude_client import (
    _log_edison_task,
    _update_edison_task_status
)


async def test_task_logging():
    """Test task logging functionality."""
    print("Testing Edison task logging...")

    # Use a temp directory for testing
    test_dir = Path(__file__).parent / "temp_edison_test"
    test_dir.mkdir(exist_ok=True)

    # Test logging a task
    task_id = "test_task_123"
    _log_edison_task(str(test_dir), task_id, "literature", "Test query")

    # Check log was created
    log_path = test_dir / "references" / "edison_tasks.json"
    assert log_path.exists(), "Log file should be created"

    # Read and verify log
    with open(log_path) as f:
        tasks = json.load(f)

    assert len(tasks) == 1, "Should have one task"
    assert tasks[0]["task_id"] == task_id
    assert tasks[0]["type"] == "literature"
    assert tasks[0]["query"] == "Test query"
    assert tasks[0]["status"] == "pending"

    print("✓ Task logging works")

    # Test updating status
    _update_edison_task_status(str(test_dir), task_id, "success", "Test answer")

    with open(log_path) as f:
        tasks = json.load(f)

    assert tasks[0]["status"] == "success"
    assert tasks[0]["answer"] == "Test answer"
    assert "completed_at" in tasks[0]

    print("✓ Status update works")

    # Clean up
    log_path.unlink()
    (test_dir / "references").rmdir()
    test_dir.rmdir()

    print("\n✅ All tests passed!")


if __name__ == "__main__":
    asyncio.run(test_task_logging())
