"""Counterexample finder module.

When automated proof search fails, independent methods run in parallel to
search for a concrete counterexample:

1. LLM-based (CounterexampleFinder): asks Claude to reason about the conjecture.
2. Symbolic/brute-force (SymbolicCounterexampleFinder): uses sympy to enumerate a
   bounded integer domain. Independent of the LLM; can neither share its blind
   spots nor confirm its biases.
3. Wolfram Alpha (WolframCounterexampleFinder): queries a third-party CAS/knowledge
   engine when configured. Independent of both Claude and local sympy.

"No counterexample found" from *one* source is absence-of-disproof, not evidence
of truth. Two independent failures-to-disprove are stronger, but still not a proof.
Use search_dual() to run all configured methods and get a combined, structured result.
"""

from __future__ import annotations

import logging
import math
import re
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

        try:
            client = wolframalpha.Client(self._settings.wolfram_app_id)
            response = client.query(query)
            pod_texts = self._extract_pod_texts(response)
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
# Combined dual search
# ---------------------------------------------------------------------------


def search_dual(
    conjecture: str,
    subfield: str = "",
    settings: Settings | None = None,
) -> dict[str, Any]:
    """Run LLM, symbolic, and Wolfram counterexample searches independently.

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
        }
    """
    conjecture = conjecture.strip()
    if not conjecture:
        raise ValueError("conjecture must be non-empty")

    # LLM search
    llm_finder = CounterexampleFinder(settings)
    try:
        llm_raw = llm_finder.search(conjecture, subfield)
        llm_result: dict[str, Any] = {
            "method": "llm",
            "applicable": True,
            "found": llm_raw["found"],
            "counterexample": llm_raw.get("counterexample"),
            "reasoning": llm_raw.get("reasoning", ""),
        }
    except Exception as exc:
        logger.error("LLM counterexample search failed: %s", exc)
        llm_result = {
            "method": "llm",
            "applicable": True,
            "found": False,
            "counterexample": None,
            "reasoning": f"LLM search error: {exc}",
        }

    # Symbolic search (independent: different method, different failure modes)
    sym_finder = SymbolicCounterexampleFinder()
    sym_result = sym_finder.search(conjecture, subfield)

    # Wolfram Alpha search (independent external engine, optional configuration)
    wolfram_finder = WolframCounterexampleFinder(settings)
    wolfram_result = wolfram_finder.search(conjecture, subfield)

    method_results = [
        ("LLM", llm_result),
        ("Symbolic", sym_result),
        ("Wolfram", wolfram_result),
    ]

    # Aggregate: found = True if any method found one
    found = any(result["found"] for _, result in method_results)
    counterexample: str | None = next(
        (
            result.get("counterexample")
            for _, result in method_results
            if result["found"] and result.get("counterexample")
        ),
        None,
    )

    if found:
        sources = []
        for label, result in method_results:
            if result["found"]:
                sources.append(
                    f"{label}: {result.get('counterexample') or result.get('reasoning', '')}"
                )
        reasoning = "; ".join(sources)
    else:
        no_counterexample_summaries = [
            f"{label}: {result.get('reasoning', '')[:150]}"
            for label, result in method_results
            if result.get("applicable", True)
        ]
        unavailable_summaries = [
            f"{label}: {result.get('reasoning', '')[:150]}"
            for label, result in method_results
            if not result.get("applicable", True)
        ]
        reasoning = (
            "No configured/applicable method found a counterexample. "
            + " | ".join(no_counterexample_summaries + unavailable_summaries)
        )

    return {
        "found": found,
        "counterexample": counterexample,
        "reasoning": reasoning,
        "llm_result": llm_result,
        "symbolic_result": sym_result,
        "wolfram_result": wolfram_result,
    }
