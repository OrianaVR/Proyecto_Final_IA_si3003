from collections import Counter, deque
import json
from src.config import PROJECT_ROOT
from src.data import load_graph
from src.application.datasets import reachable_nodes
from src.infrastructure.json_store import write_json


def main():
    graph = load_graph()
    undirected = {key: set() for key in graph.nodes}
    for edge in graph.edges:
        undirected[edge.origin].add(edge.destination)
        undirected[edge.destination].add(edge.origin)
    unseen = set(graph.nodes)
    components = []
    while unseen:
        start = min(unseen)
        unseen.remove(start)
        pending = deque([start]);size = 0
        while pending:
            node = pending.popleft(); size += 1
            for neighbor in undirected[node]:
                if neighbor in unseen:
                    unseen.remove(neighbor);pending.append(neighbor)
        components.append(size)
    pairs = json.loads((PROJECT_ROOT/"data/test_pairs.json").read_text())
    result = {"weak_component_sizes": sorted(components, reverse=True),
              "weak_component_count": len(components),
              "nodes_without_outgoing_edges": sum(not graph.adjacency[key] for key in graph.nodes),
              "reachability_by_test_origin": [{"pair_id": pair["id"], "origin": pair["origin"],
                  "reachable_nodes_including_origin": len(reachable_nodes(graph,pair["origin"]))} for pair in pairs]}
    write_json(PROJECT_ROOT/"results/eda.json", result)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
