# Day19 — assess specialized coordination before adopting it

Date:2026-11-05. Status:assessment completed; retain simpler production graph.
The roadmap explicitly permits this outcome without demonstrated benefit.
`evals/agent_coordination_assessment.py` implements a bounded typed three-role
candidate and one-node equivalent over the same real authorized tool policy.
No additional production agent API is exposed. ADR002 contains dataset,
measurements and the important live-model verification limits.

50/50policy cases passed for each shape; p50 3.406ms(single),3.742ms(three-role).
p95 9.310ms/7.213ms are single-run noise, not significant improvements. No model
calls, tokens or provider cost; no factual-reasoning benchmark is claimed.
Partial tool failure returns unavailable after one call; no recursive retry.
Targeted2passed in1.00s; full regression is recorded in implementation status.

## FDE interview questions

1. **Why not deploy more agents?** Complexity needs demonstrated benefit;
the same workload showed no correctness gain.
2. **How make a fair comparison?** Hold data, policy, identity and tools fixed;
change the coordination shape and explicitly limit conclusions.
3. **What are the handoffs?** Typed ticket ID/status/record lists, fixed edges
and recursion limit6, rather than free-form delegation or recursive prompts.
4. **Can a role bypass approvals?** No. All use the same read registry and
none have the execution capability for writes.
5. **What does50/50mean?** Deterministic authorization/policy cases only,
not live model quality or general enterprise task accuracy.
6. **When revisit?** A representative support workflow showing measurable
quality gains that outweigh latency, tokens, cost and failure surface.
