import os
from neo4j import GraphDatabase, Driver, Session
from contextlib import contextmanager

class Neo4jConnection:
    _instance = None
    _driver: Driver = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(Neo4jConnection, cls).__new__(cls)
            cls._instance._init_driver()
        return cls._instance

    def _init_driver(self):
        uri = os.getenv("NEO4J_URI", "bolt://localhost:7687")
        user = os.getenv("NEO4J_USER", "neo4j")
        password = os.getenv("NEO4J_PASSWORD", "pramanagst")
        
        try:
            self._driver = GraphDatabase.driver(uri, auth=(user, password))
            self._driver.verify_connectivity()
            print("Successfully connected to Neo4j")
        except Exception as e:
            print(f"Failed to connect to Neo4j: {e}")
            self._driver = None

    def close(self):
        if self._driver is not None:
            self._driver.close()
            self._driver = None

    @contextmanager
    def get_session(self) -> Session:
        if self._driver is None:
            self._init_driver()
            
        if self._driver is None:
            raise ConnectionError("Neo4j driver is not initialized.")
            
        session = self._driver.session()
        try:
            yield session
        finally:
            session.close()

# Singleton instance access
db = Neo4jConnection()

def get_db_session():
    """Helper function to get a session quickly"""
    with db.get_session() as session:
        yield session
