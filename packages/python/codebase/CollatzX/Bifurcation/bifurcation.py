#!/usr/bin/env python3
"""
Algebraic Structure Toolkit (AST)
==============================================================================
A practical utility for defining, analyzing, and visualizing algebraic structures
and their properties.
"""

from __future__ import annotations

# ============ 1) Imports & Utilities ============================================================
import argparse
import json
import logging
import math
import os
import random
import sys
import textwrap
from dataclasses import dataclass, field
from enum import Enum, auto
from pathlib import Path
from time import time
from typing import Any, Callable, Dict, Iterable, List, Optional, Protocol, Sequence, Tuple, Union

# Optional/3rd-party imports with graceful fallbacks
try:
    import numpy as np
except Exception:  # pragma: no cover
    np = None  # type: ignore

try:
    import sympy as sym
except Exception:  # pragma: no cover
    sym = None  # type: ignore

try:
    import networkx as nx
except Exception:  # pragma: no cover
    nx = None  # type: ignore

try:
    import yaml  # for YAML config (optional)
except Exception:  # pragma: no cover
    yaml = None  # type: ignore

try:
    from tqdm import tqdm
except Exception:  # pragma: no cover
    def tqdm(x, **kwargs):  # type: ignore
        return x

# Plotly optional (used for HTML/interactive export)
try:
    import plotly.graph_objects as go
except Exception:  # pragma: no cover
    go = None  # type: ignore

# ============ 2) Config & Logging ==============================================================

DEFAULT_RESULTS_DIR = Path("results")
DEFAULT_RESULTS_DIR.mkdir(parents=True, exist_ok=True)

class LogStyle(Enum):
    TEXT = auto()
    JSON = auto()


def set_reproducible_seeds(seed: int = 1337) -> None:
    random.seed(seed)
    try:
        import numpy as _np
        _np.random.seed(seed)
    except Exception:
        pass


def configure_logging(level: str = "INFO", style: LogStyle = LogStyle.TEXT) -> None:
    logger = logging.getLogger()
    logger.handlers.clear()
    logger.setLevel(getattr(logging, level.upper(), logging.INFO))
    handler = logging.StreamHandler(sys.stdout)

    if style == LogStyle.JSON:
        class JsonFormatter(logging.Formatter):
            def format(self, record: logging.LogRecord) -> str:  # noqa: D401
                payload = {
                    "time": self.formatTime(record, "%Y-%m-%dT%H:%M:%S"),
                    "level": record.levelname,
                    "name": record.name,
                    "msg": record.getMessage(),
                }
                return json.dumps(payload)
        handler.setFormatter(JsonFormatter())
    else:
        formatter = logging.Formatter("[%(levelname)s] %(message)s")
        handler.setFormatter(formatter)

    logger.addHandler(handler)


def load_config(config_path: Optional[str]) -> Dict[str, Any]:
    if not config_path:
        return {}
    p = Path(config_path)
    if not p.exists():
        logging.warning("Config file not found: %s", config_path)
        return {}
    try:
        if p.suffix.lower() in {".yml", ".yaml"} and yaml is not None:
            with p.open("r", encoding="utf-8") as f:
                return yaml.safe_load(f) or {}
        with p.open("r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:  # pragma: no cover
        logging.exception("Failed to load config %s: %s", config_path, e)
        return {}


# ============ 3) Domain Models ================================================================

class StructureType(Enum):
    """Types of algebraic structures with increasing constraints."""
    MAGMA = auto()           # Closed under binary operation
    SEMIGROUP = auto()       # + Associative
    MONOID = auto()          # + Identity element  
    GROUP = auto()           # + Inverse elements
    ABELIAN_GROUP = auto()   # + Commutative
    RING = auto()            # + Two operations, distributive
    FIELD = auto()           # + Multiplicative inverses (except zero)
    VECTOR_SPACE = auto()    # + Scalar multiplication
    MODULE = auto()          # + Ring action
    ALGEBRA = auto()         # + Bilinear product


class VerificationStatus(Enum):
    """Status of property verification."""
    UNVERIFIED = auto()
    VERIFIED = auto()
    REFUTED = auto()
    INCONSISTENT = auto()


@dataclass
class PropertyAssertion:
    """A claim about structural properties of an algebraic structure."""
    statement: str
    structure_type: StructureType
    status: VerificationStatus = VerificationStatus.UNVERIFIED
    verification_notes: Optional[str] = None
    dependencies: List[str] = field(default_factory=list)
    counterexamples: List[Any] = field(default_factory=list)


@dataclass
class AlgebraicStructure:
    """Represents an algebraic structure with its properties."""
    name: str
    structure_type: StructureType
    properties: Dict[str, bool] = field(default_factory=dict)
    operations: List[str] = field(default_factory=lambda: ["*"])  # Default binary operation
    
    def __post_init__(self) -> None:
        """Set default properties based on structure type."""
        if not self.properties:
            self._set_default_properties()
    
    def _set_default_properties(self) -> None:
        """Set mathematically required properties for the structure type."""
        defaults = {
            StructureType.MAGMA: {"closed": True},
            StructureType.SEMIGROUP: {"closed": True, "associative": True},
            StructureType.MONOID: {"closed": True, "associative": True, "identity": True},
            StructureType.GROUP: {"closed": True, "associative": True, "identity": True, "inverses": True},
            StructureType.ABELIAN_GROUP: {"closed": True, "associative": True, "identity": True, 
                                         "inverses": True, "commutative": True},
            StructureType.RING: {"closed_add": True, "associative_add": True, "identity_add": True,
                               "inverses_add": True, "commutative_add": True, "closed_mult": True,
                               "associative_mult": True, "distributive": True},
            StructureType.FIELD: {"closed_add": True, "associative_add": True, "identity_add": True,
                                "inverses_add": True, "commutative_add": True, "closed_mult": True,
                                "associative_mult": True, "identity_mult": True, "inverses_mult": True,
                                "commutative_mult": True, "distributive": True},
        }
        
        if self.structure_type in defaults:
            self.properties.update(defaults[self.structure_type])


# ============ 4) Property Verification Engine ===================================================

class PropertyVerifier:
    """Verifies consistency of algebraic structure properties."""
    
    def __init__(self) -> None:
        self.known_implications: List[Tuple[List[str], str]] = [
            (["associative", "identity", "inverses"], "group"),
            (["group", "commutative"], "abelian_group"),
            (["associative", "identity"], "monoid"),
            (["associative"], "semigroup"),
            (["closed"], "magma"),
        ]
        
        self.known_contradictions: List[Tuple[str, str]] = [
            ("finite_field", "characteristic_zero"),  # Example contradiction
        ]
    
    def verify_structure(self, structure: AlgebraicStructure) -> List[PropertyAssertion]:
        """Verify property consistency and generate valid implications."""
        assertions = []
        
        # Check type consistency
        type_assertion = self._verify_structure_type(structure)
        if type_assertion:
            assertions.append(type_assertion)
        
        # Check property implications
        implications = self._check_property_implications(structure)
        assertions.extend(implications)
        
        # Check for contradictions
        contradictions = self._check_contradictions(structure)
        assertions.extend(contradictions)
        
        return assertions
    
    def _verify_structure_type(self, structure: AlgebraicStructure) -> Optional[PropertyAssertion]:
        """Verify that the structure has properties consistent with its declared type."""
        required_props = self._get_required_properties(structure.structure_type)
        missing = [prop for prop in required_props if not structure.properties.get(prop, False)]
        
        if missing:
            return PropertyAssertion(
                statement=f"Structure {structure.name} missing required properties for {structure.structure_type.name}: {missing}",
                structure_type=structure.structure_type,
                status=VerificationStatus.INCONSISTENT,
                verification_notes=f"Required properties: {required_props}"
            )
        
        return PropertyAssertion(
            statement=f"Structure {structure.name} has consistent properties for {structure.structure_type.name}",
            structure_type=structure.structure_type,
            status=VerificationStatus.VERIFIED,
            dependencies=[structure.name]
        )
    
    def _get_required_properties(self, structure_type: StructureType) -> List[str]:
        """Get required properties for each structure type."""
        requirements = {
            StructureType.SEMIGROUP: ["closed", "associative"],
            StructureType.MONOID: ["closed", "associative", "identity"],
            StructureType.GROUP: ["closed", "associative", "identity", "inverses"],
            StructureType.ABELIAN_GROUP: ["closed", "associative", "identity", "inverses", "commutative"],
            StructureType.RING: ["closed_add", "associative_add", "identity_add", "inverses_add", 
                               "commutative_add", "closed_mult", "associative_mult", "distributive"],
        }
        return requirements.get(structure_type, [])
    
    def _check_property_implications(self, structure: AlgebraicStructure) -> List[PropertyAssertion]:
        """Check which known property implications apply to this structure."""
        assertions = []
        
        for premises, conclusion in self.known_implications:
            if all(structure.properties.get(premise, False) for premise in premises):
                assertion = PropertyAssertion(
                    statement=f"If {', '.join(premises)} then {conclusion}",
                    structure_type=structure.structure_type,
                    status=VerificationStatus.VERIFIED,
                    dependencies=[structure.name],
                    verification_notes="Valid property implication"
                )
                assertions.append(assertion)
        
        return assertions
    
    def _check_contradictions(self, structure: AlgebraicStructure) -> List[PropertyAssertion]:
        """Check for property contradictions."""
        assertions = []
        
        # Example: If it's a finite field, it can't have characteristic zero
        if (structure.properties.get("finite", False) and 
            structure.properties.get("field", False) and
            structure.properties.get("characteristic_zero", False)):
            
            assertion = PropertyAssertion(
                statement="Finite field cannot have characteristic zero",
                structure_type=structure.structure_type,
                status=VerificationStatus.REFUTED,
                dependencies=[structure.name],
                verification_notes="Finite fields have prime characteristic"
            )
            assertions.append(assertion)
        
        return assertions


# ============ 5) Structure Templates ===========================================================

class StructureTemplates:
    """Pre-defined templates for common algebraic structures."""
    
    @staticmethod
    def integer_group(modulus: int = None) -> AlgebraicStructure:
        """Create integer group (additive) or cyclic group."""
        if modulus:
            return AlgebraicStructure(
                name=f"Z_{modulus}",
                structure_type=StructureType.ABELIAN_GROUP,
                properties={
                    "closed": True, "associative": True, "identity": True,
                    "inverses": True, "commutative": True, "finite": True,
                    "cyclic": True, "order": modulus
                },
                operations=["+"]
            )
        else:
            return AlgebraicStructure(
                name="Z",
                structure_type=StructureType.ABELIAN_GROUP,
                properties={
                    "closed": True, "associative": True, "identity": True,
                    "inverses": True, "commutative": True, "infinite": True,
                    "cyclic": True
                },
                operations=["+"]
            )
    
    @staticmethod
    def symmetric_group(n: int) -> AlgebraicStructure:
        """Create symmetric group S_n."""
        return AlgebraicStructure(
            name=f"S_{n}",
            structure_type=StructureType.GROUP,
            properties={
                "closed": True, "associative": True, "identity": True,
                "inverses": True, "finite": True, "non_abelian": n >= 3,
                "order": math.factorial(n)
            },
            operations=["∘"]  # composition
        )
    
    @staticmethod
    def matrix_group(n: int, field: str = "R") -> AlgebraicStructure:
        """Create general linear group GL_n(field)."""
        return AlgebraicStructure(
            name=f"GL_{n}({field})",
            structure_type=StructureType.GROUP,
            properties={
                "closed": True, "associative": True, "identity": True,
                "inverses": True, "non_abelian": n >= 2, "infinite": True
            },
            operations=["*"]  # matrix multiplication
        )
    
    @staticmethod
    def polynomial_ring(variable: str = "x", field: str = "R") -> AlgebraicStructure:
        """Create polynomial ring over a field."""
        return AlgebraicStructure(
            name=f"{field}[{variable}]",
            structure_type=StructureType.RING,
            properties={
                "closed_add": True, "associative_add": True, "identity_add": True,
                "inverses_add": True, "commutative_add": True, "closed_mult": True,
                "associative_mult": True, "identity_mult": True, "commutative_mult": True,
                "distributive": True, "integral_domain": True, "infinite": True
            },
            operations=["+", "*"]
        )


# ============ 6) Repositories =================================================================

class StructureRepository:
    """Repository for AlgebraicStructure objects."""
    
    def __init__(self) -> None:
        self._items: List[AlgebraicStructure] = []
    
    def add(self, structure: AlgebraicStructure) -> None:
        logging.debug("Adding structure: %s", structure.name)
        self._items.append(structure)
    
    def get(self, name: str) -> Optional[AlgebraicStructure]:
        for item in self._items:
            if item.name == name:
                return item
        return None
    
    def all(self) -> List[AlgebraicStructure]:
        return list(self._items)
    
    def by_type(self, structure_type: StructureType) -> List[AlgebraicStructure]:
        return [s for s in self._items if s.structure_type == structure_type]
    
    def clear(self) -> None:
        self._items.clear()


class AssertionRepository:
    """Repository for PropertyAssertion objects."""
    
    def __init__(self) -> None:
        self._items: List[PropertyAssertion] = []
    
    def add(self, assertion: PropertyAssertion) -> None:
        self._items.append(assertion)
    
    def all(self) -> List[PropertyAssertion]:
        return list(self._items)
    
    def by_status(self, status: VerificationStatus) -> List[PropertyAssertion]:
        return [a for a in self._items if a.status == status]
    
    def clear(self) -> None:
        self._items.clear()


# ============ 7) Analysis Engine ==============================================================

class EventBus:
    """Simple observer bus for visualization and logging hooks."""
    
    def __init__(self) -> None:
        self._subs: Dict[str, List[Callable[..., None]]] = {}
    
    def on(self, event: str, fn: Callable[..., None]) -> None:
        self._subs.setdefault(event, []).append(fn)
    
    def emit(self, event: str, *args: Any, **kwargs: Any) -> None:
        for fn in self._subs.get(event, []):
            try:
                fn(*args, **kwargs)
            except Exception:
                logging.exception("Event handler error: %s", event)


class AlgebraicStructureToolkit:
    """Main engine for analyzing algebraic structures."""
    
    def __init__(self, cfg: Dict[str, Any]) -> None:
        self.cfg = cfg
        self.structure_repo = StructureRepository()
        self.assertion_repo = AssertionRepository()
        self.verifier = PropertyVerifier()
        self.bus = EventBus()
        
        # Register default observers
        self.bus.on("structure.added", lambda s: logging.debug("Added structure: %s", s.name))
        self.bus.on("assertion.generated", lambda a: logging.debug("Generated assertion: %s", a.statement))
    
    def add_structure(self, structure: AlgebraicStructure) -> None:
        """Add a structure and immediately verify its properties."""
        self.structure_repo.add(structure)
        self.bus.emit("structure.added", structure)
        
        # Verify properties
        assertions = self.verifier.verify_structure(structure)
        for assertion in assertions:
            self.assertion_repo.add(assertion)
            self.bus.emit("assertion.generated", assertion)
    
    def analyze_relationships(self) -> List[PropertyAssertion]:
        """Analyze relationships between different structures."""
        assertions = []
        structures = self.structure_repo.all()
        
        for i, struct1 in enumerate(structures):
            for struct2 in structures[i+1:]:
                # Check for potential homomorphisms based on structure types
                if (struct1.structure_type == struct2.structure_type and
                    self._compatible_operations(struct1, struct2)):
                    
                    assertion = PropertyAssertion(
                        statement=f"Potential homomorphism between {struct1.name} and {struct2.name}",
                        structure_type=struct1.structure_type,
                        status=VerificationStatus.UNVERIFIED,
                        dependencies=[struct1.name, struct2.name],
                        verification_notes="Same structure type and compatible operations"
                    )
                    assertions.append(assertion)
                    self.assertion_repo.add(assertion)
        
        return assertions
    
    def _compatible_operations(self, struct1: AlgebraicStructure, struct2: AlgebraicStructure) -> bool:
        """Check if two structures have compatible operations."""
        return (len(struct1.operations) == len(struct2.operations) and
                all(op1 == op2 for op1, op2 in zip(struct1.operations, struct2.operations)))
    
    def generate_structure_report(self) -> Dict[str, Any]:
        """Generate a comprehensive report of all structures and assertions."""
        return {
            "structures": [as_dict_structure(s) for s in self.structure_repo.all()],
            "assertions": [as_dict_assertion(a) for a in self.assertion_repo.all()],
            "summary": {
                "total_structures": len(self.structure_repo.all()),
                "verified_assertions": len(self.assertion_repo.by_status(VerificationStatus.VERIFIED)),
                "inconsistent_assertions": len(self.assertion_repo.by_status(VerificationStatus.INCONSISTENT)),
            }
        }


# ============ 8) Visualization ================================================================

def visualize_structure_hierarchy(structures: List[AlgebraicStructure], 
                                assertions: List[PropertyAssertion],
                                out_html: Path) -> None:
    """Create an interactive visualization of structures and their relationships."""
    if nx is None or go is None:
        logging.warning("networkx/plotly not available; skipping interactive visualization")
        return
    
    G = nx.Graph()
    
    # Add structure nodes
    for s in structures:
        G.add_node(s.name, kind="structure", type=s.structure_type.name, 
                  properties=len(s.properties))
    
    # Add assertion nodes and edges
    for a in assertions:
        if a.dependencies:
            assertion_id = f"assertion_{hash(a.statement) % 10000}"
            G.add_node(assertion_id, kind="assertion", status=a.status.name, 
                      statement=a.statement[:50] + "..." if len(a.statement) > 50 else a.statement)
            
            for dep in a.dependencies:
                if dep in G:
                    G.add_edge(dep, assertion_id)
    
    if not G.nodes:
        logging.warning("No nodes to visualize")
        return
        
    # Layout
    pos = nx.spring_layout(G, dim=3, seed=42)
    
    # Build traces
    edge_x, edge_y, edge_z = [], [], []
    for (a, b) in G.edges():
        x0, y0, z0 = pos[a]
        x1, y1, z1 = pos[b]
        edge_x += [x0, x1, None]
        edge_y += [y0, y1, None]
        edge_z += [z0, z1, None]
    
    edge_trace = go.Scatter3d(x=edge_x, y=edge_y, z=edge_z, mode="lines", 
                             line=dict(width=2, color='gray'), hoverinfo="none")
    
    # Node traces
    node_x = [pos[n][0] for n in G.nodes()]
    node_y = [pos[n][1] for n in G.nodes()]
    node_z = [pos[n][2] for n in G.nodes()]
    
    node_colors = []
    node_texts = []
    for n in G.nodes():
        data = G.nodes[n]
        if data.get("kind") == "structure":
            node_colors.append('blue')
            node_texts.append(f"Structure: {n}<br>Type: {data.get('type')}<br>Properties: {data.get('properties')}")
        else:
            status_color = {'VERIFIED': 'green', 'INCONSISTENT': 'red', 'UNVERIFIED': 'orange'}.get(data.get('status', 'UNVERIFIED'), 'gray')
            node_colors.append(status_color)
            node_texts.append(f"Assertion: {data.get('statement')}<br>Status: {data.get('status')}")
    
    node_trace = go.Scatter3d(x=node_x, y=node_y, z=node_z, mode="markers",
                             marker=dict(size=8, color=node_colors, line=dict(width=2)),
                             text=node_texts, hoverinfo="text")
    
    fig = go.Figure(data=[edge_trace, node_trace])
    fig.update_layout(title="Algebraic Structure Relationships", 
                     margin=dict(l=0, r=0, t=30, b=0),
                     scene=dict(xaxis=dict(visible=False),
                               yaxis=dict(visible=False),
                               zaxis=dict(visible=False)))
    
    fig.write_html(str(out_html))
    logging.info("Interactive graph written to %s", out_html)


# ============ 9) Exporters ====================================================================

def as_dict_structure(s: AlgebraicStructure) -> Dict[str, Any]:
    return {
        "name": s.name,
        "structure_type": s.structure_type.name,
        "properties": s.properties,
        "operations": s.operations,
    }


def as_dict_assertion(a: PropertyAssertion) -> Dict[str, Any]:
    return {
        "statement": a.statement,
        "structure_type": a.structure_type.name,
        "status": a.status.name,
        "verification_notes": a.verification_notes,
        "dependencies": a.dependencies,
    }


def export_report(report: Dict[str, Any], base_path: Path, formats: Sequence[str]) -> None:
    """Export analysis report in multiple formats."""
    base_path.parent.mkdir(parents=True, exist_ok=True)
    
    if "json" in formats:
        with (base_path.with_suffix(".json")).open("w", encoding="utf-8") as f:
            json.dump(report, f, indent=2)
        logging.info("Wrote %s", base_path.with_suffix(".json"))
    
    if "md" in formats:
        md = ["# Algebraic Structure Toolkit Report", ""]
        
        # Structures section
        md.append("## Structures")
        for s in report.get("structures", []):
            md.append(f"### {s['name']}")
            md.append(f"- **Type:** {s['structure_type']}")
            md.append(f"- **Operations:** {', '.join(s['operations'])}")
            md.append("- **Properties:**")
            for prop, value in s['properties'].items():
                md.append(f"  - {prop}: {value}")
            md.append("")
        
        # Assertions section
        md.append("## Property Assertions")
        for a in report.get("assertions", []):
            status_icon = {"VERIFIED": "✅", "INCONSISTENT": "❌", "UNVERIFIED": "⏳"}.get(a['status'], "❓")
            md.append(f"{status_icon} **{a['statement']}**")
            if a['verification_notes']:
                md.append(f"  *Note: {a['verification_notes']}*")
            md.append("")
        
        # Summary
        summary = report.get("summary", {})
        md.append("## Summary")
        md.append(f"- Total structures: {summary.get('total_structures', 0)}")
        md.append(f"- Verified assertions: {summary.get('verified_assertions', 0)}")
        md.append(f"- Inconsistent assertions: {summary.get('inconsistent_assertions', 0)}")
        
        (base_path.with_suffix(".md")).write_text("\n".join(md), encoding="utf-8")
        logging.info("Wrote %s", base_path.with_suffix(".md"))
    
    if "ipynb" in formats:
        nb = {
            "cells": [
                {
                    "cell_type": "markdown", 
                    "metadata": {}, 
                    "source": ["# Algebraic Structure Toolkit Report\n"]
                },
                {
                    "cell_type": "code",
                    "metadata": {},
                    "source": ["# Analysis report generated by Algebraic Structure Toolkit\n", 
                              f"import json\n",
                              f"report = {json.dumps(report, indent=2)}\n",
                              f"print(f\"Total structures: {{len(report['structures'])}}\")\n",
                              f"print(f\"Verified assertions: {{len([a for a in report['assertions'] if a['status'] == 'VERIFIED'])}}\")"]
                }
            ],
            "metadata": {"kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"}},
            "nbformat": 4,
            "nbformat_minor": 5,
        }
        (base_path.with_suffix(".ipynb")).write_text(json.dumps(nb, indent=2), encoding="utf-8")
        logging.info("Wrote %s", base_path.with_suffix(".ipynb"))


# ============ 10) CLI =========================================================================

def build_arg_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="Algebraic Structure Toolkit - Analyze and visualize algebraic structures",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    p.add_argument("command", choices=["analyze", "visualize", "templates", "report", "verify"],
                   help="Command to execute")
    p.add_argument("--config", "-c", type=str, default=None, help="Path to YAML/JSON config")
    p.add_argument("--seed", type=int, default=1337, help="Reproducible seed")
    p.add_argument("--log", type=str, default="INFO", help="Log level")
    p.add_argument("--json-logs", action="store_true", help="Emit JSON logs")
    p.add_argument("--formats", nargs="+", default=["json", "md"], help="Export formats")
    p.add_argument("--out", type=str, default=str(DEFAULT_RESULTS_DIR / f"ast_{int(time())}"), 
                   help="Export base path (no extension)")
    return p


def load_example_structures() -> List[AlgebraicStructure]:
    """Load a set of example algebraic structures for demonstration."""
    return [
        StructureTemplates.integer_group(),           # Z (infinite cyclic group)
        StructureTemplates.integer_group(5),          # Z_5 (finite cyclic group)
        StructureTemplates.symmetric_group(3),        # S_3 (symmetric group)
        StructureTemplates.matrix_group(2),           # GL_2(R) (general linear group)
        StructureTemplates.polynomial_ring(),         # R[x] (polynomial ring)
        
        # Additional examples
        AlgebraicStructure(
            name="Q",
            structure_type=StructureType.FIELD,
            properties={
                "closed_add": True, "associative_add": True, "identity_add": True,
                "inverses_add": True, "commutative_add": True, "closed_mult": True,
                "associative_mult": True, "identity_mult": True, "inverses_mult": True,
                "commutative_mult": True, "distributive": True, "characteristic_zero": True
            },
            operations=["+", "*"]
        ),
    ]


def run_cli(argv: Optional[Sequence[str]] = None) -> int:
    args = build_arg_parser().parse_args(argv)
    configure_logging(level=args.log, style=LogStyle.JSON if args.json_logs else LogStyle.TEXT)
    set_reproducible_seeds(args.seed)
    
    cfg = load_config(args.config)
    toolkit = AlgebraicStructureToolkit(cfg)
    
    if args.command == "analyze":
        # Load example structures and analyze them
        structures = load_example_structures()
        for structure in structures:
            toolkit.add_structure(structure)
        
        # Analyze relationships
        toolkit.analyze_relationships()
        
        # Generate and export report
        report = toolkit.generate_structure_report()
        export_report(report, Path(args.out), formats=args.formats)
        
        logging.info("Analysis complete. Generated %d assertions.", 
                    len(toolkit.assertion_repo.all()))
        return 0
    
    elif args.command == "visualize":
        # Load structures and generate visualization
        structures = load_example_structures()
        for structure in structures:
            toolkit.add_structure(structure)
        toolkit.analyze_relationships()
        
        visualize_structure_hierarchy(
            toolkit.structure_repo.all(),
            toolkit.assertion_repo.all(),
            Path(str(args.out) + "_graph.html")
        )
        return 0
    
    elif args.command == "templates":
        # List available structure templates
        templates = [
            ("integer_group", "Additive group of integers (Z) or integers mod n (Z_n)"),
            ("symmetric_group", "Symmetric group S_n (permutations)"),
            ("matrix_group", "General linear group GL_n(field)"),
            ("polynomial_ring", "Polynomial ring over a field"),
        ]
        
        print("Available structure templates:")
        for name, description in templates:
            print(f"  {name}: {description}")
        return 0
    
    elif args.command == "report":
        # Generate a comprehensive report
        structures = load_example_structures()
        for structure in structures:
            toolkit.add_structure(structure)
        toolkit.analyze_relationships()
        
        report = toolkit.generate_structure_report()
        export_report(report, Path(args.out), formats=args.formats)
        return 0
    
    elif args.command == "verify":
        # Focus on property verification
        structures = load_example_structures()
        verified_count = 0
        inconsistent_count = 0
        
        for structure in structures:
            toolkit.add_structure(structure)
            assertions = toolkit.verifier.verify_structure(structure)
            
            for assertion in assertions:
                if assertion.status == VerificationStatus.VERIFIED:
                    verified_count += 1
                    print(f"✅ {assertion.statement}")
                elif assertion.status == VerificationStatus.INCONSISTENT:
                    inconsistent_count += 1
                    print(f"❌ {assertion.statement}")
        
        print(f"\nVerification summary:")
        print(f"  Verified: {verified_count}")
        print(f"  Inconsistent: {inconsistent_count}")
        return 0
    
    return 0


# ============ 11) Tests ======================================================================

def run_tests() -> int:
    """Run basic functionality tests."""
    import doctest
    
    # Simple doctests
    def test_property_verification() -> bool:
        """Test basic property verification.
        
        >>> toolkit = AlgebraicStructureToolkit({})
        >>> group = StructureTemplates.integer_group(5)
        >>> assertions = toolkit.verifier.verify_structure(group)
        >>> any(a.status == VerificationStatus.VERIFIED for a in assertions)
        True
        """
        return True
    
    def test_structure_consistency() -> bool:
        """Test that structure properties match their type.
        
        >>> # A group should have identity and inverses
        >>> group = AlgebraicStructure("test_group", StructureType.GROUP)
        >>> "identity" in group.properties and "inverses" in group.properties
        True
        """
        return True
    
    # Run doctests
    failures, _ = doctest.testmod(verbose=False)
    
    if failures == 0:
        print("All tests passed!")
        return 0
    else:
        print(f"{failures} test(s) failed")
        return 1


# ============ Entry Point =====================================================================
if __name__ == "__main__":
    sys.exit(run_cli())