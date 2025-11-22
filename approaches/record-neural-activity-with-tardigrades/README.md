# record-neural-activity-with-tardigrades

## Hypothesis

You can use tardigrades to record neural activity from the brain

## Status

Under investigation - hypergraph being developed.

## Files

- `hypergraph.json` - Entailment hypergraph with claims, implications, and evidence
- `simulations/` - Python simulations testing key assumptions

## Visualization

To view the hypergraph interactively:

```bash
cd ../..
python -m http.server 8765
# Open: http://localhost:8765/entailment_hypergraph/?graph=approaches/record-neural-activity-with-tardigrades/hypergraph.json
```

## Created

2025-11-21
