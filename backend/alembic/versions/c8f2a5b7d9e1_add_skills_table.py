"""add_skills_table

Revision ID: c8f2a5b7d9e1
Revises: 92393ee10649
Create Date: 2026-01-23 19:59:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from pgvector.sqlalchemy import Vector

from alembic import op

# revision identifiers, used by Alembic.
revision: str = 'c8f2a5b7d9e1'
down_revision: Union[str, None] = '92393ee10649'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Enable pgvector extension
    op.execute('CREATE EXTENSION IF NOT EXISTS vector')
    
    # Create skills table
    op.create_table(
        'skills',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('agent_role', sa.String(255), nullable=False),
        sa.Column('task_description', sa.Text(), nullable=False),
        sa.Column('solution_code', sa.Text(), nullable=False),
        sa.Column('embedding', Vector(1536), nullable=True),
        sa.Column('usage_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create index for agent_role filtering
    op.create_index('ix_skills_agent_role', 'skills', ['agent_role'])


def downgrade() -> None:
    op.drop_index('ix_skills_agent_role', table_name='skills')
    op.drop_table('skills')
