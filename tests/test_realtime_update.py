#!/usr/bin/env python
"""
Test script for real-time WebSocket updates.

This script modifies a hypergraph and you should see the changes
appear instantly in any connected browser.

Usage:
    1. Start the server: ./start_visualization.sh
    2. Open browser to: http://localhost:8765/?graph=entailment_hypergraph/water_boiling_example.json
    3. Run this script: python test_realtime_update.py
    4. Watch the browser update in real-time!
"""

import json
import time
from pathlib import Path

# Path to test hypergraph
test_file = Path("entailment_hypergraph/water_boiling_example.json")

print("=" * 70)
print("Real-Time WebSocket Update Test")
print("=" * 70)
print(f"Will modify: {test_file}")
print("Make sure:")
print("  1. Server is running (./start_visualization.sh)")
print("  2. Browser is open to http://localhost:8765/?graph=entailment_hypergraph/water_boiling_example.json")
print()
print("Press Enter to start test...")
input()

# Load current hypergraph
with open(test_file, 'r') as f:
    hypergraph = json.load(f)

print(f"\nCurrent claims: {len(hypergraph['claims'])}")
print("\nAdding a new claim in 3 seconds...")
time.sleep(3)

# Add a test claim
new_claim = {
    "id": f"test_claim_{int(time.time())}",
    "text": f"Real-time test claim added at {time.strftime('%H:%M:%S')}",
    "score": 9.5,
    "reasoning": "This claim was added by the test script to demonstrate WebSocket updates",
    "tags": ["TEST", "REALTIME"]
}

hypergraph['claims'].append(new_claim)

# Save changes
with open(test_file, 'w') as f:
    json.dump(hypergraph, f, indent=2)

print(f"✓ Added claim: {new_claim['id']}")
print("Check your browser - the new claim should appear instantly!")
print()

# Wait a bit then modify the claim
print("Waiting 3 seconds before modifying the claim...")
time.sleep(3)

# Find and update the claim
for claim in hypergraph['claims']:
    if claim['id'] == new_claim['id']:
        claim['score'] = 2.5
        claim['text'] = f"UPDATED: {claim['text']}"
        print(f"✓ Updated claim score to {claim['score']}")
        break

with open(test_file, 'w') as f:
    json.dump(hypergraph, f, indent=2)

print("Check your browser - the claim should be updated!")
print()

# Wait then remove the test claim
print("Waiting 3 seconds before removing the test claim...")
time.sleep(3)

hypergraph['claims'] = [c for c in hypergraph['claims'] if c['id'] != new_claim['id']]

with open(test_file, 'w') as f:
    json.dump(hypergraph, f, indent=2)

print(f"✓ Removed test claim")
print("Check your browser - the claim should be gone!")
print()
print("=" * 70)
print("Test complete! WebSocket updates working? 🎉")
print("=" * 70)
