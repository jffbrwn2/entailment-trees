"""
Pytest configuration and shared fixtures.
"""

import pytest
import shutil
from pathlib import Path
from agent_system import HypergraphManager, AgentOrchestrator
from agent_system.config import AgentConfig


@pytest.fixture
def temp_test_dir(tmp_path):
    """Provide a temporary directory for testing."""
    return tmp_path


@pytest.fixture
def test_approach_dir(tmp_path):
    """Create a temporary approach directory."""
    approach_dir = tmp_path / "test_approach"
    approach_dir.mkdir()
    return approach_dir


@pytest.fixture
def hypergraph_manager(test_approach_dir):
    """Provide a HypergraphManager instance."""
    return HypergraphManager(test_approach_dir)


@pytest.fixture
def sample_hypergraph():
    """Provide sample hypergraph data."""
    return {
        "metadata": {
            "name": "Test Approach",
            "description": "Test hypergraph",
            "created": "2024-01-01",
            "version": "1.0"
        },
        "claims": [
            {
                "id": "hypothesis",
                "text": "Test hypothesis",
                "score": 5.0,
                "reasoning": "Initial assumption"
            },
            {
                "id": "c1",
                "text": "First supporting claim",
                "score": 8.0,
                "reasoning": "Well-established"
            }
        ],
        "implications": []
    }


@pytest.fixture
def orchestrator(tmp_path):
    """Provide an AgentOrchestrator with temp config."""
    config = AgentConfig(approaches_dir=tmp_path / "approaches")
    return AgentOrchestrator(config)


@pytest.fixture
def sample_simulation_file(tmp_path):
    """Create a sample simulation file for testing."""
    sim_file = tmp_path / "test_sim.py"
    content = """# Test simulation
import numpy as np

# Key calculation
signal_strength = 1e-12  # Pa
noise_floor = 1e-6       # Pa

# Result
snr = signal_strength / noise_floor
print(f"SNR: {snr}")
print(f"Result: {snr * 100}")
"""
    sim_file.write_text(content)
    return sim_file
