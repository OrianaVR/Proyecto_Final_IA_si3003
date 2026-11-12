"""Dashboard Streamlit: copiloto de movilidad (Medellín centro).

Ejecutar: streamlit run app.py
"""
import json
import re
from pathlib import Path

import folium
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from streamlit_folium import st_folium

ROOT = Path(__file__).resolve().parent
ALGOS = {"A*": "astar", "Dijkstra": "dijkstra"}
COLORS = {"astar": "#d62728", "dijkstra": "#1f77b4"}
DISCLAIMER = ("Herramienta académica (SI3003, EAFIT). Las rutas son por distancia sobre datos de OpenStreetMap "
              "y no constituyen consejo de movilidad, seguridad, legal ni médico. Verifica siempre la información "
              "oficial del Metro de Medellín.")

st.set_page_config(page_title="Copiloto de movilidad – Medellín", layout="wide")

try:
    from dotenv import load_dotenv
    load_dotenv(ROOT / ".env")
except Exception:  # python-dotenv es opcional
    pass

# Adaptador: algunos proveedores (p. ej. Groq, vía Cloudflare) rechazan con HTTP 403 (código 1010) el
# User-Agent por defecto de urllib. El cliente de src/agent/llm.py no define uno, así que se fija aquí.
import urllib.request

_opener = urllib.request.build_opener()
_opener.addheaders = [("User-Agent", "si3003-copiloto-movilidad/1.0")]
urllib.request.install_opener(_opener)


# ------------------------------------------------------------------ carga (cacheada)

@st.cache_resource(show_spinner="Cargando red vial…")
def get_graph():
    from src.data import load_graph
    return load_graph()


@st.cache_data
def node_labels() -> dict[str, str]:
    graph = get_graph()
    names: dict[str, list[str]] = {}
    for e in graph.edges:
        for nid in (e.origin, e.destination):
            if e.name and e.name not in names.setdefault(nid, []):
                names[nid].append(e.name)
    return {nid: (" × ".join(names[nid][:2]) + f" · {nid}") if nid in names else f"Nodo {nid}"
            for nid in graph.nodes}


@st.cache_data
def test_pairs() -> list[dict]:
    return json.loads((ROOT / "data" / "test_pairs.json").read_text(encoding="utf-8"))


@st.cache_data
def routes_csv() -> pd.DataFrame | None:
    path = ROOT / "results" / "routes.csv"
    return pd.read_csv(path) if path.exists() else None


def load_agent():
    try:
        from src.agent.agent import ask
        return ask
    except Exception:
        return None


# ------------------------------------------------------------------ barra lateral

st.title("Copiloto de movilidad – Medellín centro")
st.caption(DISCLAIMER)

try:
    graph = get_graph()
except Exception as exc:
    st.error("No se pudo cargar la red vial local (data/processed). Revisa el README. "
             f"Detalle: {type(exc).__name__}")
    st.stop()

labels = node_labels()
ids = sorted(graph.nodes, key=lambda n: labels[n])
pairs = test_pairs()

with st.sidebar:
    st.header("Parámetros")
    mode = st.radio("Selección de puntos", ["Par de prueba", "Nodos libres"])
    if mode == "Par de prueba":
        pair = st.selectbox("Par", pairs, format_func=lambda p: p["id"])
        origin, destination = pair["origin"], pair["destination"]
        st.caption(f"Origen: {labels[origin]}")
        st.caption(f"Destino: {labels[destination]}")
    else:
        origin = st.selectbox("Origen", ids, format_func=lambda n: labels[n])
        destination = st.selectbox("Destino", ids, index=min(1, len(ids) - 1), format_func=lambda n: labels[n])
    algo_choice = st.radio("Algoritmo", ["A*", "Dijkstra", "Ambos"], index=2)
    calculate = st.button("Calcular ruta", type="primary")

# ------------------------------------------------------------------ cálculo de ruta

if calculate:
    from src.routing import get_route_metrics, plan_route
    wanted = list(ALGOS.values()) if algo_choice == "Ambos" else [ALGOS[algo_choice]]
    try:
        st.session_state["route"] = {
            "origin": origin, "destination": destination,
            "results": {a: plan_route(origin, destination, a, graph=graph) for a in wanted},
            "metrics": get_route_metrics(origin, destination, graph=graph),
        }
    except Exception as exc:
        st.session_state["route"] = None
        st.error(f"No se pudo calcular la ruta ({type(exc).__name__}). Intenta con otro par.")

state = st.session_state.get("route")
st.subheader("Ruta")
if not state:
    st.info("Elige origen, destino y algoritmo en la barra lateral y pulsa **Calcular ruta**.")
else:
    results = state["results"]
    errors = {a: r for a, r in results.items() if r["status"] != "ok"}
    for a, r in errors.items():
        st.warning(f"{a}: {r['error'] or 'No hay ruta entre esos puntos.'}")
    ok = {a: r for a, r in results.items() if r["status"] == "ok"}

    col_map, col_tab = st.columns([3, 2])
    with col_map:
        o, d = graph.nodes[state["origin"]], graph.nodes[state["destination"]]
        fmap = folium.Map(location=[(o.latitude + d.latitude) / 2, (o.longitude + d.longitude) / 2],
                          zoom_start=16, tiles="OpenStreetMap")
        folium.Marker([o.latitude, o.longitude], tooltip="Origen", icon=folium.Icon(color="green")).add_to(fmap)
        folium.Marker([d.latitude, d.longitude], tooltip="Destino", icon=folium.Icon(color="red")).add_to(fmap)
        for a, r in sorted(ok.items(), key=lambda kv: kv[0] != "dijkstra"):
            pts = [[graph.nodes[n].latitude, graph.nodes[n].longitude] for n in r["path"]]
            name = "A*" if a == "astar" else "Dijkstra"
            folium.PolyLine(pts, color=COLORS[a], weight=6 if a == "dijkstra" else 4, opacity=0.8,
                            tooltip=f"{name}: {r['distance_m']:.0f} m").add_to(fmap)
        st_folium(fmap, height=450, use_container_width=True, returned_objects=[])
    with col_tab:
        if ok:
            st.dataframe(pd.DataFrame([
                {"Algoritmo": "A*" if a == "astar" else "Dijkstra", "Dist. (m)": round(r["distance_m"], 1),
                 "Nodos": r["expanded_nodes"], "ms": round(r["elapsed_ms"], 3)}
                for a, r in ok.items()]), hide_index=True, width='stretch')
        m = state["metrics"]
        if len(ok) == 2 and m["metrics"]["same_optimal_distance"]:
            st.success("Ambos algoritmos hallaron la misma distancia óptima.")

    # Visualización 2: comparación A* vs Dijkstra
    st.subheader("Comparación A* vs Dijkstra")
    m = state["metrics"]
    c1, c2 = st.columns(2)
    if m["astar"]["status"] == "ok" and m["dijkstra"]["status"] == "ok":
        with c1:
            fig = go.Figure([go.Bar(name="Dijkstra", x=["Nodos expandidos"], y=[m["dijkstra"]["expanded_nodes"]],
                                    marker_color=COLORS["dijkstra"]),
                             go.Bar(name="A*", x=["Nodos expandidos"], y=[m["astar"]["expanded_nodes"]],
                                    marker_color=COLORS["astar"])])
            fig.update_layout(title="Este par: nodos expandidos", barmode="group", height=320)
            st.plotly_chart(fig, width='stretch')
        with c2:
            fig = go.Figure([go.Bar(name="Dijkstra", x=["Tiempo (ms)"], y=[m["dijkstra"]["elapsed_ms"]],
                                    marker_color=COLORS["dijkstra"]),
                             go.Bar(name="A*", x=["Tiempo (ms)"], y=[m["astar"]["elapsed_ms"]],
                                    marker_color=COLORS["astar"])])
            fig.update_layout(title="Este par: tiempo de ejecución", barmode="group", height=320)
            st.plotly_chart(fig, width='stretch')
    else:
        st.info("No hay ruta válida con ambos algoritmos para este par; no se puede comparar.")

df = routes_csv()
if df is not None:
    with st.expander("Resumen global: 10 pares de evaluación (results/routes.csv)"):
        ok_df = df[df["status"] == "ok"]
        fig = go.Figure([go.Bar(name="Dijkstra", x=ok_df["pair_id"], y=ok_df["dijkstra_expanded_nodes"],
                                marker_color=COLORS["dijkstra"]),
                         go.Bar(name="A*", x=ok_df["pair_id"], y=ok_df["astar_expanded_nodes"],
                                marker_color=COLORS["astar"])])
        fig.update_layout(barmode="group", height=320, yaxis_title="Nodos expandidos")
        st.plotly_chart(fig, width='stretch')
        st.caption(f"Reducción media de nodos expandidos con A*: "
                   f"{ok_df['astar_expansion_reduction_pct'].mean():.1f} % sobre {len(ok_df)} pares.")

# ------------------------------------------------------------------ chat

st.divider()
st.subheader("Asistente (RAG + herramientas)")
ask = load_agent()
if ask is None:
    st.warning("Agente no disponible: no se pudo importar src.agent. El resto de la aplicación sigue funcionando.")
st.session_state.setdefault("chat", [])


def md(text: str) -> str:
    """Evita que 'A*' se interprete como cursiva de markdown."""
    return re.sub(r"(?<![\w*\\])A\*(?!\*)", lambda m: "A\\*", text)


def render_extras(msg: dict) -> None:
    if msg.get("sources"):
        st.markdown("**Fuentes**")
        for s in msg["sources"]:
            where = f", pág. {s['page']}" if s.get("page") else ""
            st.markdown(f"- [{s['title']}]({s['url']}){where}: _{s['snippet'][:240]}_")
    if msg.get("tool_trace"):
        with st.expander("Traza de herramientas"):
            st.json(msg["tool_trace"])


for msg in st.session_state["chat"]:
    with st.chat_message(msg["role"]):
        st.markdown(md(msg["content"]))
        render_extras(msg)

prompt = st.chat_input("Pregunta sobre rutas o el Metro…", disabled=ask is None)
if prompt and ask:
    st.session_state["chat"].append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)
    history = [{"role": m["role"], "content": m["content"]} for m in st.session_state["chat"][:-1]]
    with st.chat_message("assistant"):
        with st.spinner("Pensando…"):
            try:
                res = ask(prompt, history)
            except Exception as exc:
                res = {"answer": f"El agente falló ({type(exc).__name__}). Intenta de nuevo.", "sources": [],
                       "tool_trace": [], "error": "exception"}
        st.markdown(md(res["answer"]))
        if res.get("error") == "llm_not_configured":
            st.caption("Configura LLM_API_KEY y LLM_MODEL en el archivo .env (ver README).")
        elif res.get("error") and "index" in str(res["error"]).lower():
            st.caption("Construye el índice con: python -m scripts.agent.build_index")
        render_extras(res)
    st.session_state["chat"].append({"role": "assistant", "content": res["answer"],
                                     "sources": res.get("sources", []), "tool_trace": res.get("tool_trace", [])})
