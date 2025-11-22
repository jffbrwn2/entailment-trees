# acousto-optic-neuro

## Hypothesis

Ultrasound can be used to increase the spatial resolution of fNIRS through the acoustooptic effect

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
# Open: http://localhost:8765/entailment_hypergraph/?graph=approaches/acousto-optic-neuro/hypergraph.json
```

## Created

2025-11-22
