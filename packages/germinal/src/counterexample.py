"""Counterexample finder module.

When automated proof search fails, independent methods run as an ensemble to
search for a concrete counterexample:

1. LLM-based (CounterexampleFinder): asks Claude to reason about the conjecture.
2. Symbolic/brute-force (SymbolicCounterexampleFinder): uses sympy to enumerate a
   bounded integer domain. Independent of the LLM; can neither share its blind
   spots nor confirm its biases.
3. Wolfram Alpha (WolframCounterexampleFinder): queries a third-party CAS/knowledge
   engine when configured. Independent of both Claude and local sympy.

"No counterexample found" from *one* source is absence-of-disproof, not evidence
of truth. Three independent failures-to-disprove are stronger, but still not a
proof. Use search_ensemble() or the backwards-compatible search_dual() wrapper
to run all configured methods and get a combined, structured result.
"""

from __future__ import annotations

import concurrent.futures
import hashlib
import json
import logging
import math
import re
import time
from pathlib import Path
from typing import Any

import anthropic
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from src.settings import Settings

try:
    import wolframalpha
except (
    ImportError
):  # pragma: no cover - exercised by deployments without the optional wheel
    wolframalpha = None  # type: ignore[assignment]

logger = logging.getLogger(__name__)

BACKEND_TIMEOUT_SECONDS = 15.0
SOURCE_BY_METHOD = {
    "llm": "claude",
    "symbolic": "sympy",
    "wolfram": "wolfram_alpha",
}
METHOD_RESULT_KEYS = {
    "claude": "llm_result",
    "sympy": "symbolic_result",
    "wolfram_alpha": "wolfram_result",
}
VALID_SOURCES = {"claude", "sympy", "wolfram_alpha"}
CONSENSUS_COUNTEREXAMPLE_FOUND = "counterexample_found"
CONSENSUS_UNREFUTED = "unrefuted"
CONSENSUS_PARTIAL_FAILURE = "partial_failure"

_SYSTEM_PROMPT = """\
You are a mathematical expert. Given a conjecture, attempt to find a concrete
counterexample that disproves it.

Instructions:
- Think carefully about whether the conjecture is likely true or false.
- If you can find a counterexample, provide it explicitly and verify it satisfies
  all conditions while violating the conclusion.
- If the conjecture appears true and you cannot find a counterexample, say so clearly.
- Be rigorous: do not guess. Only claim a counterexample if you can verify it concretely.

Respond in JSON with this schema:
{
  "found": true | false,
  "counterexample": "concrete counterexample description or null",
  "reasoning": "your reasoning process"
}
"""


def _stable_hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _method_timeout_result(source: str) -> dict[str, Any]:
    method = {
        "claude": "llm",
        "sympy": "symbolic",
        "wolfram_alpha": "wolfram",
    }[source]
    return {
        "method": method,
        "source": source,
        "applicable": True,
        "found": False,
        "counterexample": None,
        "reasoning": f"{source} counterexample search timed out after 15s",
        "timed_out": True,
        "error": "timeout",
    }


def _normalize_method_result(
    result: dict[str, Any],
    source: str,
    conjecture: str,
) -> dict[str, Any]:
    normalized = dict(result)
    normalized.setdefault(
        "method", {"claude": "llm", "sympy": "symbolic"}.get(source, "wolfram")
    )
    normalized["source"] = source
    normalized.setdefault("applicable", True)
    normalized.setdefault("found", False)
    normalized.setdefault("counterexample", None)
    normalized.setdefault("reasoning", "")

    if normalized.get("found") and normalized.get("counterexample"):
        verified = LocalCounterexampleVerifier.verify(
            conjecture, str(normalized["counterexample"])
        )
        if verified["verified"]:
            normalized["verified_locally"] = True
        else:
            original_reasoning = str(normalized.get("reasoning", ""))
            normalized["found"] = False
            normalized["counterexample"] = None
            normalized["verified_locally"] = False
            normalized["rejected_counterexample"] = verified["candidate"]
            normalized["reasoning"] = (
                f"{original_reasoning} Candidate rejected by local verification: "
                f"{verified['reason']}"
            ).strip()

    return normalized


class LocalCounterexampleVerifier:
    """Conservative local verifier for discovered one-variable integer candidates."""

    _ASSIGNMENT = re.compile(r"\b(?P<var>[a-z])\s*=\s*(?P<value>-?\d+)\b")

    @classmethod
    def verify(cls, conjecture: str, candidate: str) -> dict[str, Any]:
        assignment = cls._extract_assignment(candidate)
        if assignment is None:
            return {
                "verified": False,
                "candidate": candidate,
                "reason": "could not extract an integer assignment from candidate",
            }

        var_name, value = assignment
        parser = _SymbolicClaimParser()
        parsed = parser.parse(conjecture.strip())
        if not parsed["applicable"]:
            return {
                "verified": False,
                "candidate": candidate,
                "reason": parsed["reasoning"],
            }
        if parsed["var_name"] != var_name:
            return {
                "verified": False,
                "candidate": candidate,
                "reason": (
                    f"candidate assigns '{var_name}', but conjecture quantifies "
                    f"'{parsed['var_name']}'"
                ),
            }
        if value not in parsed["domain"]:
            return {
                "verified": False,
                "candidate": candidate,
                "reason": f"candidate value {value} is outside the parsed domain",
            }

        v = SymbolicCounterexampleFinder._eval_int(parsed["expr"], parsed["var"], value)
        if v is None:
            return {
                "verified": False,
                "candidate": candidate,
                "reason": "could not evaluate conjecture expression at candidate",
            }

        satisfies = parser.satisfies_claim(v, parsed)
        if satisfies:
            return {
                "verified": False,
                "candidate": candidate,
                "reason": (
                    f"candidate evaluates to {v}, which satisfies the parsed claim"
                ),
            }
        return {
            "verified": True,
            "candidate": candidate,
            "reason": f"candidate evaluates to {v}, violating the parsed claim",
        }

    @classmethod
    def _extract_assignment(cls, candidate: str) -> tuple[str, int] | None:
        match = cls._ASSIGNMENT.search(candidate)
        if not match:
            return None
        return match.group("var"), int(match.group("value"))


class _SymbolicClaimParser:
    """Shared parser for symbolic search and local counterexample verification."""

    def parse(self, conjecture: str) -> dict[str, Any]:
        univ_m = SymbolicCounterexampleFinder._UNIV_INT.search(conjecture)
        if not univ_m:
            return SymbolicCounterexampleFinder._not_applicable(
                "No universal integer quantifier detected "
                "(e.g. 'for all integers n', 'for every natural number n')"
            )

        var_name = univ_m.group("var")
        pre_text = conjecture[: univ_m.end()].lower()
        natural_hints = ("natural", "positive", "non-negative", "nonnegative", "whole")
        domain = (
            SymbolicCounterexampleFinder._NAT_RANGE
            if any(h in pre_text for h in natural_hints)
            else SymbolicCounterexampleFinder._INT_RANGE
        )

        snippet = conjecture[univ_m.end() :].lstrip(", \t")
        snippet = re.sub(
            r"^" + re.escape(var_name) + r"\s*(?:>=?|<=?|[≥≤])\s*-?\d+\s*,\s*",
            "",
            snippet,
            flags=re.IGNORECASE,
        )

        is_m = re.search(r"\b(?:is|are)\b", snippet, re.IGNORECASE)
        if not is_m:
            return SymbolicCounterexampleFinder._not_applicable(
                "Could not locate 'is/are' predicate after the quantifier"
            )

        expr_raw = snippet[: is_m.start()].strip().strip(",").strip()
        expr_raw = re.sub(
            r"^(?:the\s+)?(?:expression\s+|quantity\s+|sum\s+|product\s+|value(?:\s+of)?\s+)?",
            "",
            expr_raw,
            flags=re.IGNORECASE,
        ).strip()
        if not expr_raw or var_name.lower() not in expr_raw.lower():
            return SymbolicCounterexampleFinder._not_applicable(
                f"Could not extract a mathematical expression containing '{var_name}' "
                "before the predicate"
            )

        expr_py = expr_raw.replace("^", "**")
        expr_py = re.sub(
            r"(\d)(" + re.escape(var_name) + r")",
            r"\1*\2",
            expr_py,
            flags=re.IGNORECASE,
        )

        try:
            from sympy import Symbol
            from sympy.parsing.sympy_parser import (
                implicit_multiplication_application,
                parse_expr,
                standard_transformations,
            )

            var = Symbol(var_name)
            transforms = standard_transformations + (
                implicit_multiplication_application,
            )
            expr = parse_expr(
                expr_py, local_dict={var_name: var}, transformations=transforms
            )
        except Exception as exc:
            return SymbolicCounterexampleFinder._not_applicable(
                f"Could not parse '{expr_py}' as a sympy expression: {exc}"
            )

        claim_text = snippet[is_m.end() :].strip()
        claim: dict[str, Any] | None = None
        if m := re.search(r"\bdivisible\s+by\s+(\d+)", claim_text, re.IGNORECASE):
            claim = {"type": "congruence", "modulus": int(m.group(1)), "remainder": 0}
        elif re.search(r"\beven\b", claim_text, re.IGNORECASE):
            claim = {"type": "congruence", "modulus": 2, "remainder": 0}
        elif re.search(r"\bodd\b", claim_text, re.IGNORECASE):
            claim = {"type": "congruence", "modulus": 2, "remainder": 1}
        elif re.search(r"\bprime\b", claim_text, re.IGNORECASE):
            claim = {"type": "prime"}
        elif re.search(r"perfect\s+square", claim_text, re.IGNORECASE):
            claim = {"type": "perfect_square"}

        if claim is None:
            return SymbolicCounterexampleFinder._not_applicable(
                f"Claim type not in supported set: '{claim_text[:60]}'. "
                "Supported: divisible by N, even, odd, prime, perfect square."
            )

        return {
            "method": "symbolic",
            "applicable": True,
            "found": False,
            "counterexample": None,
            "reasoning": "",
            "var_name": var_name,
            "var": var,
            "expr": expr,
            "domain": domain,
            "claim": claim,
        }

    @staticmethod
    def satisfies_claim(value: int, parsed: dict[str, Any]) -> bool:
        claim = parsed["claim"]
        if claim["type"] == "congruence":
            return value % claim["modulus"] == claim["remainder"]
        if claim["type"] == "prime":
            import sympy

            return value >= 2 and bool(sympy.isprime(value))
        if claim["type"] == "perfect_square":
            return value >= 0 and math.isqrt(value) ** 2 == value
        raise ValueError(f"Unsupported claim type: {claim['type']}")


class WolframQueryCache:
    """Tiny JSON-file cache for Wolfram Alpha query responses."""

    def __init__(self, ttl_seconds: int, cache_dir: Path | None = None) -> None:
        self._ttl_seconds = ttl_seconds
        self._cache_dir = cache_dir or Path(".cache") / "wolfram"

    def get(self, statement_hash: str, wolfram_query: str) -> Any | None:
        path = self._path(statement_hash, wolfram_query)
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            created_at = float(data.get("created_at", 0))
            if self._ttl_seconds <= 0 or time.time() - created_at > self._ttl_seconds:
                return None
            return data.get("value")
        except (OSError, json.JSONDecodeError, TypeError, ValueError):
            return None

    def set(self, statement_hash: str, wolfram_query: str, value: Any) -> None:
        path = self._path(statement_hash, wolfram_query)
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(
                json.dumps({"created_at": time.time(), "value": value}),
                encoding="utf-8",
            )
        except OSError as exc:
            logger.debug("Could not write Wolfram cache entry %s: %s", path, exc)

    def _path(self, statement_hash: str, wolfram_query: str) -> Path:
        cache_key = _stable_hash(f"{statement_hash}:{wolfram_query}")
        return self._cache_dir / f"{cache_key}.json"


# ---------------------------------------------------------------------------
# LLM-based finder (unchanged from original)
# ---------------------------------------------------------------------------


class CounterexampleFinder:
    """Asks Claude to find a concrete counterexample for a failed conjecture."""

    def __init__(self, settings: Settings | None = None) -> None:
        self._settings = settings or Settings()
        self._client = anthropic.Anthropic(api_key=self._settings.anthropic_api_key)

    @retry(
        retry=retry_if_exception_type(
            (anthropic.RateLimitError, anthropic.APIConnectionError)
        ),
        wait=wait_exponential(multiplier=1, min=2, max=60),
        stop=stop_after_attempt(4),
        reraise=True,
    )
    def _call_api(self, conjecture: str, subfield: str) -> str:
        context = f"Subfield: {subfield}\n\n" if subfield else ""
        response = self._client.messages.create(
            model=self._settings.claude_model,
            max_tokens=2048,
            system=[
                {
                    "type": "text",
                    "text": _SYSTEM_PROMPT,
                    "cache_control": {"type": "ephemeral"},
                }
            ],
            messages=[
                {
                    "role": "user",
                    "content": f"{context}Conjecture:\n{conjecture}",
                }
            ],
        )
        return response.content[0].text  # type: ignore[union-attr]

    def search(self, conjecture: str, subfield: str = "") -> dict[str, Any]:
        """Search for a counterexample to the given conjecture.

        Returns:
            Dict with keys: found (bool), counterexample (str | None), reasoning (str).
        """
        conjecture = conjecture.strip()
        if not conjecture:
            raise ValueError("conjecture must be non-empty")

        logger.info("Searching for counterexample (subfield=%r)", subfield)

        try:
            raw = self._call_api(conjecture, subfield)
        except Exception as exc:
            logger.error("Counterexample API call failed: %s", exc)
            return {
                "found": False,
                "counterexample": None,
                "reasoning": f"API error: {exc}",
            }

        import json

        text = raw.strip()
        if text.startswith("```"):
            lines = text.splitlines()
            text = "\n".join(lines[1:-1] if lines[-1].strip() == "```" else lines[1:])

        try:
            data = json.loads(text)
            found = bool(data.get("found", False))
            counterexample = data.get("counterexample") or None
            reasoning = str(data.get("reasoning", ""))
            if found and not counterexample:
                found = False
            logger.info("Counterexample search result: found=%s", found)
            return {
                "found": found,
                "counterexample": counterexample,
                "reasoning": reasoning,
            }
        except (json.JSONDecodeError, KeyError) as exc:
            logger.warning(
                "Could not parse counterexample response: %s\nRaw: %s", exc, raw
            )
            return {"found": False, "counterexample": None, "reasoning": raw}


# ---------------------------------------------------------------------------
# Symbolic / brute-force finder (independent, non-LLM)
# ---------------------------------------------------------------------------


class SymbolicCounterexampleFinder:
    """Brute-force / CAS counterexample search using sympy.

    Runs independently of the LLM finder: different method, different failure modes.

    Applicable conjecture types (decided by pattern matching, not semantic parsing):
      - Claims of the form "for all/every/any/each integer[s]/natural number[s] n, <expr> is <property>"
      - Supported properties: divisible by k, even, odd, prime, perfect square

    Explicitly NOT applicable (returns applicable=False) for:
      - Claims about infinite algebraic structures (groups, rings, topological spaces, etc.)
        where no bounded enumeration is evident from the text
      - Multi-variable claims (only one-variable integer claims are handled)
      - Conjectures whose expression cannot be parsed as a sympy arithmetic expression
      - Claim types not in the supported list (e.g., "is continuous", "converges to")

    The domain is finite: integers in [-100, 100] or naturals in [0, 200].
    "No counterexample found" here only means none exists in this bounded sample —
    it is not a mathematical proof.
    """

    # Integers checked for "for all integers n, ..." claims
    _INT_RANGE: range = range(-100, 101)  # 201 values

    # Naturals checked for "for all natural/positive/non-negative integers n, ..." claims
    _NAT_RANGE: range = range(0, 201)  # 201 values

    # Detect universal quantifier over integers/naturals with a single variable
    _UNIV_INT = re.compile(
        r"\bfor\s+(?:all|every|any|each)\s+"
        r"(?:(?:non-?negative|positive|natural|whole)\s+)?"
        r"(?:integers?|natural\s+numbers?|whole\s+numbers?)\s+"
        r"(?P<var>[a-z])\b",
        re.IGNORECASE,
    )

    def search(self, conjecture: str, subfield: str = "") -> dict[str, Any]:
        """Attempt a brute-force/symbolic counterexample check.

        Returns dict with keys:
          method          "symbolic"
          applicable      bool — False means the conjecture type is outside scope
          found           bool
          counterexample  str | None
          reasoning       str
        """
        try:
            return self._check(conjecture.strip())
        except Exception as exc:
            logger.debug("Symbolic CX check raised unexpected exception: %s", exc)
            return {
                "method": "symbolic",
                "applicable": False,
                "found": False,
                "counterexample": None,
                "reasoning": f"Symbolic check aborted due to unexpected error: {exc}",
            }

    # ------------------------------------------------------------------
    # Internal pipeline
    # ------------------------------------------------------------------

    def _check(self, conjecture: str) -> dict[str, Any]:
        # 1. Detect universal integer quantifier + single variable
        univ_m = self._UNIV_INT.search(conjecture)
        if not univ_m:
            return self._not_applicable(
                "No universal integer quantifier detected "
                "(e.g. 'for all integers n', 'for every natural number n')"
            )

        var_name = univ_m.group("var")

        # 2. Choose domain: naturals vs full integers
        pre_text = conjecture[: univ_m.end()].lower()
        natural_hints = ("natural", "positive", "non-negative", "nonnegative", "whole")
        domain = (
            self._NAT_RANGE
            if any(h in pre_text for h in natural_hints)
            else self._INT_RANGE
        )

        # 3. Extract the arithmetic expression (text between quantifier and "is/are")
        after_quant = conjecture[univ_m.end() :]
        snippet = after_quant.lstrip(", \t")

        # Strip leading constraints like "n >= 0," or "n > 1,"
        snippet = re.sub(
            r"^" + re.escape(var_name) + r"\s*(?:>=?|<=?|[≥≤])\s*-?\d+\s*,\s*",
            "",
            snippet,
            flags=re.IGNORECASE,
        )

        is_m = re.search(r"\b(?:is|are)\b", snippet, re.IGNORECASE)
        if not is_m:
            return self._not_applicable(
                "Could not locate 'is/are' predicate after the quantifier"
            )

        expr_raw = snippet[: is_m.start()].strip().strip(",").strip()

        # Remove leading prose words ("the expression", "the sum", etc.)
        expr_raw = re.sub(
            r"^(?:the\s+)?(?:expression\s+|quantity\s+|sum\s+|product\s+|value(?:\s+of)?\s+)?",
            "",
            expr_raw,
            flags=re.IGNORECASE,
        ).strip()

        if not expr_raw or var_name.lower() not in expr_raw.lower():
            return self._not_applicable(
                f"Could not extract a mathematical expression containing '{var_name}' "
                "before the predicate"
            )

        # 4. Normalize: Python-style arithmetic
        expr_py = expr_raw.replace("^", "**")
        # 2n → 2*n, 3n^2 → 3*n**2 (already replaced ^)
        expr_py = re.sub(
            r"(\d)(" + re.escape(var_name) + r")",
            r"\1*\2",
            expr_py,
            flags=re.IGNORECASE,
        )

        # 5. Parse with sympy
        try:
            from sympy import Symbol
            from sympy.parsing.sympy_parser import (
                implicit_multiplication_application,
                parse_expr,
                standard_transformations,
            )

            var = Symbol(var_name)
            transforms = standard_transformations + (
                implicit_multiplication_application,
            )
            expr = parse_expr(
                expr_py, local_dict={var_name: var}, transformations=transforms
            )
        except Exception as exc:
            return self._not_applicable(
                f"Could not parse '{expr_py}' as a sympy expression: {exc}"
            )

        # 6. Identify and check claim type from text after "is/are"
        claim_text = snippet[is_m.end() :].strip()

        if m := re.search(r"\bdivisible\s+by\s+(\d+)", claim_text, re.IGNORECASE):
            k = int(m.group(1))
            return self._check_congruence(
                expr, var, var_name, domain, k, 0, f"divisible by {k}"
            )

        if re.search(r"\beven\b", claim_text, re.IGNORECASE):
            return self._check_congruence(expr, var, var_name, domain, 2, 0, "even")

        if re.search(r"\bodd\b", claim_text, re.IGNORECASE):
            return self._check_congruence(expr, var, var_name, domain, 2, 1, "odd")

        if re.search(r"\bprime\b", claim_text, re.IGNORECASE):
            return self._check_primality(expr, var, var_name, domain)

        if re.search(r"perfect\s+square", claim_text, re.IGNORECASE):
            return self._check_perfect_square(expr, var, var_name, domain)

        return self._not_applicable(
            f"Claim type not in supported set: '{claim_text[:60]}'. "
            "Supported: divisible by N, even, odd, prime, perfect square."
        )

    # ------------------------------------------------------------------
    # Domain checkers
    # ------------------------------------------------------------------

    @staticmethod
    def _eval_int(expr: Any, var: Any, n: int) -> int | None:
        """Evaluate expr at integer n; return None if evaluation fails."""
        try:
            return int(expr.subs(var, n))
        except (TypeError, ValueError, AttributeError):
            return None

    def _check_congruence(
        self,
        expr: Any,
        var: Any,
        var_name: str,
        domain: range,
        modulus: int,
        expected_rem: int,
        claim_label: str,
    ) -> dict[str, Any]:
        """Check expr(n) ≡ expected_rem (mod modulus) for all n in domain."""
        for n in domain:
            v = self._eval_int(expr, var, n)
            if v is None:
                continue
            if v % modulus != expected_rem:
                actual = (
                    "even"
                    if modulus == 2 and v % 2 == 0
                    else "odd"
                    if modulus == 2
                    else f"≡ {v % modulus} (mod {modulus})"
                )
                return {
                    "method": "symbolic",
                    "applicable": True,
                    "found": True,
                    "counterexample": (
                        f"{var_name} = {n}: expression = {v}, which is {actual} "
                        f"(violates: {claim_label})"
                    ),
                    "reasoning": (
                        f"Brute-force enumeration over {len(domain)} integer values "
                        f"found {var_name} = {n} where the expression evaluates to {v}, "
                        f"which is NOT {claim_label}."
                    ),
                }

        return {
            "method": "symbolic",
            "applicable": True,
            "found": False,
            "counterexample": None,
            "reasoning": (
                f"Checked {len(domain)} integer values in the domain "
                f"[{domain.start}, {domain.stop - 1}]; "
                f"the expression is {claim_label} at every tested point. "
                "No counterexample found by exhaustive search over this sample "
                "(this is not a mathematical proof)."
            ),
        }

    def _check_primality(
        self,
        expr: Any,
        var: Any,
        var_name: str,
        domain: range,
    ) -> dict[str, Any]:
        import sympy

        for n in domain:
            v = self._eval_int(expr, var, n)
            if v is None:
                continue
            if v < 2 or not sympy.isprime(v):
                verdict = (
                    f"< 2 (value: {v})"
                    if v < 2
                    else f"composite — factors: {sympy.factorint(v)}"
                )
                return {
                    "method": "symbolic",
                    "applicable": True,
                    "found": True,
                    "counterexample": (
                        f"{var_name} = {n}: expression = {v}, which is NOT prime ({verdict})"
                    ),
                    "reasoning": (
                        f"Brute-force enumeration found {var_name} = {n} where the "
                        f"expression evaluates to {v}, which is not prime."
                    ),
                }

        return {
            "method": "symbolic",
            "applicable": True,
            "found": False,
            "counterexample": None,
            "reasoning": (
                f"Checked {len(domain)} values in [{domain.start}, {domain.stop - 1}]; "
                "expression appears prime at every tested point. "
                "No counterexample found by exhaustive search over this sample."
            ),
        }

    def _check_perfect_square(
        self,
        expr: Any,
        var: Any,
        var_name: str,
        domain: range,
    ) -> dict[str, Any]:
        for n in domain:
            v = self._eval_int(expr, var, n)
            if v is None:
                continue
            if v < 0 or math.isqrt(v) ** 2 != v:
                verdict = (
                    f"negative ({v})"
                    if v < 0
                    else f"not a perfect square (√{v} ≈ {math.sqrt(v):.3f})"
                )
                return {
                    "method": "symbolic",
                    "applicable": True,
                    "found": True,
                    "counterexample": (
                        f"{var_name} = {n}: expression = {v}, which is {verdict}"
                    ),
                    "reasoning": (
                        f"Brute-force enumeration found {var_name} = {n} where "
                        f"the expression = {v}, which is NOT a perfect square."
                    ),
                }

        return {
            "method": "symbolic",
            "applicable": True,
            "found": False,
            "counterexample": None,
            "reasoning": (
                f"Checked {len(domain)} values; expression is a perfect square at "
                "every tested point. No counterexample found over this sample."
            ),
        }

    @staticmethod
    def _not_applicable(reason: str) -> dict[str, Any]:
        return {
            "method": "symbolic",
            "applicable": False,
            "found": False,
            "counterexample": None,
            "reasoning": f"Not applicable: {reason}",
        }


# ---------------------------------------------------------------------------
# Wolfram Alpha finder (independent external CAS/knowledge engine)
# ---------------------------------------------------------------------------


class WolframCounterexampleFinder:
    """Counterexample search using Wolfram Alpha when an App ID is configured."""

    _FOUND_HINTS = (
        "counterexample",
        "counter-example",
        "is false",
        "statement is false",
        "false for",
        "does not hold",
        "not true",
        "violates",
    )
    _NO_HINTS = (
        "no counterexample",
        "no counter-example",
        "not false",
        "is not false",
        "statement is true",
    )

    def __init__(self, settings: Settings | None = None) -> None:
        self._settings = settings or Settings()

    def search(self, conjecture: str, subfield: str = "") -> dict[str, Any]:
        """Query Wolfram Alpha for counterexample evidence.

        Returns dict with keys:
          method          "wolfram"
          applicable      bool
          found           bool
          counterexample  str | None
          reasoning       str
        """
        conjecture = conjecture.strip()
        if not self._settings.wolfram_app_id:
            return self._not_applicable("Wolfram Alpha App ID not configured")
        if wolframalpha is None:
            return self._not_applicable("wolframalpha package is not installed")

        query = self._build_query(conjecture, subfield)
        statement_hash = _stable_hash(conjecture)
        cache = WolframQueryCache(self._settings.wolfram_cache_ttl_seconds)
        cached_pod_texts = cache.get(statement_hash, query)
        if cached_pod_texts is not None:
            pod_texts = [(str(title), str(text)) for title, text in cached_pod_texts]
        else:
            try:
                client = wolframalpha.Client(self._settings.wolfram_app_id)
                response = client.query(query)
                pod_texts = self._extract_pod_texts(response)
                cache.set(statement_hash, query, pod_texts)
            except Exception as exc:
                logger.debug("Wolfram Alpha counterexample search failed: %s", exc)
                return self._not_applicable(f"Wolfram Alpha query failed: {exc}")

        if not pod_texts:
            return self._not_applicable("Wolfram Alpha returned no readable pod text")

        parsed = self._parse_pods(pod_texts)
        if parsed is not None:
            return parsed

        raw = self._format_raw_pods(pod_texts)
        return self._not_applicable(
            "Wolfram Alpha response did not contain a clear yes/no, false-statement, "
            f"or counterexample-bearing pod. Raw pod text: {raw}"
        )

    @staticmethod
    def _build_query(conjecture: str, subfield: str) -> str:
        context = f" in {subfield}" if subfield else ""
        return (
            "Is this mathematical statement false? "
            f"If false, give a concrete counterexample{context}: {conjecture}"
        )

    @classmethod
    def _extract_pod_texts(cls, response: Any) -> list[tuple[str, str]]:
        pods = getattr(response, "pods", None) or []
        pod_texts: list[tuple[str, str]] = []
        for pod in pods:
            title = str(getattr(pod, "title", "") or "")
            texts: list[str] = []

            direct_text = getattr(pod, "text", None)
            if direct_text:
                texts.append(str(direct_text))

            subpods = getattr(pod, "subpods", None) or []
            for subpod in subpods:
                plaintext = getattr(subpod, "plaintext", None)
                if plaintext:
                    texts.append(str(plaintext))
                subpod_text = getattr(subpod, "text", None)
                if subpod_text:
                    texts.append(str(subpod_text))

            text = "\n".join(t.strip() for t in texts if t and t.strip())
            if text:
                pod_texts.append((title, text))
        return pod_texts

    @classmethod
    def _parse_pods(cls, pod_texts: list[tuple[str, str]]) -> dict[str, Any] | None:
        for title, text in pod_texts:
            haystack = f"{title}\n{text}".lower()
            if cls._looks_like_counterexample(title, text):
                counterexample = cls._clean_counterexample_text(text)
                return {
                    "method": "wolfram",
                    "applicable": True,
                    "found": True,
                    "counterexample": counterexample,
                    "reasoning": f"Wolfram Alpha returned counterexample evidence in pod '{title}'.",
                }

            if re.search(r"\b(false|statement is false|is false)\b", haystack):
                counterexample = cls._clean_counterexample_text(text)
                return {
                    "method": "wolfram",
                    "applicable": True,
                    "found": True,
                    "counterexample": counterexample,
                    "reasoning": f"Wolfram Alpha indicated the statement is false in pod '{title}'.",
                }

            yes_no = cls._parse_yes_no(text)
            if yes_no == "yes":
                return {
                    "method": "wolfram",
                    "applicable": True,
                    "found": True,
                    "counterexample": cls._clean_counterexample_text(text),
                    "reasoning": (
                        f"Wolfram Alpha answered yes to the falsity/counterexample query "
                        f"in pod '{title}'."
                    ),
                }
            if yes_no == "no":
                return {
                    "method": "wolfram",
                    "applicable": True,
                    "found": False,
                    "counterexample": None,
                    "reasoning": (
                        f"Wolfram Alpha answered no to the falsity/counterexample query "
                        f"in pod '{title}'. This is not a proof."
                    ),
                }

        return None

    @classmethod
    def _looks_like_counterexample(cls, title: str, text: str) -> bool:
        haystack = f"{title}\n{text}".lower()
        if any(hint in haystack for hint in cls._FOUND_HINTS):
            return not any(no_hint in haystack for no_hint in cls._NO_HINTS)
        return False

    @staticmethod
    def _parse_yes_no(text: str) -> str | None:
        normalized = re.sub(r"\s+", " ", text.strip().lower())
        if re.fullmatch(r"(yes|true)(?:[.;:].*)?", normalized):
            return "yes"
        if re.fullmatch(r"(no|false)(?:[.;:].*)?", normalized):
            return "no"
        return None

    @staticmethod
    def _clean_counterexample_text(text: str) -> str:
        return re.sub(r"\s+", " ", text).strip()

    @staticmethod
    def _format_raw_pods(pod_texts: list[tuple[str, str]]) -> str:
        snippets = []
        for title, text in pod_texts[:5]:
            label = title or "Untitled pod"
            clean_text = re.sub(r"\s+", " ", text).strip()
            snippets.append(f"{label}: {clean_text[:300]}")
        return " | ".join(snippets)

    @staticmethod
    def _not_applicable(reason: str) -> dict[str, Any]:
        return {
            "method": "wolfram",
            "applicable": False,
            "found": False,
            "counterexample": None,
            "reasoning": reason,
        }


# ---------------------------------------------------------------------------
# Combined ensemble search
# ---------------------------------------------------------------------------


def _run_backend_searches(
    conjecture: str,
    subfield: str,
    settings: Settings | None,
) -> dict[str, dict[str, Any]]:
    callables = {
        "claude": lambda: CounterexampleFinder(settings).search(conjecture, subfield),
        "sympy": lambda: SymbolicCounterexampleFinder().search(conjecture, subfield),
        "wolfram_alpha": lambda: WolframCounterexampleFinder(settings).search(
            conjecture, subfield
        ),
    }
    results: dict[str, dict[str, Any]] = {}
    executor = concurrent.futures.ThreadPoolExecutor(max_workers=len(callables))
    futures = {executor.submit(search): source for source, search in callables.items()}
    deadline = time.monotonic() + BACKEND_TIMEOUT_SECONDS

    try:
        for future, source in futures.items():
            remaining = max(0.0, deadline - time.monotonic())
            try:
                raw_result = future.result(timeout=remaining)
            except concurrent.futures.TimeoutError:
                results[source] = _method_timeout_result(source)
            except Exception as exc:
                logger.error("%s counterexample search failed: %s", source, exc)
                results[source] = {
                    "method": {
                        "claude": "llm",
                        "sympy": "symbolic",
                        "wolfram_alpha": "wolfram",
                    }[source],
                    "source": source,
                    "applicable": True,
                    "found": False,
                    "counterexample": None,
                    "reasoning": f"{source} search error: {exc}",
                    "error": str(exc),
                }
            else:
                results[source] = _normalize_method_result(
                    raw_result, source, conjecture
                )
    finally:
        for future in futures:
            if not future.done():
                future.cancel()
        executor.shutdown(wait=False, cancel_futures=True)

    for source in callables:
        results.setdefault(source, _method_timeout_result(source))
    return results


def _consensus(method_results: list[dict[str, Any]]) -> str:
    if any(result.get("found", False) for result in method_results):
        return CONSENSUS_COUNTEREXAMPLE_FOUND
    if any(result.get("timed_out") or result.get("error") for result in method_results):
        return CONSENSUS_PARTIAL_FAILURE
    return CONSENSUS_UNREFUTED


def _disagreement(methods_by_source: dict[str, dict[str, Any]]) -> dict[str, bool]:
    return {
        "claude_found": bool(methods_by_source["claude"].get("found", False)),
        "sympy_found": bool(methods_by_source["sympy"].get("found", False)),
        "wolfram_found": bool(methods_by_source["wolfram_alpha"].get("found", False)),
    }


def _aggregate_reasoning(method_results: list[tuple[str, dict[str, Any]]]) -> str:
    found_results = [
        (label, result) for label, result in method_results if result.get("found")
    ]
    if found_results:
        return "; ".join(
            f"{label}: {result.get('counterexample') or result.get('reasoning', '')}"
            for label, result in found_results
        )

    summaries = [
        f"{label}: {str(result.get('reasoning', ''))[:150]}"
        for label, result in method_results
    ]
    return (
        "No configured/applicable method found a locally verified counterexample. "
        + " | ".join(summaries)
    )


def search_ensemble(
    conjecture: str,
    subfield: str = "",
    settings: Settings | None = None,
) -> dict[str, Any]:
    """Run Claude, SymPy, and Wolfram counterexample searches as an ensemble.

    Returns a combined dict that is a strict superset of the old single-method
    format, so existing callers reading only {found, counterexample, reasoning}
    continue to work without changes:

        {
            "found": bool,            # True if either method found one
            "counterexample": ...,    # from whichever method found it, or None
            "reasoning": str,         # brief combined summary
            "llm_result": {
                "method": "llm",
                "applicable": True,
                "found": bool,
                "counterexample": ...,
                "reasoning": str,
            },
            "symbolic_result": {
                "method": "symbolic",
                "applicable": bool,   # False when conjecture is out-of-scope
                "found": bool,
                "counterexample": ...,
                "reasoning": str,
            },
            "wolfram_result": {
                "method": "wolfram",
                "applicable": bool,   # False when not configured or response is ambiguous
                "found": bool,
                "counterexample": ...,
                "reasoning": str,
            },
            "methods_attempted": 3,
            "methods_applicable": int,
            "methods_found_counterexample": int,
            "consensus": "counterexample_found" | "unrefuted" | "partial_failure",
            "method_disagreement": {
                "claude_found": bool,
                "sympy_found": bool,
                "wolfram_found": bool,
            },
        }
    """
    conjecture = conjecture.strip()
    if not conjecture:
        raise ValueError("conjecture must be non-empty")

    methods_by_source = _run_backend_searches(conjecture, subfield, settings)
    llm_result = methods_by_source["claude"]
    sym_result = methods_by_source["sympy"]
    wolfram_result = methods_by_source["wolfram_alpha"]

    method_results = [
        ("LLM", llm_result),
        ("Symbolic", sym_result),
        ("Wolfram", wolfram_result),
    ]

    found = any(result.get("found", False) for _, result in method_results)
    counterexample: str | None = next(
        (
            result.get("counterexample")
            for _, result in method_results
            if result.get("found") and result.get("counterexample")
        ),
        None,
    )

    method_result_dicts = [result for _, result in method_results]
    disagreement = _disagreement(methods_by_source)
    if len(set(disagreement.values())) > 1:
        logger.info("Counterexample backend disagreement: %s", disagreement)

    consensus = _consensus(method_result_dicts)

    return {
        "found": found,
        "counterexample": counterexample,
        "reasoning": _aggregate_reasoning(method_results),
        "llm_result": llm_result,
        "symbolic_result": sym_result,
        "wolfram_result": wolfram_result,
        "methods_attempted": len(method_results),
        "methods_applicable": sum(
            1 for result in method_result_dicts if result.get("applicable", True)
        ),
        "methods_found_counterexample": sum(
            1 for result in method_result_dicts if result.get("found", False)
        ),
        "consensus": consensus,
        "method_disagreement": disagreement,
    }


def search_dual(
    conjecture: str,
    subfield: str = "",
    settings: Settings | None = None,
) -> dict[str, Any]:
    """Backward-compatible wrapper for the three-method ensemble search."""
    return search_ensemble(conjecture, subfield, settings)
