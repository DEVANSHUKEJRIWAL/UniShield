// Create relationships between KG nodes
MATCH (c:Client {id: 'meridian-financial'})
MERGE (d:Device {id: 'workstation-42', hostname: 'workstation-42', clientId: 'meridian-financial', criticality: 'medium'})
MERGE (s:Service {id: 'db-prod-01', name: 'db-prod-01', clientId: 'meridian-financial', criticality: 'high', crownJewel: true})
MERGE (d)-[:RUNS]->(s)
MERGE (f:Finding {id: 'finding-001', clientId: 'meridian-financial', severity: 'critical'})
MERGE (f)-[:INVOLVES]->(d);
