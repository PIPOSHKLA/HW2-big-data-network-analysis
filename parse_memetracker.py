#!/usr/bin/env python3
"""
Stream the MemeTracker quotes_2009-04.txt file and build a DOMAIN-LEVEL
weighted hyperlink graph.

Record format (tab-separated):
  P <url>   post/document URL   -> source node
  T <time>  timestamp           (ignored)
  Q <text>  quote               (ignored)
  L <url>   hyperlink target    -> edge source_domain -> target_domain

We aggregate links to the registered-domain (eTLD+1) level and count how many
times domain A links to domain B across the whole month.

Outputs (into the Neo4j /import folder):
  mt_domain_nodes.csv   domain
  mt_domain_edges.csv   src,dst,weight
"""
import sys, time

IN_PATH  = r"C:\Users\GIGABYTE_N\Desktop\Docker\neo4j-import\quotes_2009-04.txt"
NODES_OUT = r"C:\Users\GIGABYTE_N\Desktop\Docker\neo4j-import\mt_domain_nodes.csv"
EDGES_OUT = r"C:\Users\GIGABYTE_N\Desktop\Docker\neo4j-import\mt_domain_edges.csv"

# Common multi-label public suffixes so foo.co.uk -> foo.co.uk (not co.uk),
# while foo.bar.com -> bar.com.
TWO_LEVEL = frozenset("""
co.uk org.uk gov.uk ac.uk me.uk ltd.uk plc.uk net.uk sch.uk nhs.uk police.uk mod.uk
com.au net.au org.au gov.au edu.au id.au asn.au
co.nz org.nz govt.nz net.nz ac.nz geek.nz school.nz
co.jp ne.jp or.jp go.jp ac.jp ad.jp ed.jp gr.jp lg.jp
co.kr or.kr ne.kr re.kr pe.kr go.kr
com.br net.br org.br gov.br edu.br
co.in net.in org.in gen.in firm.in ind.in gov.in ac.in edu.in
co.za org.za net.za gov.za ac.za web.za
com.mx org.mx gob.mx net.mx edu.mx
com.cn net.cn org.cn gov.cn edu.cn ac.cn
com.tw org.tw net.tw gov.tw edu.tw idv.tw
co.il org.il net.il ac.il gov.il muni.il
com.tr net.tr org.tr gov.tr edu.tr web.tr
com.ar net.ar org.ar gov.ar edu.ar
com.sg net.sg org.sg gov.sg edu.sg
com.hk net.hk org.hk gov.hk edu.hk idv.hk
com.my net.my org.my gov.my edu.my
co.id or.id web.id ac.id go.id sch.id
com.ru net.ru org.ru
com.ua net.ua org.ua
com.pl net.pl org.pl gov.pl edu.pl
com.ph net.ph org.ph gov.ph edu.ph
com.vn net.vn org.vn gov.vn edu.vn
""".split())


def domain_of(url):
    """Extract registered domain (eTLD+1) from a URL. Returns '' if unusable."""
    # strip scheme
    i = url.find("://")
    if i != -1:
        url = url[i + 3:]
    # strip path/query/fragment
    for sep in ("/", "?", "#"):
        j = url.find(sep)
        if j != -1:
            url = url[:j]
    # strip userinfo
    at = url.rfind("@")
    if at != -1:
        url = url[at + 1:]
    # strip port
    c = url.find(":")
    if c != -1:
        url = url[:c]
    host = url.strip().lower().strip(".")
    if not host or " " in host:
        return ""
    # drop leading www.
    if host.startswith("www."):
        host = host[4:]
    labels = host.split(".")
    if len(labels) < 2:
        return ""
    # need a non-numeric TLD (skip raw IPs)
    if labels[-1].isdigit():
        return ""
    last2 = ".".join(labels[-2:])
    if last2 in TWO_LEVEL and len(labels) >= 3:
        return ".".join(labels[-3:])
    return last2


def main():
    edges = {}          # (src, dst) -> weight
    domains = set()
    cur = ""
    n_lines = 0
    n_links = 0
    t0 = time.time()

    with open(IN_PATH, "r", encoding="utf-8", errors="replace", buffering=1 << 20) as f:
        for line in f:
            n_lines += 1
            if not line or line[0] == "\n":
                continue
            tag = line[0]
            if tag == "P":
                cur = domain_of(line[2:])
                if cur:
                    domains.add(cur)
            elif tag == "L":
                if cur:
                    dst = domain_of(line[2:])
                    if dst and dst != cur:
                        domains.add(dst)
                        k = (cur, dst)
                        edges[k] = edges.get(k, 0) + 1
                        n_links += 1
            if n_lines % 20_000_000 == 0:
                el = time.time() - t0
                print(f"  {n_lines:,} lines | {len(domains):,} domains | "
                      f"{len(edges):,} edges | {n_links:,} links | {el:,.0f}s",
                      flush=True)

    print(f"DONE reading: {n_lines:,} lines in {time.time()-t0:,.0f}s", flush=True)
    print(f"Unique domains: {len(domains):,} | Unique edges: {len(edges):,} | "
          f"Total links: {n_links:,}", flush=True)

    with open(NODES_OUT, "w", encoding="utf-8", newline="") as f:
        f.write("domain\n")
        for d in domains:
            f.write(d)
            f.write("\n")

    with open(EDGES_OUT, "w", encoding="utf-8", newline="") as f:
        f.write("src,dst,weight\n")
        for (s, d), w in edges.items():
            f.write(f"{s},{d},{w}\n")

    print(f"Wrote {NODES_OUT} and {EDGES_OUT}", flush=True)


if __name__ == "__main__":
    main()
