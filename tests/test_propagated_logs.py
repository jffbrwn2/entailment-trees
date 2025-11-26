#!/usr/bin/env python
"""
Test script for propagated negative log calculation.

Tests the propagation logic on the water boiling example.
"""

import json
import math
from pathlib import Path

# Load water boiling example
example_file = Path("entailment_hypergraph/water_boiling_example.json")
with open(example_file, 'r') as f:
    hypergraph = json.load(f)

print("=" * 70)
print("Testing Propagated Negative Log Calculation")
print("=" * 70)
print()

# Manual calculation for verification
print("Manual Calculation:")
print("-" * 70)

claims = {c['id']: c for c in hypergraph['claims']}
implications = hypergraph['implications']

# Leaf nodes (c1, c2, c3)
for claim_id in ['c1', 'c2', 'c3']:
    score = claims[claim_id]['score']
    neg_log = -math.log2(score / 10.0)
    print(f"{claim_id}: score={score} -> propagated_negative_log = -log2({score}/10) = {neg_log:.6f}")

print()

# Non-leaf node (c4)
# c4 is conclusion of AND(c1, c2, c3)
c1_log = -math.log2(claims['c1']['score'] / 10.0)
c2_log = -math.log2(claims['c2']['score'] / 10.0)
c3_log = -math.log2(claims['c3']['score'] / 10.0)
c4_log = c1_log + c2_log + c3_log

print(f"c4 (conclusion of AND[c1, c2, c3]):")
print(f"  = c1_log + c2_log + c3_log")
print(f"  = {c1_log:.6f} + {c2_log:.6f} + {c3_log:.6f}")
print(f"  = {c4_log:.6f}")
print()

# Now test with HypergraphManager
print("=" * 70)
print("Testing with HypergraphManager:")
print("-" * 70)

# Create a temporary copy to test with
from agent_system.hypergraph_manager import HypergraphManager

# Create temp directory for testing
test_dir = Path("test_temp_approach")
test_dir.mkdir(exist_ok=True)

# Copy water boiling example to test directory
import shutil
test_hypergraph_path = test_dir / "hypergraph.json"
shutil.copy(example_file, test_hypergraph_path)

# Create manager and calculate
manager = HypergraphManager(test_dir)
propagated_logs = manager.calculate_propagated_negative_logs()

print("Calculated propagated_negative_logs:")
for claim_id, neg_log in propagated_logs.items():
    score = claims[claim_id]['score']
    print(f"  {claim_id}: {neg_log:.6f} (score={score})")

print()

# Update the hypergraph with propagated logs
manager.update_propagated_negative_logs()
print("✓ Updated hypergraph with propagated_negative_log values")
print(f"✓ Saved to {test_hypergraph_path}")
print()

# Load and display updated hypergraph
with open(test_hypergraph_path, 'r') as f:
    updated = json.load(f)

print("Updated claims:")
print("-" * 70)
for claim in updated['claims']:
    print(f"{claim['id']}: score={claim['score']}, propagated_negative_log={claim.get('propagated_negative_log', 'N/A')}")

print()
print("=" * 70)
print("Test Complete!")
print("=" * 70)

# Cleanup
shutil.rmtree(test_dir)
print(f"✓ Cleaned up {test_dir}")
