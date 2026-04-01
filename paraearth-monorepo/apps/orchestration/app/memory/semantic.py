class SemanticMemoryStore:
    async def query(self, agent_id: str, query_embedding: list, top_k: int = 10) -> list:
        # HNSW index retrieval stub
        return []

    async def store(self, agent_id: str, content: str, embedding: list):
        # Store knowledge vector
        pass