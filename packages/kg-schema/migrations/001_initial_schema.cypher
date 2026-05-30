// Initial knowledge graph schema — UniShield §6
// Migration: 001_initial_schema.cypher

CREATE CONSTRAINT client_id IF NOT EXISTS FOR (c:Client) REQUIRE c.id IS UNIQUE;
CREATE CONSTRAINT user_id IF NOT EXISTS FOR (u:User) REQUIRE u.id IS UNIQUE;
CREATE CONSTRAINT device_id IF NOT EXISTS FOR (d:Device) REQUIRE d.id IS UNIQUE;
CREATE CONSTRAINT service_id IF NOT EXISTS FOR (s:Service) REQUIRE s.id IS UNIQUE;
CREATE CONSTRAINT finding_id IF NOT EXISTS FOR (f:Finding) REQUIRE f.id IS UNIQUE;
CREATE CONSTRAINT incident_id IF NOT EXISTS FOR (i:Incident) REQUIRE i.id IS UNIQUE;
CREATE CONSTRAINT cve_id IF NOT EXISTS FOR (c:CVE) REQUIRE c.id IS UNIQUE;

CREATE INDEX client_tenant IF NOT EXISTS FOR (c:Client) ON (c.id);
CREATE INDEX finding_client IF NOT EXISTS FOR (f:Finding) ON (f.clientId);
CREATE INDEX device_client IF NOT EXISTS FOR (d:Device) ON (d.clientId);
