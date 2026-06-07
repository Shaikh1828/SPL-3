"""Add missing critical fields.

Revision ID: 002
Revises: 001
Create Date: 2026-06-07 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '002'
down_revision = '001'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Upgrade: Add missing critical fields."""
    
    # Add description to tournaments if not exists
    try:
        op.add_column('tournaments', sa.Column('description', sa.String(500), nullable=True))
    except Exception:
        pass  # Column already exists
    
    # Ensure archer_id exists in session_archers
    try:
        op.add_column('session_archers', sa.Column('archer_id', sa.Integer(), nullable=False, server_default='0'))
    except Exception:
        pass
    
    # Add created_at and updated_at to session_archers if missing
    try:
        op.add_column('session_archers', sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()))
    except Exception:
        pass
    
    try:
        op.add_column('session_archers', sa.Column('updated_at', sa.DateTime(timezone=True), onupdate=sa.func.now()))
    except Exception:
        pass
    
    # Add current_round to session_archers if missing
    try:
        op.add_column('session_archers', sa.Column('current_round', sa.Integer(), default=1, server_default='1'))
    except Exception:
        pass


def downgrade() -> None:
    """Downgrade: Remove added fields."""
    
    try:
        op.drop_column('tournaments', 'description')
    except Exception:
        pass
    
    try:
        op.drop_column('session_archers', 'archer_id')
    except Exception:
        pass
    
    try:
        op.drop_column('session_archers', 'created_at')
    except Exception:
        pass
    
    try:
        op.drop_column('session_archers', 'updated_at')
    except Exception:
        pass
    
    try:
        op.drop_column('session_archers', 'current_round')
    except Exception:
        pass
