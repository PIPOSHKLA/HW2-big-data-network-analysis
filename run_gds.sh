#!/usr/bin/env bash
# Runs the full import + 7-algorithm GDS pipeline against the neo4j-gds container.
# All computation is expressed in Cypher (GDS procedures are invoked from Cypher).
set -e
CY() { docker exec -i neo4j-gds cypher-shell -u neo4j -p 123 --format plain "$1"; }

echo "== [1/6] constraint =="
CY "CREATE CONSTRAINT domain_name IF NOT EXISTS FOR (d:Domain) REQUIRE d.name IS UNIQUE;"

echo "== [2/6] load nodes =="
CY "LOAD CSV WITH HEADERS FROM 'file:///mt_domain_nodes.csv' AS row
    CALL (row) { CREATE (:Domain {name: row.domain}) } IN TRANSACTIONS OF 50000 ROWS;"

echo "== [3/6] load edges =="
CY "LOAD CSV WITH HEADERS FROM 'file:///mt_domain_edges.csv' AS row
    CALL (row) {
      MATCH (a:Domain {name: row.src}) MATCH (b:Domain {name: row.dst})
      CREATE (a)-[:LINKS {weight: toInteger(row.weight)}]->(b)
    } IN TRANSACTIONS OF 50000 ROWS;"

echo "== counts =="
CY "MATCH (d:Domain) WITH count(d) AS nodes
    MATCH ()-[r:LINKS]->() RETURN nodes, count(r) AS rels;"

echo "== [4/6] drop old projections (if any) =="
CY "CALL gds.graph.drop('mtDir', false) YIELD graphName RETURN graphName;"
CY "CALL gds.graph.drop('mtUndir', false) YIELD graphName RETURN graphName;"

echo "== project directed (weighted) =="
CY "MATCH (s:Domain)-[r:LINKS]->(t:Domain)
    RETURN gds.graph.project('mtDir', s, t,
      { relationshipProperties: r { .weight } }) AS g;"

echo "== project undirected (weighted) =="
CY "MATCH (s:Domain)-[r:LINKS]->(t:Domain)
    RETURN gds.graph.project('mtUndir', s, t,
      { relationshipProperties: r { .weight },
        relationshipType: 'LINKS' }, { undirectedRelationshipTypes: ['LINKS'] }) AS g;"

echo "== [5/6] centrality algorithms (write back as node properties) =="

echo "-- Degree (weighted, directed out-degree) --"
CY "CALL gds.degree.write('mtDir', {relationshipWeightProperty:'weight', writeProperty:'deg'})
    YIELD centralityDistribution AS d RETURN d.max AS max, d.mean AS mean;"

echo "-- PageRank (weighted) --"
CY "CALL gds.pageRank.write('mtDir', {relationshipWeightProperty:'weight', writeProperty:'pr', maxIterations:50})
    YIELD ranIterations, didConverge RETURN ranIterations, didConverge;"

echo "-- Eigenvector --"
CY "CALL gds.eigenvector.write('mtDir', {writeProperty:'eig', maxIterations:100})
    YIELD ranIterations, didConverge RETURN ranIterations, didConverge;"

echo "-- Betweenness (sampled, directed) --"
CY "CALL gds.betweenness.write('mtDir', {samplingSize:2000, samplingSeed:42, writeProperty:'btw'})
    YIELD centralityDistribution AS d RETURN d.max AS max, d.mean AS mean;"

echo "-- Closeness (Wasserman-Faust for disconnected) --"
CY "CALL gds.closeness.write('mtDir', {useWassermanFaust:true, writeProperty:'clo'})
    YIELD centralityDistribution AS d RETURN d.max AS max, d.mean AS mean;"

echo "-- Louvain (community, undirected weighted) --"
CY "CALL gds.louvain.write('mtUndir', {relationshipWeightProperty:'weight', writeProperty:'louvain'})
    YIELD communityCount, modularity RETURN communityCount, modularity;"

echo "-- Bridges (undirected) : count only (edge-level) --"
CY "CALL gds.bridges.stream('mtUndir') YIELD from, to RETURN count(*) AS bridge_edges;"

echo "== [6/6] DONE =="
