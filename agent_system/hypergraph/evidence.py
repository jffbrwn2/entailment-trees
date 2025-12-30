"""
Evidence Parser - Helpers for formatting evidence in hypergraph-compatible format.

These functions help convert simulation outputs and literature findings into
the structured evidence format required by the hypergraph schema.
"""

from pathlib import Path
from typing import Dict, Any, List, Optional
import re


def parse_simulation_evidence(
    sim_path: Path,
    lines: str,
    description: str = ""
) -> Dict[str, Any]:
    """
    Create simulation evidence object.

    Args:
        sim_path: Path to simulation file
        lines: Line specification (e.g., "10-50" or "10-15, 20-25")
        description: Optional description of what this evidence shows

    Returns:
        Evidence dict in hypergraph format (code is loaded on-demand)
    """
    # Try to make path relative to cwd, otherwise use absolute
    try:
        source_path = str(sim_path.relative_to(Path.cwd()))
    except ValueError:
        source_path = str(sim_path)

    # Code is loaded on-demand from source:lines during evaluation
    evidence = {
        "type": "simulation",
        "source": source_path,
        "lines": lines,
    }

    if description:
        evidence["description"] = description

    return evidence


def format_literature_evidence(
    source: str,
    reference_text: str,
    lines: Optional[str] = None
) -> Dict[str, Any]:
    """
    Create literature evidence object.

    Args:
        source: Citation or file path
        reference_text: Exact quote from source
        lines: Optional line numbers if source is a file

    Returns:
        Evidence dict in hypergraph format
    """
    evidence = {
        "type": "literature",
        "source": source,
        "reference_text": reference_text
    }

    if lines:
        evidence["lines"] = lines

    return evidence


def format_calculation_evidence(
    equations: str,
    program: str,
    description: str = ""
) -> Dict[str, Any]:
    """
    Create calculation evidence object.

    Args:
        equations: Mathematical equations (LaTeX or text)
        program: Python code performing calculation
        description: Optional description

    Returns:
        Evidence dict in hypergraph format
    """
    evidence = {
        "type": "calculation",
        "equations": equations,
        "program": program
    }

    if description:
        evidence["description"] = description

    return evidence


def read_lines_from_file(file_path: Path, lines_spec: str) -> str:
    """
    Read specific lines from a file.

    Args:
        file_path: Path to file
        lines_spec: Line specification like "10-50" or "10-15, 20-25"

    Returns:
        Extracted text from specified lines

    Raises:
        FileNotFoundError: If file doesn't exist
        ValueError: If line spec is invalid
    """
    if not file_path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")

    with open(file_path, 'r') as f:
        all_lines = f.readlines()

    result_lines = []

    # Handle multiple ranges separated by commas
    for range_spec in lines_spec.split(','):
        range_spec = range_spec.strip()

        if '-' in range_spec:
            # Range like "10-50"
            start, end = map(int, range_spec.split('-'))
            # Convert to 0-indexed
            selected_lines = all_lines[start-1:end]
            result_lines.extend(selected_lines)
        else:
            # Single line
            line_num = int(range_spec)
            result_lines.append(all_lines[line_num-1])

    return ''.join(result_lines).rstrip()


def extract_key_results(simulation_output: str) -> Dict[str, Any]:
    """
    Parse simulation output to extract key numerical results.

    This is a simple heuristic parser that looks for common patterns:
    - "Result: X"
    - "SNR = Y"
    - "Score: Z"

    Args:
        simulation_output: stdout/stderr from simulation

    Returns:
        Dict of extracted values
    """
    results = {}

    # Pattern: "key = value" or "key: value"
    patterns = [
        r'(\w+)\s*=\s*([-+]?\d*\.?\d+(?:[eE][-+]?\d+)?)',
        r'(\w+)\s*:\s*([-+]?\d*\.?\d+(?:[eE][-+]?\d+)?)',
    ]

    for pattern in patterns:
        matches = re.finditer(pattern, simulation_output, re.IGNORECASE)
        for match in matches:
            key, value = match.groups()
            try:
                results[key.lower()] = float(value)
            except ValueError:
                pass

    return results


def suggest_score_from_simulation(
    simulation_output: str,
    target_key: Optional[str] = None
) -> Optional[float]:
    """
    Suggest a score (0-10) based on simulation results.

    This is a helper for the agent to propose scores. The user should review.

    Args:
        simulation_output: Output from simulation
        target_key: Optional specific key to look for (e.g., 'snr', 'feasibility')

    Returns:
        Suggested score or None if can't determine
    """
    results = extract_key_results(simulation_output)

    if not results:
        return None

    # If target key specified, use that
    if target_key and target_key.lower() in results:
        value = results[target_key.lower()]
        # Map to 0-10 scale (this is a simple heuristic)
        if 'snr' in target_key.lower():
            # SNR in dB: <0 is bad, >20 is good
            return max(0, min(10, (value + 10) / 3))
        else:
            return max(0, min(10, value))

    # Look for common indicators
    if 'feasibility' in results:
        return results['feasibility']
    if 'score' in results:
        return results['score']

    # Check for SNR
    snr_keys = ['snr', 'signal_to_noise', 'snr_db']
    for key in snr_keys:
        if key in results:
            value = results[key]
            return max(0, min(10, (value + 10) / 3))

    return None


def format_simulation_summary(
    sim_path: Path,
    output: str,
    key_results: Optional[Dict[str, Any]] = None
) -> str:
    """
    Format a human-readable summary of simulation results.

    Args:
        sim_path: Path to simulation
        output: Simulation output
        key_results: Optional extracted key results

    Returns:
        Formatted summary string
    """
    if key_results is None:
        key_results = extract_key_results(output)

    lines = [
        f"Simulation: {sim_path.name}",
        f"",
    ]

    if key_results:
        lines.append("Key Results:")
        for key, value in key_results.items():
            lines.append(f"  {key}: {value}")
        lines.append("")

    # Include first/last few lines of output
    output_lines = output.strip().split('\n')
    if len(output_lines) <= 10:
        lines.append("Output:")
        lines.extend(f"  {line}" for line in output_lines)
    else:
        lines.append("Output (first 5 lines):")
        lines.extend(f"  {line}" for line in output_lines[:5])
        lines.append("  ...")
        lines.append("Output (last 5 lines):")
        lines.extend(f"  {line}" for line in output_lines[-5:])

    return '\n'.join(lines)
