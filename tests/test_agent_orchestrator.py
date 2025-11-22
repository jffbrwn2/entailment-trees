"""
Tests for AgentOrchestrator.
"""

import pytest
from pathlib import Path
from agent_system.agent_orchestrator import AgentOrchestrator, Session
from agent_system.config import AgentConfig


class TestSessionManagement:
    """Test session creation and management."""

    def test_start_approach(self, orchestrator):
        """Test starting a new approach."""
        result = orchestrator.start_approach(
            name="Test Approach",
            initial_claim="Test hypothesis",
            description="Test description"
        )

        assert "session" in result
        assert "hypergraph" in result
        assert "system_prompt" in result

        # Check session info
        assert result["session"]["name"] == "Test Approach"
        assert result["session"]["folder"] == "test_approach"
        assert "path" in result["session"]

        # Check hypergraph was created
        assert result["hypergraph"]["metadata"]["name"] == "Test Approach"
        assert len(result["hypergraph"]["claims"]) == 1

        # Check system prompt is substantial
        assert len(result["system_prompt"]) > 1000
        assert "hypergraph" in result["system_prompt"].lower()

    def test_start_approach_creates_folder(self, orchestrator):
        """Test that starting approach creates folder structure."""
        result = orchestrator.start_approach(
            name="Test Approach",
            initial_claim="Hypothesis"
        )

        folder_path = Path(result["session"]["path"])
        assert folder_path.exists()
        assert (folder_path / "hypergraph.json").exists()
        assert (folder_path / "simulations").exists()
        assert (folder_path / "README.md").exists()

    def test_start_approach_sanitizes_name(self, orchestrator):
        """Test that approach name is sanitized for folder name."""
        result = orchestrator.start_approach(
            name="Test / Approach With Spaces",
            initial_claim="Hypothesis"
        )

        # Should be converted to valid folder name
        folder = result["session"]["folder"]
        assert "/" not in folder
        assert " " not in folder
        assert folder == "test___approach_with_spaces"

    def test_session_tracked(self, orchestrator):
        """Test that session is tracked in orchestrator."""
        orchestrator.start_approach(
            name="Test Approach",
            initial_claim="Hypothesis"
        )

        assert orchestrator.current_session is not None
        assert orchestrator.current_session.approach_name == "Test Approach"
        assert orchestrator.current_session.turn_count == 0


class TestSystemPrompt:
    """Test system prompt generation."""

    def test_system_prompt_without_session_fails(self, orchestrator):
        """Test that getting system prompt without session raises error."""
        with pytest.raises(RuntimeError, match="No active session"):
            orchestrator.get_system_prompt()

    def test_system_prompt_includes_key_info(self, orchestrator):
        """Test that system prompt includes essential information."""
        orchestrator.start_approach(
            name="Test Approach",
            initial_claim="Hypothesis"
        )

        prompt = orchestrator.get_system_prompt()

        # Check for key sections
        assert "Test Approach" in prompt
        assert "hypergraph.json" in prompt
        assert "simulations/" in prompt

        # Check for evidence types
        assert "simulation" in prompt
        assert "literature" in prompt
        assert "calculation" in prompt

        # Check for workflow guidance
        assert "claim" in prompt.lower()
        assert "implication" in prompt.lower()
        assert "evidence" in prompt.lower()

    def test_system_prompt_includes_example(self, orchestrator):
        """Test that system prompt includes example workflow."""
        orchestrator.start_approach(
            name="Test",
            initial_claim="Hypothesis"
        )

        prompt = orchestrator.get_system_prompt()

        # Should have example interaction
        assert "Example" in prompt or "example" in prompt


class TestStatusTracking:
    """Test status and statistics tracking."""

    def test_get_status_no_session(self, orchestrator):
        """Test getting status with no active session."""
        status = orchestrator.get_status()

        assert status["active"] is False

    def test_get_status_with_session(self, orchestrator):
        """Test getting status with active session."""
        orchestrator.start_approach(
            name="Test Approach",
            initial_claim="Hypothesis"
        )

        status = orchestrator.get_status()

        assert status["active"] is True
        assert status["approach"] == "Test Approach"
        assert "folder" in status
        assert status["turns"] == 0
        assert "stats" in status

    def test_get_status_includes_stats(self, orchestrator):
        """Test that status includes hypergraph statistics."""
        orchestrator.start_approach(
            name="Test",
            initial_claim="Hypothesis"
        )

        status = orchestrator.get_status()
        stats = status["stats"]

        assert "num_claims" in stats
        assert "num_implications" in stats
        assert "avg_score" in stats
        assert stats["num_claims"] == 1  # Initial hypothesis

    def test_increment_turn(self, orchestrator):
        """Test incrementing turn counter."""
        orchestrator.start_approach(
            name="Test",
            initial_claim="Hypothesis"
        )

        assert orchestrator.current_session.turn_count == 0

        orchestrator.increment_turn()
        assert orchestrator.current_session.turn_count == 1

        orchestrator.increment_turn()
        assert orchestrator.current_session.turn_count == 2


class TestValidation:
    """Test hypergraph validation."""

    def test_validate_hypergraph_without_session_fails(self, orchestrator):
        """Test that validation without session raises error."""
        with pytest.raises(RuntimeError):
            orchestrator.validate_hypergraph()

    def test_validate_valid_hypergraph(self, orchestrator):
        """Test validating a valid hypergraph."""
        orchestrator.start_approach(
            name="Test",
            initial_claim="Hypothesis"
        )

        result = orchestrator.validate_hypergraph()

        assert result["valid"] is True
        assert len(result["errors"]) == 0

    def test_validate_returns_structure(self, orchestrator):
        """Test that validation returns proper structure."""
        orchestrator.start_approach(
            name="Test",
            initial_claim="Hypothesis"
        )

        result = orchestrator.validate_hypergraph()

        assert "valid" in result
        assert "errors" in result
        assert "warnings" in result
        assert isinstance(result["errors"], list)
        assert isinstance(result["warnings"], list)


class TestConfiguration:
    """Test configuration handling."""

    def test_custom_config(self, tmp_path):
        """Test using custom configuration."""
        config = AgentConfig(
            approaches_dir=tmp_path / "custom_approaches",
            require_approval=False
        )

        orchestrator = AgentOrchestrator(config)
        assert orchestrator.config.approaches_dir == tmp_path / "custom_approaches"
        assert orchestrator.config.require_approval is False

    def test_default_config(self):
        """Test that default config is used when none provided."""
        orchestrator = AgentOrchestrator()
        assert orchestrator.config is not None
        assert orchestrator.config.approaches_dir.name == "approaches"
