from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import declarative_base, Mapped, mapped_column
from sqlalchemy import String, Integer, Float, DateTime, Enum as SAEnum, JSON, Column
from pgvector.sqlalchemy import Vector
from datetime import datetime, timezone
import enum

from core.config import settings

Base = declarative_base()

class CognitiveStateEnum(str, enum.Enum):
    ACTIVE = "active"
    DELIBERATING = "deliberating"
    COMMUNICATING = "communicating"
    RESTING = "resting"
    EMERGENCY = "emergency"

class AgentModel(Base):
    __tablename__ = "agents"

    agent_id: Mapped[str] = mapped_column(String, primary_key=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    model_id: Mapped[str] = mapped_column(String, nullable=False)
    system_prompt: Mapped[str] = mapped_column(String, nullable=False)
    cognitive_state: Mapped[CognitiveStateEnum] = mapped_column(SAEnum(CognitiveStateEnum))

    # Store dynamic dicts as JSONB natively in Postgres
    current_location: Mapped[dict] = mapped_column(JSON, default=dict)
    emotional_state: Mapped[dict] = mapped_column(JSON, default=dict)
    goal_stack: Mapped[list] = mapped_column(JSON, default=list)
    inventory: Mapped[dict] = mapped_column(JSON, default=dict)

class EpisodicMemoryModel(Base):
    __tablename__ = "agent_episodic_memory"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    agent_id: Mapped[str] = mapped_column(String, index=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    event_type: Mapped[str] = mapped_column(String)
    content: Mapped[str] = mapped_column(String)
    retention_score: Mapped[float] = mapped_column(Float, default=1.0)
    summary_level: Mapped[int] = mapped_column(Integer, default=0)

class SemanticMemoryModel(Base):
    __tablename__ = "agent_semantic_memory"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    agent_id: Mapped[str] = mapped_column(String, index=True)
    content: Mapped[str] = mapped_column(String)
    # Using pgvector's Vector type for 384-dimensional HNSW queries
    embedding = Column(Vector(384))
    knowledge_type: Mapped[str] = mapped_column(String, default="FACT")
    source: Mapped[str] = mapped_column(String, default="observation")
    confidence: Mapped[float] = mapped_column(Float, default=1.0)

# Asynchronous SQLAlchemy Engine setup
engine = create_async_engine(settings.database_url.replace("postgresql://", "postgresql+asyncpg://"), echo=False)
AsyncSessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

async def init_db():
    """
    Creates all tables and indexes (including pgvector).
    Used for local deployment/testing.
    """
    async with engine.begin() as conn:
        # Require pgvector extension
        await conn.execute("CREATE EXTENSION IF NOT EXISTS vector")
        await conn.run_sync(Base.metadata.create_all)
