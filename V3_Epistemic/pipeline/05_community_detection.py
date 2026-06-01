"""
05_community_detection.py

Builds issue/profile communities from the canonical feature matrix and a
separate relationship community from processed graph edges. UMAP coordinates
are kept for centroids, but relationship communities are not inferred from 2D
geometry alone.
"""

from __future__ import annotations

import json
import math
from collections import Counter, defaultdict

import networkx as nx
import numpy as np
import pandas as pd
from sklearn.neighbors import NearestNeighbors

from config import PROCESSED_DIR


OUT = PROCESSED_DIR
RANDOM_STATE = 42


try:
    import community as community_louvain  # type: ignore

    LOUVAIN_AVAILABLE = True
except Exception:
    community_louvain = None
    LOUVAIN_AVAILABLE = False


def detect_partition(graph: nx.Graph) -> dict:
    if graph.number_of_nodes() == 0:
        return {}
    if graph.number_of_edges() == 0:
        return {node: idx for idx, node in enumerate(graph.nodes())}
    if LOUVAIN_AVAILABLE:
        return community_louvain.best_partition(graph, weight="weight", random_state=RANDOM_STATE)
    communities = nx.algorithms.community.greedy_modularity_communities(graph, weight="weight")
    partition = {}
    for cid, members in enumerate(communities):
        for node in members:
            partition[node] = cid
    return partition


def build_feature_knn(feature_matrix: pd.DataFrame, ids: np.ndarray) -> nx.Graph:
    feature_cols = [col for col in feature_matrix.columns if col not in {"entity_id", "name"}]
    X = feature_matrix[feature_cols].fillna(0.0).astype(float).to_numpy()
    k = min(15, max(1, len(ids) - 1))
    graph = nx.Graph()
    graph.add_nodes_from(ids)
    if len(ids) <= 1:
        return graph
    nbrs = NearestNeighbors(n_neighbors=k + 1, metric="cosine").fit(X)
    distances, indices = nbrs.kneighbors(X)
    finite_distances = distances[:, 1:].ravel()
    finite_distances = finite_distances[np.isfinite(finite_distances)]
    sigma = float(np.median(finite_distances[finite_distances > 0])) if np.any(finite_distances > 0) else 1.0
    sigma = max(sigma, 1e-6)
    for row_idx, entity_id in enumerate(ids):
        for neighbor_idx, dist in zip(indices[row_idx][1:], distances[row_idx][1:]):
            neighbor_id = ids[neighbor_idx]
            if entity_id == neighbor_id:
                continue
            dist = float(dist if np.isfinite(dist) else 1.0)
            weight = math.exp(-(dist**2) / (2 * sigma**2))
            graph.add_edge(entity_id, neighbor_id, weight=weight)
    return graph


def build_relationship_graph(edges: pd.DataFrame, valid_ids: set[str]) -> nx.Graph:
    graph = nx.Graph()
    graph.add_nodes_from(valid_ids)
    if edges.empty:
        return graph
    for _, edge in edges.iterrows():
        source = str(edge.get("source_id", ""))
        target = str(edge.get("target_id", ""))
        if source not in valid_ids or target not in valid_ids or source == target:
            continue
        weight = float(edge.get("weight", 1) or 1)
        if graph.has_edge(source, target):
            graph[source][target]["weight"] += weight
        else:
            graph.add_edge(source, target, weight=weight)
    return graph


def build_directed_relationship_graph(edges: pd.DataFrame, valid_ids: set[str]) -> nx.DiGraph:
    graph = nx.DiGraph()
    graph.add_nodes_from(valid_ids)
    if edges.empty:
        return graph
    for _, edge in edges.iterrows():
        source = str(edge.get("source_id", ""))
        target = str(edge.get("target_id", ""))
        if source not in valid_ids or target not in valid_ids or source == target:
            continue
        weight = float(edge.get("weight", 1) or 1)
        if graph.has_edge(source, target):
            graph[source][target]["weight"] += weight
        else:
            graph.add_edge(source, target, weight=weight)
    return graph


def top_counter(values, n=5) -> list[dict]:
    counts = Counter(v for v in values if pd.notna(v) and str(v).strip())
    return [{"value": value, "count": int(count)} for value, count in counts.most_common(n)]


def relationship_analytics(
    edges: pd.DataFrame,
    relationship_graph: nx.Graph,
    relationship_partition: dict,
    entity_lookup: dict[str, dict],
    valid_ids: set[str],
) -> dict:
    directed_graph = build_directed_relationship_graph(edges, valid_ids)
    if directed_graph.number_of_edges():
        pagerank = nx.pagerank(directed_graph, weight="weight", max_iter=200, tol=1e-8)
    else:
        pagerank = {node: 0.0 for node in valid_ids}

    if relationship_graph.number_of_edges() and relationship_graph.number_of_nodes() > 2:
        k = min(128, relationship_graph.number_of_nodes())
        betweenness = nx.betweenness_centrality(
            relationship_graph,
            k=k,
            normalized=True,
            weight=None,
            seed=RANDOM_STATE,
        )
    else:
        betweenness = {node: 0.0 for node in valid_ids}

    in_strength: defaultdict[str, float] = defaultdict(float)
    out_strength: defaultdict[str, float] = defaultdict(float)
    edge_type_summary: defaultdict[str, dict[str, float]] = defaultdict(lambda: {"count": 0, "weight": 0.0})
    adjacency: defaultdict[str, list[dict]] = defaultdict(list)

    for _, edge in edges.iterrows():
        source = str(edge.get("source_id", ""))
        target = str(edge.get("target_id", ""))
        if source not in valid_ids or target not in valid_ids or source == target:
            continue
        weight = float(edge.get("weight", 1) or 1)
        edge_type = str(edge.get("edge_type", "unknown"))
        out_strength[source] += weight
        in_strength[target] += weight
        edge_type_summary[edge_type]["count"] += 1
        edge_type_summary[edge_type]["weight"] += weight
        stub = {
            "source_id": source,
            "target_id": target,
            "edge_type": edge_type,
            "weight": round(weight, 6),
        }
        adjacency[source].append(stub)
        adjacency[target].append(stub)

    participation = {}
    for node in relationship_graph.nodes():
        community_weights: defaultdict[int, float] = defaultdict(float)
        total = 0.0
        for neighbor, attrs in relationship_graph[node].items():
            weight = float(attrs.get("weight", 1) or 1)
            community_weights[int(relationship_partition.get(neighbor, -1))] += weight
            total += weight
        participation[node] = 0.0 if total <= 0 else 1.0 - sum((weight / total) ** 2 for weight in community_weights.values())

    entity_metrics = {}
    for node in valid_ids:
        total_strength = in_strength[node] + out_strength[node]
        brokerage = float(betweenness.get(node, 0.0)) * math.log1p(total_strength) * (1.0 + participation.get(node, 0.0))
        entity_metrics[node] = {
            "pagerank": round(float(pagerank.get(node, 0.0)), 10),
            "weighted_in_strength": round(float(in_strength[node]), 6),
            "weighted_out_strength": round(float(out_strength[node]), 6),
            "weighted_total_strength": round(float(total_strength), 6),
            "betweenness": round(float(betweenness.get(node, 0.0)), 10),
            "brokerage_score": round(brokerage, 10),
            "participation_coefficient": round(float(participation.get(node, 0.0)), 10),
        }

    top_brokers = []
    for entity_id, metrics in sorted(entity_metrics.items(), key=lambda item: item[1]["brokerage_score"], reverse=True)[:50]:
        entity = entity_lookup.get(entity_id, {})
        top_brokers.append({
            "entity_id": entity_id,
            "name": entity.get("name", entity_id),
            "entity_type": entity.get("entity_type", "unknown"),
            **metrics,
        })

    adjacency_topk = {
        entity_id: sorted(rows, key=lambda row: -float(row.get("weight", 0)))[:25]
        for entity_id, rows in adjacency.items()
    }

    return {
        "entity_metrics": entity_metrics,
        "top_brokers": top_brokers,
        "edge_type_summaries": {
            edge_type: {"count": int(values["count"]), "weight": round(float(values["weight"]), 6)}
            for edge_type, values in edge_type_summary.items()
        },
        "adjacency_topk": adjacency_topk,
    }


def main() -> None:
    coords = pd.read_csv(OUT / "umap_coords.csv")
    entities = pd.read_csv(OUT / "entities.csv")
    industries = pd.read_csv(OUT / "entity_industries.csv")
    feature_matrix = pd.read_csv(OUT / "issue_matrix_aggregate.csv")
    edges = pd.read_csv(OUT / "edges.csv") if (OUT / "edges.csv").exists() else pd.DataFrame()

    merged = coords.merge(
        entities[["entity_id", "entity_type", "total_spending", "filings_total", "top_issue", "issue_codes"]],
        on="entity_id",
        how="left",
    ).merge(industries[["entity_id", "industry_label"]], on="entity_id", how="left")
    ids = merged["entity_id"].astype(str).to_numpy()
    valid_ids = set(ids)

    issue_graph = build_feature_knn(feature_matrix, ids)
    issue_partition = detect_partition(issue_graph)
    relationship_graph = build_relationship_graph(edges, valid_ids)
    relationship_partition = detect_partition(relationship_graph)
    entity_lookup = (
        merged.set_index("entity_id")[["name", "entity_type"]]
        .fillna("")
        .to_dict(orient="index")
    )
    analytics = relationship_analytics(edges, relationship_graph, relationship_partition, entity_lookup, valid_ids)

    merged["issue_community_id"] = [issue_partition.get(entity_id, -1) for entity_id in ids]
    merged["relationship_community_id"] = [relationship_partition.get(entity_id, -1) for entity_id in ids]
    # Preserve `cluster_id` for existing frontend compatibility.
    merged["cluster_id"] = merged["issue_community_id"]

    cluster_profiles: dict[str, dict] = {}
    cluster_labels: dict[int, str] = {}
    for cid in sorted(c for c in merged["cluster_id"].unique() if c >= 0):
        members = merged[merged["cluster_id"] == cid]
        industry_counts = members["industry_label"].fillna("Unknown").value_counts()
        dominant = str(industry_counts.index[0]) if len(industry_counts) else "Unknown"
        second = str(industry_counts.index[1]) if len(industry_counts) > 1 else ""
        label = dominant
        if second and industry_counts.iloc[1] > 0.25 * industry_counts.iloc[0]:
            label = f"{dominant} / {second}"
        cluster_labels[int(cid)] = label
        top_entities = (
            members.sort_values("total_spending", ascending=False)[["name", "entity_type", "total_spending"]]
            .head(8)
            .to_dict(orient="records")
        )
        issue_values = []
        for raw in members["issue_codes"].fillna(""):
            issue_values.extend(str(raw).split("|"))
        cluster_profiles[str(int(cid))] = {
            "cluster_id": int(cid),
            "label": label,
            "member_count": int(len(members)),
            "total_spending": float(members[members["entity_type"] != "gov_agency"]["total_spending"].fillna(0).sum()),
            "total_lobbying_exposure": float(members[members["entity_type"] == "gov_agency"]["total_spending"].fillna(0).sum()),
            "centroid_x": float(members["x"].mean()),
            "centroid_y": float(members["y"].mean()),
            "entity_types": {k: int(v) for k, v in members["entity_type"].value_counts().items()},
            "top_issues": top_counter(issue_values),
            "top_industries": top_counter(members["industry_label"]),
            "top_entities": top_entities,
            "community_method": "feature_knn_louvain" if LOUVAIN_AVAILABLE else "feature_knn_greedy_modularity",
            "confidence": "derived_from_canonical_feature_matrix",
        }

    result = merged[
        [
            "entity_id",
            "name",
            "cluster_id",
            "issue_community_id",
            "relationship_community_id",
        ]
    ].copy()
    result["cluster_label"] = result["cluster_id"].map(cluster_labels).fillna("Unclustered")
    result.to_csv(OUT / "clusters.csv", index=False)

    graph_metrics = {
        "issue_graph": {
            "nodes": issue_graph.number_of_nodes(),
            "edges": issue_graph.number_of_edges(),
            "method": "feature_knn_louvain" if LOUVAIN_AVAILABLE else "feature_knn_greedy_modularity",
        },
        "relationship_graph": {
            "nodes": relationship_graph.number_of_nodes(),
            "edges": relationship_graph.number_of_edges(),
            "method": "relationship_louvain" if LOUVAIN_AVAILABLE else "relationship_greedy_modularity",
            "communities": len(set(relationship_partition.values())),
        },
        "entity_metrics": analytics["entity_metrics"],
        "top_brokers": analytics["top_brokers"],
        "edge_type_summaries": analytics["edge_type_summaries"],
    }
    with open(OUT / "cluster_profiles.json", "w", encoding="utf-8") as f:
        json.dump(cluster_profiles, f, indent=2)
    with open(OUT / "graph_metrics.json", "w", encoding="utf-8") as f:
        json.dump(graph_metrics, f, indent=2)
    with open(OUT / "adjacency_topk.json", "w", encoding="utf-8") as f:
        json.dump(analytics["adjacency_topk"], f, indent=2)

    print(f"Saved: clusters.csv ({len(result)} rows)")
    print(f"Saved: cluster_profiles.json ({len(cluster_profiles)} issue communities)")
    print(f"Saved: graph_metrics.json")


if __name__ == "__main__":
    main()
