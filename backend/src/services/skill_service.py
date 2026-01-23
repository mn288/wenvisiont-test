"""
Skill Service for Voyager (arXiv:2305.16291) persistent skill library.

Handles embedding generation, skill storage, and semantic retrieval.
"""

from typing import List, Optional
from uuid import UUID

from core.database import pool
from models.skills import Skill


class SkillService:
    """
    Service for managing the Voyager skill library.
    
    Provides:
    - Skill storage with auto-embedding
    - Semantic similarity search
    - Usage tracking
    """

    def __init__(self):
        self._embedding_model = "text-embedding-ada-002"
        self._embedding_dim = 1536

    async def _generate_embedding(self, text: str) -> List[float]:
        """Generate embedding using OpenAI API."""
        import openai

        from core.config import settings

        client = openai.AsyncOpenAI(
            api_key=settings.OPENAI_API_KEY,
            base_url=settings.OPENAI_API_BASE
        )
        
        response = await client.embeddings.create(
            model=self._embedding_model,
            input=text
        )
        return response.data[0].embedding

    async def add_skill(
        self,
        agent_role: str,
        task_description: str,
        solution_code: str
    ) -> Skill:
        """
        Save a new skill to the library.
        
        Args:
            agent_role: Role of the agent (e.g., "coder", "researcher")
            task_description: What task was solved
            solution_code: The solution that worked
            
        Returns:
            The saved Skill object
        """
        # Generate embedding for semantic search
        embedding = await self._generate_embedding(task_description)
        
        skill = Skill(
            agent_role=agent_role,
            task_description=task_description,
            solution_code=solution_code,
            embedding=embedding
        )
        
        async with pool.connection() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    """
                    INSERT INTO skills (id, agent_role, task_description, solution_code, embedding, usage_count, created_at, updated_at)
                    VALUES (%s, %s, %s, %s, %s::vector, %s, NOW(), NOW())
                    RETURNING id
                    """,
                    (
                        str(skill.id),
                        skill.agent_role,
                        skill.task_description,
                        skill.solution_code,
                        embedding,
                        0
                    )
                )
            await conn.commit()
        
        return skill

    async def retrieve_skills(
        self,
        query: str,
        agent_role: Optional[str] = None,
        k: int = 3,
        similarity_threshold: float = 0.7
    ) -> List[Skill]:
        """
        Retrieve similar skills using vector similarity search.
        
        Args:
            query: Task description to match against
            agent_role: Optional filter by agent role
            k: Number of results to return
            similarity_threshold: Minimum cosine similarity (0-1)
            
        Returns:
            List of similar skills, ordered by relevance
        """
        query_embedding = await self._generate_embedding(query)
        
        # Build query with optional role filter
        role_filter = "AND agent_role = %s" if agent_role else ""
        params = [query_embedding, similarity_threshold, k]
        if agent_role:
            params.insert(1, agent_role)
        
        async with pool.connection() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    f"""
                    SELECT id, agent_role, task_description, solution_code, usage_count,
                           1 - (embedding <=> %s::vector) as similarity
                    FROM skills
                    WHERE 1 - (embedding <=> %s::vector) > %s
                    {role_filter}
                    ORDER BY similarity DESC
                    LIMIT %s
                    """,
                    params if not agent_role else [query_embedding, query_embedding, agent_role, similarity_threshold, k]
                )
                rows = await cur.fetchall()
        
        skills = []
        for row in rows:
            skill = Skill(
                id=UUID(row[0]) if isinstance(row[0], str) else row[0],
                agent_role=row[1],
                task_description=row[2],
                solution_code=row[3],
                usage_count=row[4]
            )
            skills.append(skill)
            
            # Increment usage count (async, fire-and-forget)
            await self._increment_usage(skill.id)
        
        return skills

    async def _increment_usage(self, skill_id: UUID):
        """Increment the usage count for a skill."""
        async with pool.connection() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    "UPDATE skills SET usage_count = usage_count + 1, updated_at = NOW() WHERE id = %s",
                    (str(skill_id),)
                )
            await conn.commit()

    async def ensure_table_exists(self):
        """Create the skills table if it doesn't exist."""
        async with pool.connection() as conn:
            async with conn.cursor() as cur:
                # Enable pgvector extension
                await cur.execute("CREATE EXTENSION IF NOT EXISTS vector")
                
                # Create table
                await cur.execute("""
                    CREATE TABLE IF NOT EXISTS skills (
                        id UUID PRIMARY KEY,
                        agent_role VARCHAR(255) NOT NULL,
                        task_description TEXT NOT NULL,
                        solution_code TEXT NOT NULL,
                        embedding vector(1536),
                        usage_count INTEGER DEFAULT 0,
                        created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                        updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
                    )
                """)
                
                # Create index for vector similarity search
                await cur.execute("""
                    CREATE INDEX IF NOT EXISTS skills_embedding_idx 
                    ON skills USING ivfflat (embedding vector_cosine_ops)
                    WITH (lists = 100)
                """)
                
                # Create index for agent_role filtering
                await cur.execute("""
                    CREATE INDEX IF NOT EXISTS skills_agent_role_idx ON skills (agent_role)
                """)
            await conn.commit()


# Singleton instance
skill_service = SkillService()
