"""
Prime Attractor Graph System
==================================

Theory Overview:
For primes p, we define a trajectory T(p) = {p, T(p), T²(p), ...} where T is a generalized
Collatz rule T(x) = (k*x + b)/d when divisible. The system studies:
1. Attractor primes (fixed points or cycle minima)
2. Basin structures (connected components)
3. Convergence statistics
4. Parity sequence properties
5. Graph-theoretic invariants

Example Applications:
- Classifying primes by convergence behavior
- Comparing rule systems through graph metrics
- Discovering novel attractor cycles
- Analyzing entropy in prime trajectories
"""

import networkx as nx
import matplotlib.pyplot as plt
import plotly.graph_objects as go
import numpy as np
import sympy
from collections import defaultdict, deque
from typing import (Dict, List, Tuple, Optional, Callable, Set, Union, Any)
import math
from hashlib import sha256
import time
import json
import csv
from dataclasses import dataclass
from enum import Enum, auto
import logging

# Configure research-grade logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('prime_attractor_research.log'),
        logging.StreamHandler()
    ]
)

class ConvergenceStatus(Enum):
    """Classification of trajectory convergence outcomes."""
    ATTRACTOR_PRIME = auto()
    CYCLE = auto()
    DIVERGENT = auto()
    UNKNOWN = auto()

@dataclass
class TrajectoryAnalysis:
    """Comprehensive analysis of a single prime trajectory."""
    prime: int
    sequence: List[int]
    attractor: Union[int, Tuple[int, ...]]  # Single value or cycle tuple
    status: ConvergenceStatus
    parity_hash: str
    length: int
    steps_to_convergence: int
    entropy: float
    max_value: int
    is_cycle: bool

@dataclass
class EdgeAnalytics:
    """Quantitative analysis of graph edges."""
    source: int
    target: int
    weight: int
    entropy: float
    mean_step_length: float
    primes_contributing: Set[int]
    trajectory_samples: List[List[int]]
    convergence_certainty: float  # Percentage of trajectories that continue to same attractor

class PrimeAttractorGraph:
    """
    Research-grade implementation of the Prime Attractor Graph system.

    Attributes:
        graph (nx.DiGraph): The directed graph of prime transitions
        attractor_map (Dict[int, Union[int, Tuple[int, ...]]]): Prime to attractor mapping
        trajectory_cache (Dict[int, TrajectoryAnalysis]): Full trajectory analysis cache
        basin_sizes (Dict[Union[int, Tuple[int, ...]], int]): Attractor basin sizes
        edge_analytics (Dict[Tuple[int, int], EdgeAnalytics]): Enhanced edge metadata
        rule (Callable): The current transformation rule
        diagnostics (Dict[str, Any]): System-wide performance metrics
    """

    def __init__(self,
                 rule: Optional[Callable] = None,
                 k: int = 3,
                 b: int = 1,
                 d: int = 2,
                 verbose: bool = False):
        """
        Initialize the Prime Attractor Graph with enhanced diagnostics.

        Args:
            rule: Custom transformation function T(x) (overrides k,b,d if provided)
            k: Coefficient in (k*x + b)
            b: Additive constant in (k*x + b)
            d: Divisor in (k*x + b)/d
            verbose: Enable detailed operation logging
        """
        self.graph = nx.DiGraph()
        self.attractor_map = {}
        self.trajectory_cache = {}
        self.basin_sizes = defaultdict(int)
        self.edge_analytics = {}
        self.diagnostics = {
            'compute_time': 0,
            'graph_build_time': 0,
            'cache_hits': 0,
            'primes_processed': 0
        }
        self.verbose = verbose

        if rule is not None:
            self.rule = rule
            self.rule_signature = "custom"
        else:
            self.rule = self._create_standard_rule(k, b, d)
            self.rule_signature = f"T(x) = ({k}x + {b})/{d}"

        self._validate_initial_parameters(k, b, d)

        if self.verbose:
            logging.info(f"Initialized PrimeAttractorGraph with rule: {self.rule_signature}")

    def _create_standard_rule(self, k: int, b: int, d: int) -> Callable:
        """Factory for standard Collatz-type rules with enhanced validation."""
        def rule(x: int) -> Optional[int]:
            numerator = k * x + b
            if numerator % d == 0:
                return numerator // d
            return None
        return rule

    def _validate_initial_parameters(self, k: int, b: int, d: int) -> None:
        """Assert mathematical validity of rule parameters."""
        if d == 0:
            raise ValueError("Divisor d cannot be zero")
        if k < 1:
            raise ValueError("Coefficient k must be positive")
        if not isinstance(k, int) or not isinstance(b, int) or not isinstance(d, int):
            raise TypeError("Parameters k, b, d must be integers")

    def is_prime(self, n: int) -> bool:
        """Optimized prime check with memoization and input validation."""
        if not isinstance(n, int) or n < 0:
            return False
        return sympy.isprime(n) if n > 1 else False

    def next_in_sequence(self, x: int) -> Optional[int]:
        """
        Apply the transformation rule once with enhanced diagnostics.

        Returns:
            Next value in sequence or None if rule doesn't apply
        """
        try:
            result = self.rule(x)
            if result is not None and result < 0:
                logging.warning(f"Negative value generated from {x}: {result}")
            return result
        except Exception as e:
            logging.error(f"Rule application failed for x={x}: {str(e)}")
            return None

    def compute_trajectory(self,
                         start: int,
                         max_steps: int = 1000,
                         return_analysis: bool = False) -> Union[List[int], TrajectoryAnalysis]:
        """
        Compute the trajectory with comprehensive cycle detection and analysis.

        Args:
            start: Starting number (prime recommended)
            max_steps: Maximum iterations before termination
            return_analysis: Return full TrajectoryAnalysis object

        Returns:
            Trajectory as list or full analysis object
        """
        if start in self.trajectory_cache:
            self.diagnostics['cache_hits'] += 1
            cached = self.trajectory_cache[start]
            return cached if return_analysis else cached.sequence

        start_time = time.time()
        trajectory = []
        x = start
        seen = {}  # Track both values and their positions for cycle detection

        for step in range(max_steps):
            if x in seen:
                cycle_start = seen[x]
                cycle = trajectory[cycle_start:]
                analysis = self._analyze_cycle(trajectory, cycle, start)
                self.trajectory_cache[start] = analysis
                self.diagnostics['compute_time'] += time.time() - start_time
                return analysis if return_analysis else trajectory

            trajectory.append(x)
            seen[x] = step

            next_x = self.next_in_sequence(x)
            if next_x is None:
                analysis = self._analyze_termination(trajectory, start)
                self.trajectory_cache[start] = analysis
                self.diagnostics['compute_time'] += time.time() - start_time
                return analysis if return_analysis else trajectory

            x = next_x

        # Max steps reached
        analysis = self._analyze_divergence(trajectory, start)
        self.trajectory_cache[start] = analysis
        self.diagnostics['compute_time'] += time.time() - start_time
        return analysis if return_analysis else trajectory

    def _analyze_cycle(self, trajectory: List[int], cycle: List[int], start: int) -> TrajectoryAnalysis:
        """Comprehensive analysis of cyclic trajectory."""
        cycle_tuple = tuple(sorted(set(cycle)))
        is_prime_cycle = all(self.is_prime(p) for p in cycle_tuple)

        return TrajectoryAnalysis(
            prime=start,
            sequence=trajectory,
            attractor=cycle_tuple[0] if len(cycle_tuple) == 1 else cycle_tuple,
            status=ConvergenceStatus.ATTRACTOR_PRIME if is_prime_cycle and len(cycle_tuple) == 1
                  else ConvergenceStatus.CYCLE,
            parity_hash=self._compute_parity_hash(trajectory),
            length=len(trajectory),
            steps_to_convergence=trajectory.index(cycle[0]),
            entropy=self._calculate_entropy(trajectory),
            max_value=max(trajectory),
            is_cycle=True
        )

    def _analyze_termination(self, trajectory: List[int], start: int) -> TrajectoryAnalysis:
        """Analyze terminated trajectory."""
        last = trajectory[-1]
        is_attractor = self.is_prime(last)

        return TrajectoryAnalysis(
            prime=start,
            sequence=trajectory,
            attractor=last,
            status=ConvergenceStatus.ATTRACTOR_PRIME if is_attractor
                  else ConvergenceStatus.UNKNOWN,
            parity_hash=self._compute_parity_hash(trajectory),
            length=len(trajectory),
            steps_to_convergence=len(trajectory) - 1,
            entropy=self._calculate_entropy(trajectory),
            max_value=max(trajectory),
            is_cycle=False
        )

    def _analyze_divergence(self, trajectory: List[int], start: int) -> TrajectoryAnalysis:
        """Analyze divergent trajectory."""
        return TrajectoryAnalysis(
            prime=start,
            sequence=trajectory,
            attractor=None,
            status=ConvergenceStatus.DIVERGENT,
            parity_hash=self._compute_parity_hash(trajectory),
            length=len(trajectory),
            steps_to_convergence=-1,
            entropy=self._calculate_entropy(trajectory),
            max_value=max(trajectory),
            is_cycle=False
        )

    def _compute_parity_hash(self, sequence: List[int]) -> str:
        """Create a unique signature of the parity sequence."""
        parity = [x % 2 for x in sequence]
        return sha256(bytes(parity)).hexdigest()[:16]

    def _calculate_entropy(self, sequence: List[int]) -> float:
        """Calculate Shannon entropy of the sequence."""
        if len(sequence) <= 1:
            return 0.0

        values, counts = np.unique(sequence, return_counts=True)
        probs = counts / counts.sum()
        return -np.sum(probs * np.log2(probs))

    def find_attractor(self, prime: int) -> Union[int, Tuple[int, ...]]:
        """
        Find the attractor for a prime with enhanced cycle detection.

        Returns:
            Prime attractor or cycle tuple, with convergence status
        """
        analysis = self.compute_trajectory(prime, return_analysis=True)

        if analysis.status == ConvergenceStatus.CYCLE:
            return analysis.attractor
        return analysis.attractor if analysis.attractor is not None else -1

    def build_graph(self, primes: List[int], track_non_primes: bool = False):
        """
        Construct the attractor graph with comprehensive edge analytics.

        Args:
            primes: List of primes to include
            track_non_primes: Whether to track transitions through non-prime numbers
        """
        if not primes:
            raise ValueError("Empty prime list provided")

        start_time = time.time()
        self.diagnostics['primes_processed'] += len(primes)

        for p in primes:
            if not self.is_prime(p):
                if self.verbose:
                    logging.warning(f"Skipping non-prime input: {p}")
                continue

            analysis = self.compute_trajectory(p, return_analysis=True)
            attractor = analysis.attractor

            # Node attributes
            self.graph.add_node(p,
                              is_attractor=(p == attractor),
                              **analysis.__dict__)

            # Basin statistics
            if self.is_prime(attractor) or track_non_primes:
                self.basin_sizes[attractor] += 1

            # Process transitions between primes in the trajectory
            prime_steps = [x for x in analysis.sequence if self.is_prime(x)]

            for i in range(len(prime_steps) - 1):
                source = prime_steps[i]
                target = prime_steps[i + 1]

                if source == target:
                    continue

                # Update graph structure
                if self.graph.has_edge(source, target):
                    self.graph[source][target]['weight'] += 1
                else:
                    self.graph.add_edge(source, target, weight=1)
                    self.edge_analytics[(source, target)] = EdgeAnalytics(
                        source=source,
                        target=target,
                        weight=1,
                        entropy=0,
                        mean_step_length=0,
                        primes_contributing=set(),
                        trajectory_samples=[],
                        convergence_certainty=0
                    )

                # Update edge analytics
                edge_key = (source, target)
                edge_data = self.edge_analytics[edge_key]
                edge_data.weight += 1
                edge_data.primes_contributing.add(p)

                # Extract the trajectory segment between these primes
                segment = analysis.sequence[analysis.sequence.index(source):analysis.sequence.index(target)+1]
                edge_data.trajectory_samples.append(segment)

                # Update dynamic metrics
                edge_data.entropy = self._calculate_entropy(
                    [x for seg in edge_data.trajectory_samples for x in seg]
                )
                edge_data.mean_step_length = np.mean([
                    len(seg) for seg in edge_data.trajectory_samples
                ])

                # Convergence certainty: % of paths that continue to same attractor
                if attractor is not None:
                    same_attractor = sum(
                        1 for prime in edge_data.primes_contributing
                        if self.attractor_map.get(prime) == attractor
                    )
                    edge_data.convergence_certainty = same_attractor / len(edge_data.primes_contributing)

            # Record final attractor mapping
            self.attractor_map[p] = attractor

        self.diagnostics['graph_build_time'] += time.time() - start_time
        if self.verbose:
            logging.info(f"Graph construction completed for {len(primes)} primes")

    def get_attractor_clusters(self) -> Dict[Union[int, Tuple[int, ...]], List[int]]:
        """Return primes grouped by their attractors with statistical summary."""
        clusters = defaultdict(list)
        for p, attractor in self.attractor_map.items():
            clusters[attractor].append(p)

        return {
            attractor: {
                'primes': members,
                'count': len(members),
                'average_path_length': np.mean([
                    len(self.compute_trajectory(p)) for p in members
                ])
            }
            for attractor, members in clusters.items()
        }

    def visualize_with_networkx(self,
                              layout: str = 'spring',
                              figsize: Tuple[int, int] = (12, 12),
                              annotate_threshold: int = 10):
        """
        Enhanced static visualization with research-grade annotations.

        Args:
            layout: Graph layout algorithm ('spring', 'kamada_kawai', 'spectral')
            figsize: Figure dimensions
            annotate_threshold: Minimum basin size for attractor labels
        """
        plt.figure(figsize=figsize)

        # Compute layout
        pos = self._get_layout(layout)

        # Prepare visual attributes
        node_sizes, node_colors = self._get_node_attributes()
        edge_widths, edge_alphas = self._get_edge_attributes()

        # Draw nodes with attractors highlighted
        nx.draw_networkx_nodes(
            self.graph, pos,
            node_size=node_sizes,
            node_color=node_colors,
            alpha=0.9,
            cmap=plt.cm.viridis
        )

        # Draw edges with weights
        nx.draw_networkx_edges(
            self.graph, pos,
            width=edge_widths,
            edge_color='gray',
            alpha=edge_alphas,
            arrows=True,
            arrowstyle='->',
            arrowsize=10
        )

        # Label significant attractors
        labels = {
            node: f"{node}\nΔ={self.basin_sizes[node]}"
            for node in self.graph.nodes()
            if self.graph.nodes[node].get('is_attractor', False)
            and self.basin_sizes.get(node, 0) >= annotate_threshold
        }
        nx.draw_networkx_labels(
            self.graph, pos, labels,
            font_size=8,
            font_weight='bold',
            bbox=dict(facecolor='white', alpha=0.8)

        # Add legend and title
        plt.title(
            f"Prime Attractor Graph\nRule: {self.rule_signature}\n"
            f"{len(self.graph.nodes())} nodes, {len(self.graph.edges())} edges",
            fontsize=12
        )
        plt.axis('off')

        # Add colorbar for basin sizes
        sm = plt.cm.ScalarMappable(
            cmap=plt.cm.viridis,
            norm=plt.Normalize(vmin=min(node_sizes), vmax=max(node_sizes))
        sm.set_array([])
        cbar = plt.colorbar(sm, ax=plt.gca(), shrink=0.5)
        cbar.set_label('Log(Basin Size)')

        plt.tight_layout()
        plt.show()

    def visualize_with_plotly(self,
                            layout: str = 'spring',
                            show_edges: bool = True,
                            show_attractor_labels: bool = True):
        """
        Interactive visualization with Plotly with enhanced research features.

        Args:
            layout: Graph layout algorithm
            show_edges: Whether to display edges
            show_attractor_labels: Whether to label attractors
        """
        pos = self._get_layout(layout)

        # Create edge traces if enabled
        edge_traces = []
        if show_edges:
            for edge in self.graph.edges():
                x0, y0 = pos[edge[0]]
                x1, y1 = pos[edge[1]]

                edge_trace = go.Scatter(
                    x=[x0, x1, None],
                    y=[y0, y1, None],
                    line=dict(
                        width=1 + 2 * math.log(1 + self.graph[edge[0]][edge[1]]['weight']),
                        color='rgba(150, 150, 150, 0.5)'),
                    hoverinfo='none',
                    mode='lines')
                edge_traces.append(edge_trace)

        # Create node trace
        node_x = []
        node_y = []
        node_text = []
        node_sizes = []
        node_colors = []
        node_hover = []

        for node in self.graph.nodes():
            x, y = pos[node]
            node_x.append(x)
            node_y.append(y)

            # Visual properties
            basin_size = math.log(1 + self.basin_sizes.get(node, 1))
            node_sizes.append(10 + 5 * basin_size)

            if self.graph.nodes[node].get('is_attractor', False):
                node_colors.append(basin_size)
                cluster_size = len([p for p, a in self.attractor_map.items() if a == node])
                hover_text = (
                    f"<b>Attractor Prime: {node}</b><br>"
                    f"Basin Size: {cluster_size}<br>"
                    f"Rule: {self.rule_signature}"
                )
            else:
                node_colors.append(0)  # Non-attractors get baseline color
                attractor = self.attractor_map.get(node, "Unknown")
                hover_text = (
                    f"Prime: {node}<br>"
                    f"Attractor: {attractor}<br>"
                    f"Path Length: {len(self.compute_trajectory(node))}"
                )

            node_hover.append(hover_text)
            node_text.append(str(node) if (show_attractor_labels and
                                         self.graph.nodes[node].get('is_attractor', False))
                           else '')

        node_trace = go.Scatter(
            x=node_x,
            y=node_y,
            mode='markers+text',
            text=node_text,
            textposition="top center",
            hovertext=node_hover,
            hoverinfo='text',
            marker=dict(
                showscale=True,
                colorscale='Viridis',
                color=node_colors,
                size=node_sizes,
                colorbar=dict(
                    thickness=15,
                    title='Basin Size (log)',
                    xanchor='left',
                    titleside='right'
                ),
                line_width=2))

        fig = go.Figure(data=edge_traces + [node_trace],
                       layout=go.Layout(
                            showlegend=False,
                            hovermode='closest',
                            margin=dict(b=20, l=5, r=5, t=40),
                            title=f"Prime Attractor Graph<br>Rule: {self.rule_signature}",
                            xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
                            yaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
                            width=1000,
                            height=800
                        ))
        fig.show()

    def _get_layout(self, layout: str) -> Dict[int, Tuple[float, float]]:
        """Compute graph layout with appropriate parameters."""
        if layout == 'spring':
            return nx.spring_layout(self.graph, k=0.15, iterations=100)
        elif layout == 'kamada_kawai':
            return nx.kamada_kawai_layout(self.graph)
        elif layout == 'spectral':
            return nx.spectral_layout(self.graph)
        else:
            return nx.spring_layout(self.graph)

    def _get_node_attributes(self) -> Tuple[List[int], List[float]]:
        """Prepare node sizes and colors based on basin sizes."""
        sizes = []
        colors = []
        max_basin = max(self.basin_sizes.values()) if self.basin_sizes else 1

        for node in self.graph.nodes():
            basin = self.basin_sizes.get(node, 1)
            sizes.append(100 + 900 * (math.log(1 + basin) / math.log(1 + max_basin)))
            colors.append(math.log(1 + basin))

        return sizes, colors

    def _get_edge_attributes(self) -> Tuple[List[float], List[float]]:
        """Prepare edge widths and transparencies based on weights."""
        widths = []
        alphas = []
        weights = [self.graph[u][v]['weight'] for u, v in self.graph.edges()]
        max_weight = max(weights) if weights else 1

        for u, v in self.graph.edges():
            weight = self.graph[u][v]['weight']
            widths.append(0.5 + 3 * weight / max_weight)
            alphas.append(0.1 + 0.9 * weight / max_weight)

        return widths, alphas

    def analyze_network_properties(self) -> Dict[str, Any]:
        """
        Compute comprehensive network metrics with statistical significance.

        Returns:
            Dictionary containing:
            - Basic graph metrics
            - Attractor statistics
            - Path analysis
            - Connectivity measures
        """
        if not self.graph.nodes():
            return {}

        undirected = self.graph.to_undirected()

        return {
            'basic_metrics': {
                'node_count': self.graph.number_of_nodes(),
                'edge_count': self.graph.number_of_edges(),
                'density': nx.density(self.graph),
                'directed_acyclic': nx.is_directed_acyclic_graph(self.graph)
            },
            'attractor_analysis': {
                'total_attractors': sum(1 for node in self.graph.nodes()
                                      if self.graph.nodes[node].get('is_attractor', False)),
                'basin_size_distribution': {
                    'max': max(self.basin_sizes.values()) if self.basin_sizes else 0,
                    'min': min(self.basin_sizes.values()) if self.basin_sizes else 0,
                    'mean': np.mean(list(self.basin_sizes.values())) if self.basin_sizes else 0,
                    'median': np.median(list(self.basin_sizes.values())) if self.basin_sizes else 0
                },
                'attractor_types': {
                    'fixed_points': sum(1 for a in self.basin_sizes
                                      if isinstance(a, int) and self.is_prime(a))),
                    'cycles': sum(1 for a in self.basin_sizes
                                if isinstance(a, tuple))
                }
            },
            'path_analysis': {
                'average_path_length': nx.average_shortest_path_length(self.graph)
                                      if nx.is_strongly_connected(self.graph) else float('inf'),
                'diameter': nx.diameter(undirected)
                           if nx.is_connected(undirected) else float('inf')
            },
            'centrality': {
                'degree_centrality': nx.degree_centrality(self.graph),
                'betweenness_centrality': nx.betweenness_centrality(self.graph),
                'closeness_centrality': nx.closeness_centrality(self.graph)
            },
            'connectivity': {
                'strongly_connected_components': nx.number_strongly_connected_components(self.graph),
                'weakly_connected_components': nx.number_weakly_connected_components(self.graph)
            }
        }

    def export_graph(self,
                    filename: str,
                    format: str = 'gexf',
                    include_analytics: bool = True) -> None:
        """
        Export the graph to a file with comprehensive metadata.

        Supported formats:
        - 'gexf' (Gephi)
        - 'graphml' (GraphML)
        - 'json' (Node-link)
        - 'csv' (Edge list)

        Args:
            filename: Output file path
            format: File format
            include_analytics: Whether to include analytical metadata
        """
        if not self.graph.nodes():
            raise ValueError("Graph is empty - nothing to export")

        graph_to_export = self.graph.copy()

        if include_analytics:
            # Add node analytics
            for node in graph_to_export.nodes():
                graph_to_export.nodes[node].update({
                    'basin_size': self.basin_sizes.get(node, 0),
                    'is_attractor': self.graph.nodes[node].get('is_attractor', False)
                })

                if node in self.trajectory_cache:
                    analysis = self.trajectory_cache[node]
                    graph_to_export.nodes[node].update({
                        'trajectory_length': analysis.length,
                        'convergence_status': analysis.status.name,
                        'max_value': analysis.max_value
                    })

            # Add edge analytics
            for u, v in graph_to_export.edges():
                if (u, v) in self.edge_analytics:
                    analytics = self.edge_analytics[(u, v)]
                    graph_to_export.edges[u, v].update({
                        'entropy': analytics.entropy,
                        'mean_step_length': analytics.mean_step_length,
                        'convergence_certainty': analytics.convergence_certainty
                    })

        # Handle different export formats
        if format.lower() == 'gexf':
            nx.write_gexf(graph_to_export, filename)
        elif format.lower() == 'graphml':
            nx.write_graphml(graph_to_export, filename)
        elif format.lower() == 'json':
            data = nx.node_link_data(graph_to_export)
            with open(filename, 'w') as f:
                json.dump(data, f)
        elif format.lower() == 'csv':
            with open(filename, 'w', newline='') as f:
                writer = csv.writer(f)
                writer.writerow(['source', 'target', 'weight'])
                for u, v, d in graph_to_export.edges(data=True):
                    writer.writerow([u, v, d.get('weight', 1)])
        else:
            raise ValueError(f"Unsupported format: {format}")

        if self.verbose:
            logging.info(f"Graph exported to {filename} ({format.upper()})")

    def compare_to(self, other: 'PrimeAttractorGraph') -> Dict[str, Any]:
        """
        Compare this graph to another PrimeAttractorGraph instance.

        Returns:
            Dictionary of comparative metrics:
            - node_overlap: Jaccard similarity of node sets
            - edge_overlap: Jaccard similarity of edge sets
            - attractor_comparison: Common attractors
            - rule_comparison: Rule signatures
        """
        if not isinstance(other, PrimeAttractorGraph):
            raise TypeError("Can only compare with another PrimeAttractorGraph instance")

        nodes_self = set(self.graph.nodes())
        nodes_other = set(other.graph.nodes())
        edges_self = set(self.graph.edges())
        edges_other = set(other.graph.edges())

        attractors_self = {
            a for a in self.basin_sizes
            if isinstance(a, int) and self.graph.nodes[a].get('is_attractor', False)
        }
        attractors_other = {
            a for a in other.basin_sizes
            if isinstance(a, int) and other.graph.nodes[a].get('is_attractor', False)
        }

        return {
            'node_overlap': {
                'jaccard': len(nodes_self & nodes_other) / len(nodes_self | nodes_other),
                'count_self': len(nodes_self),
                'count_other': len(nodes_other),
                'common': len(nodes_self & nodes_other)
            },
            'edge_overlap': {
                'jaccard': len(edges_self & edges_other) / len(edges_self | edges_other),
                'count_self': len(edges_self),
                'count_other': len(edges_other),
                'common': len(edges_self & edges_other)
            },
            'attractor_comparison': {
                'common_attractors': attractors_self & attractors_other,
                'unique_to_self': attractors_self - attractors_other,
                'unique_to_other': attractors_other - attractors_self
            },
            'rule_comparison': {
                'self_rule': self.rule_signature,
                'other_rule': other.rule_signature
            }
        }

    def get_diagnostics(self) -> Dict[str, Any]:
        """Return comprehensive performance and operational metrics."""
        return {
            **self.diagnostics,
            'cache_stats': {
                'size': len(self.trajectory_cache),
                'hit_rate': self.diagnostics['cache_hits'] / max(1, self.diagnostics['primes_processed'])
            },
            'memory_usage': {
                'graph_nodes': len(self.graph.nodes()),
                'graph_edges': len(self.graph.edges()),
                'attractor_map': len(self.attractor_map)
            }
        }


# Example Research Usage
if __name__ == "__main__":
    # Initialize with enhanced diagnostics
    print("Initializing research-grade Prime Attractor Graph...")
    pag = PrimeAttractorGraph(k=3, b=1, d=2, verbose=True)

    # Load primes (example range)
    primes = list(sympy.primerange(2, 500))
    print(f"\nAnalyzing {len(primes)} primes from 2 to {max(primes)}...")

    # Build graph with timing
    start_time = time.time()
    pag.build_graph(primes)
    print(f"Graph construction completed in {time.time() - start_time:.2f} seconds")

    # Display key findings
    print("\nKey Network Properties:")
    props = pag.analyze_network_properties()
    print(f"- {props['basic_metrics']['node_count']} nodes, {props['basic_metrics']['edge_count']} edges")
    print(f"- {props['attractor_analysis']['total_attractors']} attractor primes found")
    print(f"- Largest basin size: {props['attractor_analysis']['basin_size_distribution']['max']}")

    # Visualize
    print("\nGenerating visualizations...")
    pag.visualize_with_networkx()
    pag.visualize_with_plotly()

    # Export for further analysis
    print("\nExporting graph data...")
    pag.export_graph("prime_attractor_graph.gexf", format='gexf')
    pag.export_graph("prime_attractor_edges.csv", format='csv')

    # Show diagnostics
    print("\nSystem Diagnostics:")
    for k, v in pag.get_diagnostics().items():
        print(f"{k}: {v}")
