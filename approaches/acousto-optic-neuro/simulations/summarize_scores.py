"""
Summarize the current state of claims in the hypergraph.
"""

import json

with open('hypergraph.json', 'r') as f:
    data = json.load(f)

claims = data['claims']

print("Claim Scores Summary")
print("=" * 80)
print(f"{'ID':<15} {'Score':<8} {'Evidence':<10} {'Description':<45}")
print("-" * 80)

for c in claims:
    if c['id'] == 'hypothesis':
        continue
    score = c.get('score', 5.0)
    n_evidence = len(c.get('evidence', []))
    text = c['text'][:45] + '...' if len(c['text']) > 45 else c['text']
    print(f"{c['id']:<15} {score:<8.1f} {n_evidence:<10} {text}")

print()
print("=" * 80)

# Find hypothesis
hypothesis = [c for c in claims if c['id'] == 'hypothesis'][0]
print(f"Hypothesis score: {hypothesis.get('score', 5.0)}")
print(f"Hypothesis: {hypothesis['text']}")

print()
print("=" * 80)
print("Score Distribution:")
print("-" * 80)

scores = [c.get('score', 5.0) for c in claims if c['id'] != 'hypothesis']
print(f"  Average: {sum(scores)/len(scores):.1f}")
print(f"  Min: {min(scores):.1f}")
print(f"  Max: {max(scores):.1f}")
print(f"  Claims with score >= 7: {len([s for s in scores if s >= 7])}/{len(scores)}")
print(f"  Claims with score < 5: {len([s for s in scores if s < 5])}/{len(scores)}")
