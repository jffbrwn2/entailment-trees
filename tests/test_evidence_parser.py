"""
Tests for evidence_parser module.
"""

import pytest
from pathlib import Path
from agent_system.evidence_parser import (
    parse_simulation_evidence,
    format_literature_evidence,
    format_calculation_evidence,
    read_lines_from_file,
    extract_key_results,
    suggest_score_from_simulation,
    format_simulation_summary
)


class TestSimulationEvidence:
    """Test simulation evidence formatting."""

    def test_parse_simulation_evidence(self, sample_simulation_file):
        """Test parsing simulation evidence."""
        evidence = parse_simulation_evidence(
            sim_path=sample_simulation_file,
            lines="4-6",
            description="Key calculation"
        )

        assert evidence["type"] == "simulation"
        assert "test_sim.py" in evidence["source"]
        assert evidence["lines"] == "4-6"
        assert "signal_strength" in evidence["code"]
        assert evidence["description"] == "Key calculation"

    def test_parse_simulation_evidence_without_description(self, sample_simulation_file):
        """Test that description is optional."""
        evidence = parse_simulation_evidence(
            sim_path=sample_simulation_file,
            lines="1-3"
        )

        assert "description" not in evidence
        assert evidence["type"] == "simulation"


class TestLiteratureEvidence:
    """Test literature evidence formatting."""

    def test_format_literature_evidence(self):
        """Test formatting literature evidence."""
        evidence = format_literature_evidence(
            source="Smith et al. (2023)",
            reference_text="Neural signals produce 10^-12 Pa pressure"
        )

        assert evidence["type"] == "literature"
        assert evidence["source"] == "Smith et al. (2023)"
        assert evidence["reference_text"] == "Neural signals produce 10^-12 Pa pressure"

    def test_format_literature_evidence_with_lines(self):
        """Test literature evidence with line numbers."""
        evidence = format_literature_evidence(
            source="paper.pdf",
            reference_text="Important quote",
            lines="45-50"
        )

        assert evidence["lines"] == "45-50"


class TestCalculationEvidence:
    """Test calculation evidence formatting."""

    def test_format_calculation_evidence(self):
        """Test formatting calculation evidence."""
        evidence = format_calculation_evidence(
            equations="E = mc^2, F = ma",
            program="def calc(): return 42",
            description="Physics calculation"
        )

        assert evidence["type"] == "calculation"
        assert evidence["equations"] == "E = mc^2, F = ma"
        assert evidence["program"] == "def calc(): return 42"
        assert evidence["description"] == "Physics calculation"

    def test_format_calculation_evidence_without_description(self):
        """Test that description is optional."""
        evidence = format_calculation_evidence(
            equations="x = y + z",
            program="lambda x, y: x + y"
        )

        assert "description" not in evidence


class TestReadLinesFromFile:
    """Test reading specific lines from files."""

    def test_read_single_range(self, sample_simulation_file):
        """Test reading a single range of lines."""
        content = read_lines_from_file(sample_simulation_file, "4-6")

        assert "signal_strength" in content
        assert "noise_floor" in content
        assert len(content.split('\n')) == 3

    def test_read_multiple_ranges(self, sample_simulation_file):
        """Test reading multiple ranges."""
        content = read_lines_from_file(sample_simulation_file, "1-2, 8-9")

        assert "# Test simulation" in content
        assert "# Result" in content

    def test_read_single_line(self, sample_simulation_file):
        """Test reading a single line."""
        content = read_lines_from_file(sample_simulation_file, "5")

        assert "signal_strength" in content
        assert "noise_floor" not in content

    def test_read_from_nonexistent_file_fails(self, tmp_path):
        """Test that reading non-existent file raises error."""
        with pytest.raises(FileNotFoundError):
            read_lines_from_file(tmp_path / "nonexistent.py", "1-10")


class TestExtractKeyResults:
    """Test extracting results from simulation output."""

    def test_extract_with_equals_pattern(self):
        """Test extracting key = value patterns."""
        output = """
        Running simulation...
        signal = 1.5e-12
        noise = 3.2e-6
        snr = 4.6875e-07
        Done.
        """

        results = extract_key_results(output)

        assert "signal" in results
        assert "noise" in results
        assert "snr" in results
        assert results["signal"] == pytest.approx(1.5e-12)
        assert results["noise"] == pytest.approx(3.2e-6)

    def test_extract_with_colon_pattern(self):
        """Test extracting key: value patterns."""
        output = """
        Results:
        SNR: 0.5
        Feasibility: 2.5
        Score: 7.8
        """

        results = extract_key_results(output)

        assert results["snr"] == pytest.approx(0.5)
        assert results["feasibility"] == pytest.approx(2.5)
        assert results["score"] == pytest.approx(7.8)

    def test_extract_with_no_results(self):
        """Test extraction from output with no numerical results."""
        output = "Just some text without numbers"

        results = extract_key_results(output)

        assert len(results) == 0


class TestSuggestScore:
    """Test score suggestion from simulation output."""

    def test_suggest_score_from_feasibility(self):
        """Test score suggestion when feasibility is present."""
        output = "feasibility = 7.5"

        score = suggest_score_from_simulation(output)

        assert score == 7.5

    def test_suggest_score_from_explicit_score(self):
        """Test score suggestion when score is explicitly present."""
        output = "score = 8.2"

        score = suggest_score_from_simulation(output)

        assert score == 8.2

    def test_suggest_score_from_snr(self):
        """Test score suggestion from SNR."""
        # SNR = 10 dB should map to reasonable score
        output = "snr_db = 10.0"

        score = suggest_score_from_simulation(output, target_key="snr_db")

        assert score is not None
        assert 0 <= score <= 10

    def test_suggest_score_with_target_key(self):
        """Test using specific target key."""
        output = "x = 5.0\ny = 8.0"

        score = suggest_score_from_simulation(output, target_key="y")

        assert score == 8.0

    def test_suggest_score_no_results(self):
        """Test that no results returns None."""
        output = "No numerical data here"

        score = suggest_score_from_simulation(output)

        assert score is None


class TestFormatSimulationSummary:
    """Test simulation summary formatting."""

    def test_format_summary_short_output(self, sample_simulation_file):
        """Test formatting summary with short output."""
        output = "SNR: 0.5\nResult: 50.0"

        summary = format_simulation_summary(
            sim_path=sample_simulation_file,
            output=output
        )

        assert "test_sim.py" in summary
        assert "SNR: 0.5" in summary
        assert "Result: 50.0" in summary

    def test_format_summary_with_key_results(self, sample_simulation_file):
        """Test formatting summary with extracted key results."""
        output = "SNR: 0.5"
        key_results = {"snr": 0.5, "feasibility": 3.0}

        summary = format_simulation_summary(
            sim_path=sample_simulation_file,
            output=output,
            key_results=key_results
        )

        assert "snr: 0.5" in summary
        assert "feasibility: 3.0" in summary

    def test_format_summary_long_output(self, sample_simulation_file):
        """Test that long output is truncated."""
        output = "\n".join([f"Line {i}" for i in range(20)])

        summary = format_simulation_summary(
            sim_path=sample_simulation_file,
            output=output
        )

        # Should show first/last 5 lines
        assert "first 5 lines" in summary
        assert "last 5 lines" in summary
        assert "..." in summary
