"""Mathlib4 retrieval-augmented context for the formalizer.

Maintains a curated index of Mathlib4 declarations organised by mathematical
area.  At formalization time the index is queried by keyword to return the
most relevant lemma signatures, which are then injected into the Claude prompt
so it knows which tools are actually available.
"""

from __future__ import annotations

import re
from typing import Any

# ---------------------------------------------------------------------------
# Curated Mathlib4 declaration index
# Entries: {"name": str, "sig": str, "tags": list[str]}
# ---------------------------------------------------------------------------

_INDEX: list[dict[str, Any]] = [
    # ── Number Theory ─────────────────────────────────────────────────────
    {
        "name": "Nat.Prime",
        "sig": "Nat.Prime (p : ℕ) : Prop",
        "tags": ["prime", "number theory", "nat"],
    },
    {
        "name": "Nat.Infinite.exists_infinite_primes",
        "sig": "∀ n : ℕ, ∃ p, n ≤ p ∧ Nat.Prime p",
        "tags": ["prime", "infinite", "number theory"],
    },
    {
        "name": "Nat.Prime.two_le",
        "sig": "Nat.Prime p → 2 ≤ p",
        "tags": ["prime", "number theory"],
    },
    {
        "name": "Nat.Coprime",
        "sig": "Nat.Coprime (m n : ℕ) : Prop",
        "tags": ["coprime", "gcd", "number theory"],
    },
    {
        "name": "Nat.gcd_comm",
        "sig": "Nat.gcd m n = Nat.gcd n m",
        "tags": ["gcd", "number theory"],
    },
    {
        "name": "Int.emod_emod_of_dvd",
        "sig": "∀ (b : ℤ), c ∣ b → a % b % c = a % c",
        "tags": ["mod", "divisibility", "number theory"],
    },
    {
        "name": "Nat.dvd_antisymm",
        "sig": "m ∣ n → n ∣ m → m = n",
        "tags": ["divisibility", "number theory"],
    },
    {
        "name": "Nat.factors_prime_pow",
        "sig": "Nat.factors (p ^ n) = List.replicate n p",
        "tags": ["prime", "factors", "number theory"],
    },
    {
        "name": "ZMod.val_cast_of_lt",
        "sig": "n < p → (ZMod.val (n : ZMod p)) = n",
        "tags": ["zmod", "modular arithmetic", "number theory"],
    },
    {
        "name": "Finset.sum_range_id",
        "sig": "∑ i in Finset.range n, i = n * (n - 1) / 2",
        "tags": ["sum", "combinatorics", "number theory"],
    },
    # ── Algebra ───────────────────────────────────────────────────────────
    {
        "name": "Group.orderOf_dvd_card",
        "sig": "orderOf a ∣ Fintype.card G",
        "tags": ["group", "order", "algebra"],
    },
    {
        "name": "Fingroup.lagrange",
        "sig": "H.card ∣ G.card",
        "tags": ["group", "subgroup", "lagrange", "algebra"],
    },
    {"name": "Ring.sub_self", "sig": "a - a = 0", "tags": ["ring", "algebra"]},
    {
        "name": "Algebra.id.smul_eq_mul",
        "sig": "Algebra.id.smul r a = r * a",
        "tags": ["algebra", "smul"],
    },
    {
        "name": "Polynomial.degree_add_le",
        "sig": "degree (p + q) ≤ max (degree p) (degree q)",
        "tags": ["polynomial", "algebra"],
    },
    {
        "name": "Polynomial.roots_X_sub_C",
        "sig": "(X - C a).roots = {a}",
        "tags": ["polynomial", "roots", "algebra"],
    },
    {
        "name": "LinearMap.ker_eq_bot",
        "sig": "LinearMap.ker f = ⊥ ↔ Function.Injective f",
        "tags": ["linear map", "kernel", "algebra"],
    },
    {
        "name": "Matrix.det_mul",
        "sig": "Matrix.det (A * B) = Matrix.det A * Matrix.det B",
        "tags": ["matrix", "determinant", "algebra"],
    },
    # ── Combinatorics / Graph Theory ──────────────────────────────────────
    {
        "name": "Finset.card_union_add_card_inter",
        "sig": "(s ∪ t).card + (s ∩ t).card = s.card + t.card",
        "tags": ["finset", "combinatorics", "inclusion-exclusion"],
    },
    {
        "name": "Finset.card_powerset",
        "sig": "s.powerset.card = 2 ^ s.card",
        "tags": ["combinatorics", "powerset"],
    },
    {
        "name": "Nat.choose_symm",
        "sig": "Nat.choose n k = Nat.choose n (n - k)",
        "tags": ["choose", "binomial", "combinatorics"],
    },
    {
        "name": "SimpleGraph.Subgraph.degree_le",
        "sig": "G'.degree v ≤ G.degree v",
        "tags": ["graph theory", "degree"],
    },
    {
        "name": "SimpleGraph.isClique_iff",
        "sig": "G.IsClique s ↔ ∀ v ∈ s, ∀ w ∈ s, v ≠ w → G.Adj v w",
        "tags": ["graph theory", "clique"],
    },
    {
        "name": "SimpleGraph.Coloring",
        "sig": "SimpleGraph.Coloring G α := {f : V → α // ∀ ⦃v w⦄, G.Adj v w → f v ≠ f w}",
        "tags": ["graph theory", "coloring", "chromatic"],
    },
    {
        "name": "Finpartition.card_parts_le_card",
        "sig": "P.parts.card ≤ s.card",
        "tags": ["combinatorics", "partition"],
    },
    # ── Topology / Analysis ───────────────────────────────────────────────
    {
        "name": "Metric.dist_triangle",
        "sig": "dist x z ≤ dist x y + dist y z",
        "tags": ["metric", "topology", "distance"],
    },
    {
        "name": "Real.tendsto_atTop_atTop",
        "sig": "Filter.Tendsto f Filter.atTop Filter.atTop ↔ ∀ b, ∃ N, ∀ n ≥ N, b ≤ f n",
        "tags": ["analysis", "limit", "topology"],
    },
    {
        "name": "ContinuousOn.continuousAt",
        "sig": "ContinuousOn f s → x ∈ interior s → ContinuousAt f x",
        "tags": ["topology", "continuity"],
    },
    {
        "name": "IsCompact.elim_finite_subcover",
        "sig": "IsCompact s → ∀ (ι : Type*) (U : ι → Set α), (∀ i, IsOpen (U i)) → s ⊆ ⋃ i, U i → ∃ t : Finset ι, s ⊆ ⋃ i ∈ t, U i",
        "tags": ["topology", "compactness"],
    },
    {
        "name": "MeasureTheory.integral_add",
        "sig": "Integrable f → Integrable g → ∫ x, f x + g x ∂μ = ∫ x, f x ∂μ + ∫ x, g x ∂μ",
        "tags": ["measure theory", "integral", "analysis"],
    },
    # ── Logic / Set Theory ────────────────────────────────────────────────
    {
        "name": "Set.Finite.exists_maximal_wrt",
        "sig": "s.Finite → s.Nonempty → ∃ m ∈ s, ∀ a ∈ s, r m a → r a m → a = m",
        "tags": ["set", "finite", "maximal"],
    },
    {
        "name": "Function.Injective.comp",
        "sig": "Function.Injective g → Function.Injective f → Function.Injective (g ∘ f)",
        "tags": ["function", "injective", "logic"],
    },
    {
        "name": "Equiv.bijective",
        "sig": "Function.Bijective e.toFun",
        "tags": ["equivalence", "bijective", "logic"],
    },
]


def _tokenize(text: str) -> set[str]:
    return set(re.findall(r"[a-zA-Z]+", text.lower()))


def retrieve(
    conjecture: str, subfield: str = "", top_k: int = 12
) -> list[dict[str, Any]]:
    """Return the top-k most relevant Mathlib4 declarations for *conjecture*.

    Relevance is measured by Jaccard similarity on word tokens between the
    query (conjecture + subfield) and each entry's tags + signature.
    """
    query_tokens = _tokenize(conjecture + " " + subfield)
    if not query_tokens:
        return _INDEX[:top_k]

    scored: list[tuple[float, dict[str, Any]]] = []
    for entry in _INDEX:
        entry_tokens = _tokenize(
            " ".join(entry["tags"]) + " " + entry["sig"] + " " + entry["name"]
        )
        union = query_tokens | entry_tokens
        inter = query_tokens & entry_tokens
        score = len(inter) / len(union) if union else 0.0
        scored.append((score, entry))

    scored.sort(key=lambda x: x[0], reverse=True)
    return [e for _, e in scored[:top_k] if scored[0][0] > 0.0]


def format_for_prompt(entries: list[dict[str, Any]]) -> str:
    """Render retrieved declarations as a compact prompt block."""
    if not entries:
        return ""
    lines = ["Relevant Mathlib4 declarations (use these — do not invent names):"]
    for e in entries:
        lines.append(f"  {e['name']} : {e['sig']}")
    return "\n".join(lines)
