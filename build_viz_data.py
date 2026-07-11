#!/usr/bin/env python3
"""Assemble the visualization JSON from the exported Neo4j/GDS results."""
import csv, json

CORE = r"C:\Users\GIGABYTE_N\Desktop\code\core_metrics.csv"
EDGES = r"C:\Users\GIGABYTE_N\Desktop\code\core_top_edges.csv"
OUT  = r"C:\Users\GIGABYTE_N\Desktop\code\viz_data.json"


def num(x):
    x = x.strip().strip('"')
    if x == "" or x.lower() == "null":
        return None
    return float(x)


rows = []
with open(CORE, encoding="utf-8") as f:
    r = csv.reader(f)
    header = [h.strip() for h in next(r)]
    for line in r:
        if not line:
            continue
        d = {header[i]: line[i] for i in range(len(header))}
        rows.append({
            "name": d["name"].strip().strip('"'),
            "deg": num(d["deg"]),
            "pr": num(d["pr"]),
            "eig": num(d["eig"]),
            "btw": num(d["btw"]),
            "clo": num(d["clo"]),
            "bridges": num(d["bridges"]),
            "louvain": int(num(d["louvain"])),
        })

by = {n["name"]: n for n in rows}

MEASURES = [
    ("btw",     "Betweenness",  "sampled (2000 pivots), directed"),
    ("bridges", "Bridges",      "bridge edges incident to the domain"),
    ("clo",     "Closeness",    "Wasserman-Faust, on the degree≥50 core"),
    ("deg",     "Degree",       "weighted out-degree (Σ link weight)"),
    ("eig",     "Eigenvector",  "directed, 46 iters (converged)"),
    ("pr",      "PageRank",     "weighted, damping 0.85"),
]

top = {}
for key, label, sub in MEASURES:
    vals = [n for n in rows if n[key] is not None]
    vals.sort(key=lambda n: n[key], reverse=True)
    top[key] = {
        "label": label, "sub": sub,
        "items": [{"name": n["name"], "v": n[key]} for n in vals[:15]],
        "max": vals[0][key] if vals else 0,
    }

# ---- Louvain communities (from full-graph sizes provided separately) ----
communities = [
    {"id": 32562,  "size": 196057, "lead": "blogspot.com"},
    {"id": 764978, "size": 124668, "lead": "wikipedia.org"},
    {"id": 504611, "size": 79417,  "lead": "topix.net"},
    {"id": 261016, "size": 58393,  "lead": "twitter.com"},
    {"id": 518120, "size": 39914,  "lead": "typepad.com"},
    {"id": 105319, "size": 30524,  "lead": "bigblog.com"},
    {"id": 76398,  "size": 27605,  "lead": "blogmura.com"},
    {"id": 235325, "size": 27474,  "lead": "wikipedia.com"},
    {"id": 252498, "size": 26771,  "lead": "google.de"},
    {"id": 456285, "size": 24732,  "lead": "flickr.com"},
    {"id": 92825,  "size": 22021,  "lead": "igooi.com"},
    {"id": 122579, "size": 20987,  "lead": "myspace.com"},
]
comm_ids = [c["id"] for c in communities]

# ---- Network graph: top 60 by PageRank + filtered strong edges ----
netnodes = sorted(rows, key=lambda n: n["pr"], reverse=True)[:60]
netset = {n["name"] for n in netnodes}

raw_edges = []
with open(EDGES, encoding="utf-8") as f:
    r = csv.reader(f)
    next(r)
    for line in r:
        if len(line) < 3:
            continue
        s = line[0].strip().strip('"'); d = line[1].strip().strip('"')
        w = num(line[2])
        if s in netset and d in netset and s != d:
            raw_edges.append((s, d, w))
# keep the strongest ~120 edges for legibility
raw_edges.sort(key=lambda e: e[2], reverse=True)
net_edges = raw_edges[:120]
# only keep nodes that have at least one kept edge, plus always the top 30
kept = set()
for s, d, w in net_edges:
    kept.add(s); kept.add(d)
top30 = {n["name"] for n in netnodes[:30]}
kept |= top30
netnodes = [n for n in netnodes if n["name"] in kept]

# assign a stable palette index per community among the net nodes
present_comms = []
for n in netnodes:
    if n["louvain"] not in present_comms:
        present_comms.append(n["louvain"])
cidx = {c: i for i, c in enumerate(present_comms)}

net = {
    "nodes": [{
        "name": n["name"], "pr": n["pr"], "btw": n["btw"],
        "deg": n["deg"], "clo": n["clo"], "eig": n["eig"],
        "bridges": n["bridges"], "comm": n["louvain"], "ci": cidx[n["louvain"]],
    } for n in netnodes],
    "edges": [{"s": s, "t": d, "w": w} for s, d, w in net_edges
              if s in kept and d in kept],
    "ncomms": len(present_comms),
}

data = {
    "summary": {
        "nodes": 795268, "rels": 2213774, "links": 23550613,
        "core": 10290, "communities": 3145, "modularity": 0.6107,
        "bridges": 524219,
    },
    "measures_order": [m[0] for m in MEASURES],
    "top": top,
    "communities": communities,
    "net": net,
}

with open(OUT, "w", encoding="utf-8") as f:
    json.dump(data, f, ensure_ascii=False)
print("wrote", OUT)
print("net nodes:", len(net["nodes"]), "net edges:", len(net["edges"]),
      "comms in net:", net["ncomms"])
