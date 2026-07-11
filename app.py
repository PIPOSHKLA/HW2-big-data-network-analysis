"""
HW2 — Big Data Network Analysis
Centrality & community structure of the April 2009 MemeTracker domain hyperlink graph.
Computed in Neo4j GDS (Cypher); this app visualises the exported results.

Run:  streamlit run app.py
"""
import json
import math
import pandas as pd
import networkx as nx
import plotly.graph_objects as go
import streamlit as st

st.set_page_config(page_title="HW2 · Big Data Network Analysis",
                   page_icon="🕸️", layout="wide")

# ----------------------------------------------------------------------------- data
@st.cache_data
def load():
    with open("viz_data.json", encoding="utf-8") as f:
        vd = json.load(f)
    df = pd.read_csv("core_metrics.csv", skipinitialspace=True)
    df.columns = [c.strip() for c in df.columns]
    df["name"] = df["name"].astype(str).str.strip().str.strip('"')
    return vd, df

VD, DF = load()
S = VD["summary"]

MEASURES = {
    "pr":      ("PageRank",     "Random-surfer importance (weighted, damping 0.85)."),
    "btw":     ("Betweenness",  "Brokerage of information flow (sampled, 2000 pivots)."),
    "clo":     ("Closeness",    "Proximity to all others (Wasserman-Faust, on the deg≥50 core)."),
    "deg":     ("Degree",       "Weighted out-degree = Σ outbound link weight."),
    "eig":     ("Eigenvector",  "Influence weighted by the influence of who links you."),
    "bridges": ("Bridges",      "Number of incident bridge edges (cut edges)."),
}
PALETTE = ['#34d8c6', '#ffb454', '#7c8cff', '#ff7a9c', '#5fd07a', '#ff8f5e',
           '#b892ff', '#4bc3ff', '#e9d16b', '#ff6b6b', '#46d6a8', '#ff9ed2', '#8aa0c8']


def fmt(v):
    if v is None or (isinstance(v, float) and math.isnan(v)):
        return "—"
    a = abs(v)
    if a >= 1e9: return f"{v/1e9:.2f}B"
    if a >= 1e6: return f"{v/1e6:.2f}M"
    if a >= 1e3: return f"{v/1e3:.1f}k"
    if a >= 1:   return f"{v:.0f}" if float(v).is_integer() else f"{v:.2f}"
    return f"{v:.3f}"

# ----------------------------------------------------------------------------- header
st.title("🕸️ Who was central on the web in April 2009?")
st.caption("HW2 · Big Data Network Analysis — MemeTracker `quotes_2009-04` · "
           "domain hyperlink graph scored with 7 algorithms in Neo4j GDS (Cypher)")

c = st.columns(7)
kpis = [("Domains", S["nodes"]), ("Weighted links", S["rels"]), ("Raw hyperlinks", S["links"]),
        ("Core (deg≥50)", S["core"]), ("Communities", S["communities"]),
        ("Modularity", S["modularity"]), ("Bridge edges", S["bridges"])]
for col, (label, val) in zip(c, kpis):
    col.metric(label, f"{val:.2f}" if label == "Modularity" else fmt(val))

st.markdown(
    "A **10.9 GB** MemeTracker dump (167M lines) was collapsed to a **domain-level link graph** — "
    "nodes are registered domains, a weighted edge **A→B** counts every time a post on A linked to B — "
    "then scored entirely in Cypher / GDS. Use the controls in the sidebar to explore each measure."
)

# ----------------------------------------------------------------------------- sidebar
st.sidebar.header("Controls")
measure_key = st.sidebar.selectbox(
    "Centrality measure", list(MEASURES),
    format_func=lambda k: MEASURES[k][0], index=0)
mlabel, mdesc = MEASURES[measure_key]
color_by = st.sidebar.radio("Colour network by", ["Community (Louvain)", f"{mlabel} value"], index=0)
topn = st.sidebar.slider("Top-N in ranking", 5, 40, 15, step=5)
st.sidebar.info(mdesc)
st.sidebar.markdown(
    "---\n**Engine** · Neo4j 2026.05 + GDS 2026.05 (Docker `neo4j-gds`)\n\n"
    "**Graph** · 795,268 domains / 2,213,774 links")

tab_net, tab_rank, tab_comm, tab_data = st.tabs(
    ["🌐 Core network", "📊 Rankings", "🧩 Communities", "🗃️ Data"])

# ----------------------------------------------------------------------------- network
with tab_net:
    st.subheader("Core link network — top domains by PageRank")
    st.caption(f"Node size ∝ **{mlabel}** · colour ∝ {color_by.lower()} · edge width ∝ link volume")

    net = VD["net"]
    G = nx.Graph()
    for n in net["nodes"]:
        G.add_node(n["name"], **n)
    for e in net["edges"]:
        if e["s"] in G and e["t"] in G:
            G.add_edge(e["s"], e["t"], w=e["w"])

    pos = nx.spring_layout(G, k=1.1/math.sqrt(max(len(G), 1)), weight="w",
                           seed=42, iterations=200)

    vals = [G.nodes[n].get(measure_key) or 0 for n in G.nodes]
    vmax = max(vals) or 1
    sizes = [10 + 34 * math.sqrt((v or 0) / vmax) for v in vals]

    if color_by.startswith("Community"):
        node_color = [PALETTE[G.nodes[n]["ci"] % len(PALETTE)] for n in G.nodes]
        colorscale = None
    else:
        node_color = vals
        colorscale = "Teal"

    ws = [d["w"] for *_, d in G.edges(data=True)] or [1]
    wmin, wmax = min(ws), max(ws)
    def lg(w): return (math.log(w) - math.log(wmin)) / (math.log(wmax) - math.log(wmin) + 1e-9)

    edge_traces = []
    for u, v, d in G.edges(data=True):
        x0, y0 = pos[u]; x1, y1 = pos[v]
        edge_traces.append(go.Scatter(
            x=[x0, x1, None], y=[y0, y1, None], mode="lines",
            line=dict(width=0.4 + 3 * lg(d["w"]), color="rgba(130,150,175,0.35)"),
            hoverinfo="skip", showlegend=False))

    xs = [pos[n][0] for n in G.nodes]; ys = [pos[n][1] for n in G.nodes]
    hover = []
    for n in G.nodes:
        nd = G.nodes[n]
        hover.append("<b>%s</b><br>PageRank %s<br>Betweenness %s<br>Degree %s<br>"
                     "Closeness %s<br>Eigenvector %s<br>Bridges %s<br>community #%s" % (
                         n, fmt(nd["pr"]), fmt(nd["btw"]), fmt(nd["deg"]),
                         fmt(nd["clo"]), fmt(nd["eig"]), fmt(nd["bridges"]), nd["comm"]))
    labels = [n if sizes[i] > 20 else "" for i, n in enumerate(G.nodes)]

    node_trace = go.Scatter(
        x=xs, y=ys, mode="markers+text", text=labels, textposition="top center",
        textfont=dict(size=10, color="#c7d0dd"),
        marker=dict(size=sizes, color=node_color, colorscale=colorscale,
                    line=dict(width=1, color="rgba(0,0,0,0.35)"),
                    colorbar=(dict(title=mlabel) if colorscale else None),
                    showscale=bool(colorscale)),
        hovertext=hover, hoverinfo="text", showlegend=False)

    fig = go.Figure(edge_traces + [node_trace])
    fig.update_layout(height=620, margin=dict(l=0, r=0, t=0, b=0),
                      paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                      xaxis=dict(visible=False), yaxis=dict(visible=False))
    st.plotly_chart(fig, use_container_width=True)

# ----------------------------------------------------------------------------- rankings
with tab_rank:
    st.subheader(f"Top {topn} domains by {mlabel}")
    st.caption(mdesc + "  · ranked across all 795,268 nodes (core-scored where noted)")
    sub = DF[["name", measure_key]].dropna().sort_values(measure_key, ascending=False).head(topn)
    sub = sub.iloc[::-1]  # so largest is on top in a horizontal bar
    fig = go.Figure(go.Bar(
        x=sub[measure_key], y=sub["name"], orientation="h",
        marker=dict(color=sub[measure_key], colorscale="Teal"),
        text=[fmt(v) for v in sub[measure_key]], textposition="outside"))
    fig.update_layout(height=28 * topn + 60, margin=dict(l=0, r=20, t=10, b=10),
                      paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                      xaxis_title=mlabel, yaxis=dict(tickfont=dict(size=11)))
    st.plotly_chart(fig, use_container_width=True)

# ----------------------------------------------------------------------------- communities
with tab_comm:
    st.subheader("Louvain communities")
    st.caption(f"{S['communities']:,} communities · modularity {S['modularity']:.2f} · 12 largest shown")
    comms = pd.DataFrame(VD["communities"])
    comms["share %"] = (comms["size"] / S["nodes"] * 100).round(1)
    order = comms.iloc[::-1]
    fig = go.Figure(go.Bar(
        x=order["size"], y=order["lead"], orientation="h",
        marker=dict(color=[PALETTE[(len(comms) - 1 - i) % len(PALETTE)] for i in range(len(order))]),
        text=[f"{fmt(s)} · {p}%" for s, p in zip(order["size"], order["share %"])],
        textposition="outside"))
    fig.update_layout(height=440, margin=dict(l=0, r=30, t=10, b=10),
                      paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                      xaxis_title="domains in community (lead domain labelled)")
    st.plotly_chart(fig, use_container_width=True)
    st.dataframe(comms[["lead", "size", "share %", "id"]], use_container_width=True, hide_index=True)

# ----------------------------------------------------------------------------- data
with tab_data:
    st.subheader("Core domain metrics (degree ≥ 50 · 10,290 domains)")
    show = DF.copy()
    show = show.rename(columns={k: v[0] for k, v in MEASURES.items()} | {"louvain": "community"})
    st.dataframe(show.sort_values("PageRank", ascending=False),
                 use_container_width=True, height=460, hide_index=True)
    st.download_button("⬇️ Download core_metrics.csv",
                       DF.to_csv(index=False).encode("utf-8"),
                       "core_metrics.csv", "text/csv")
    with st.expander("How each value was computed (Cypher / GDS)"):
        st.markdown("""
- **Degree** — `gds.degree.write` (weighted out-degree)
- **PageRank** — `gds.pageRank.write` (weighted, damping 0.85)
- **Eigenvector** — `gds.eigenvector.write` (converged, 46 iters)
- **Betweenness** — `gds.betweenness.write` (`samplingSize: 2000`)
- **Closeness** — `gds.closeness.write` (`useWassermanFaust`, on the deg≥50 core)
- **Bridges** — `gds.bridges.stream` → per-node incident-bridge count
- **Louvain** — `gds.louvain.write` (3,145 communities, modularity 0.61)

Source: Stanford SNAP MemeTracker `quotes_2009-04` · graph 795,268 domains / 2,213,774 weighted links.
""")
