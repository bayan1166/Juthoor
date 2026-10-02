# 08 - Knowledge-graph integrity

**Status: DONE (branching deliberately not added)**

## Objective
The prerequisite graph must be valid (no cycles/orphans, consistent closure, reachable) and any branching must be pedagogically sound.

## Current problem (before this work)
Graph validated at import only for basic shape; no tests for closure/reachability.

## Required implementation
- Tests for cycles, orphans, transitive closure, reachability, ordering; engine rejects bad graphs.
- Branching: **not added**. Adding unreviewed curriculum links would be an unsupported pedagogical claim.

## Files affected
- tests/test_knowledge_graph_integrity.py
- app/engine/knowledge_graph.py

## Tests required
- tests/test_knowledge_graph_integrity.py

## Acceptance criteria
- Graph valid; closure and reachability hold

## Actual result
Done for integrity. The shipped graph is still a chain (9 skills); branching and competing roots are supported and tested on synthetic graphs only. The integers -> fractions edge remains an unreviewed teacher assumption.

## Status
DONE (branching deliberately not added)

## Evidence
- tests/test_knowledge_graph_integrity.py passes (10 tests)
