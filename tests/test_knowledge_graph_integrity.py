"""Knowledge-graph integrity (pure): the shipped graph and the validator itself."""
import pytest

from app.engine import diagnosis as dx
from app.engine import knowledge_graph as kg
from app.engine import offline_bank as ob


def test_shipped_graph_is_a_valid_dag():
    assert dx.validate_prerequisites({s.id: s.prerequisites for s in kg.SKILLS.values()}) == []


def test_skill_ids_and_names_are_unique_and_consistent():
    ids = list(kg.SKILLS)
    assert len(ids) == len(set(ids))
    assert all(k == s.id for k, s in kg.SKILLS.items())
    names = [s.name for s in kg.SKILLS.values()]
    assert len(names) == len(set(names))


def test_every_prerequisite_exists_and_has_no_duplicates():
    for s in kg.SKILLS.values():
        assert all(p in kg.SKILLS for p in s.prerequisites), s.id
        assert len(set(s.prerequisites)) == len(s.prerequisites), s.id
        assert s.id not in s.prerequisites


def test_no_orphan_skills_every_skill_is_reachable_from_a_root():
    roots = [s for s in kg.SKILLS if not kg.prerequisites(s)]
    assert roots, "graph has no entry skill"
    reachable = set(roots)
    for r in roots:
        reachable |= kg.descendants(r)
    assert reachable == set(kg.SKILLS)


def test_prerequisite_closure_is_transitive():
    for s in kg.SKILLS:
        anc = kg.ancestors(s)
        for a in list(anc):
            assert kg.ancestors(a) <= anc
        assert s not in anc


def test_depth_is_consistent_with_prerequisites_and_order_is_topological():
    for s in kg.SKILLS:
        pres = kg.prerequisites(s)
        assert kg.depth(s) == (0 if not pres else 1 + max(kg.depth(p) for p in pres))
        assert kg.depth(s) == kg.PREREQ_GRAPH.depth(s)
    pos = {s: i for i, s in enumerate(kg.ordered_skills())}
    for s in kg.SKILLS:
        assert all(pos[p] < pos[s] for p in kg.prerequisites(s))


def test_every_skill_has_a_question_bank_and_remediation_text():
    for s in kg.SKILLS.values():
        assert s.id in ob.REGISTRY, f"{s.id} has no question bank"
        assert s.intervention.strip() and len(s.ladder) == 3


@pytest.mark.parametrize("graph, needle", [
    ({"a": ["a"]}, "itself"),
    ({"a": ["b"], "b": []} | {"c": ["zzz"]}, "unknown prerequisite"),
    ({"a": ["b", "b"], "b": []}, "duplicate"),
    ({"a": ["b"], "b": ["c"], "c": ["a"]}, "cycle"),
])
def test_validator_reports_each_kind_of_defect(graph, needle):
    problems = dx.validate_prerequisites(graph)
    assert problems and any(needle in p for p in problems)
    with pytest.raises(dx.GraphError):
        dx.PrereqGraph(graph)


def test_a_valid_branching_graph_is_accepted_and_ancestors_are_correct():
    g = dx.PrereqGraph({"base": [], "left": ["base"], "right": ["base"], "top": ["left", "right"]})
    assert g.ancestors("top") == {"base", "left", "right"}
    assert g.depth("top") == 2


def test_the_real_graph_is_a_linear_chain_documented_limitation():
    """Not a defect check: documents that branching is only exercised on fixtures (see README, Knowledge graph)."""
    assert all(len(kg.prerequisites(s)) <= 1 for s in kg.SKILLS)
