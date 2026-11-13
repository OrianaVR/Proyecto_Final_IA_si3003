
import json

from src.config import PROJECT_ROOT
from src.data import load_graph


def main():
    graph = load_graph()

    print(
        f"Grafo local: {len(graph.nodes)} nodos "
        f"y {len(graph.edges)} aristas"
    )

    pairs_path = PROJECT_ROOT / "data" / "test_pairs.json"
    pairs = json.loads(pairs_path.read_text(encoding="utf-8"))

    origin = pairs[0]["origin"]

    print("Par válido:", pairs[0])
    print("Nodo de origen:", graph.nodes[origin])
    print("Vecinos salientes:")

    for edge in graph.adjacency[origin][:5]:
        print(
            edge.destination,
            round(edge.distance_m, 2),
            "metros",
            edge.name,
        )


if __name__ == "__main__":
    main()