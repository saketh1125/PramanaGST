// Placeholder Neo4j schema
// Create constraints and indexes here
CREATE CONSTRAINT ON (t:Taxpayer) ASSERT t.gstin IS UNIQUE;
