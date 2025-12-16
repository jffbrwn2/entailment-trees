---
layout: default
title: Entailment Trees
---

# Entailment Trees: A Cost Function for Ideas

As AI systems become more intelligent, it ought to be possible to use them to both discover truly interesting new scientific ideas and evaluate them. Additionally, we need systems that can make their reasoning and evaluation clear to us. It's not helpful if an AI system gives you 20 pages of impenetrable reasoning when you're the one who has to sign the check or run the experiment. You need to understand what's going on, how the different parts of the idea play together, what the critical bottlenecks or risky parts are.

So, we explore the idea of an **entailment tree**.

Entailment trees formalize a simple idea: to understand a big idea, break it down into simpler parts. Specifically, in these trees, we break claims into premises that, if true, imply the claim. This kind of relationship is called "entailment."

In an entailment tree, there are **claim nodes** that contain a particular claim that can be rated as true or false with varying degrees of certainty, and logical **AND** and **OR** nodes. Multiple claim nodes can point to a single logical node:

- If multiple claims lead into an **AND** node, they are ANDed together; i.e., the resulting claim is true if and only if every subclaim is true.
- If multiple claims lead into an **OR** node, they are ORed together; i.e., the resulting claim is true if at least one subclaim is true.

A single logical node can then lead to a claim node, defining the implication or entailment relationship.

---

## The Demanding "AND"

ANDing multiple claims together captures the intuition that many things have to work together for an idea to work out. Breaking down the idea into its components is designed to identify claims that are more specific and more usefully concrete. This was one of the original motivations; if you could repeatedly break down an idea into more fundamental parts, these would be easier to evaluate and understand.

---

## The Magical "OR"

When it comes to transformative ideas, often the interesting thing is that someone comes up with a new solution to an outstanding problem. Think, for instance, about the use of GCaMP, a protein that is used to monitor the activity of neurons with light. Prior to the discovery of Green Fluorescent Protein in jellyfish, I imagine it was really hard to think of a way of studying neurons without using electrical recordings. However, eventually there came a new strategy, a "we could do this OR this new thing," and that opened up an entirely new way of interacting with the problem.

The ability to introduce OR nodes in the graph represents this possibility.

---

## The "Epistemic" Cost Function

Something that we've been after is a "cost function" for ideas. The cost function should:

1. Have **0 cost** if the idea will work (i.e., you can record neural activity with an electrode)
2. Have a **very high cost** if the idea working requires violating facts that are known in the world (e.g., you can travel backwards through time)
3. **Scale with the uncertainty** of the idea

The nice thing about entailment trees is that you can use them to define a cost function that satisfies all these criteria.

To do so, you assign each leaf a "probability" *P* from 0 (False) to 1 (True), with 0.5 being maximally unsure. Then, you define the cost of each leaf node to be −log₂(*P*). Finally, you propagate scores from the premise nodes to non-leaf conclusion nodes using the logical nodes as follows:

- **AND**: Cost(C) = Σ −log *Pᵢ*
- **OR**: Cost(C) = min −log *Pᵢ*

The cost function has the properties we outlined. True claims don't add anything to the cost (−log 1 = 0), while expressly false claims add a lot (infinite if the claim probability is 0).
