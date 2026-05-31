"""Initial schema migration - create all tables.

Revision ID: 001
Revises: 
Create Date: 2026-05-25 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '001'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Upgrade: Create all tables for archery scoring system."""
    
    # Create users table
    op.create_table(
        'users',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('username', sa.String(50), nullable=False, unique=True),
        sa.Column('email', sa.String(120), nullable=False, unique=True),
        sa.Column('password_hash', sa.String(255), nullable=False),
        sa.Column('role', sa.String(20), nullable=False),
        sa.Column('is_active', sa.Boolean(), default=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), onupdate=sa.func.now()),
        sa.PrimaryKeyConstraint('id'),
        sa.Index('idx_users_username', 'username'),
        sa.Index('idx_users_email', 'email'),
    )

    # Create tournaments table
    op.create_table(
        'tournaments',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(100), nullable=False),
        sa.Column('description', sa.Text()),
        sa.Column('location', sa.String(200)),
        sa.Column('start_date', sa.Date(), nullable=False),
        sa.Column('end_date', sa.Date(), nullable=False),
        sa.Column('created_by', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), onupdate=sa.func.now()),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['created_by'], ['users.id']),
        sa.Index('idx_tournaments_created_by', 'created_by'),
        sa.Index('idx_tournaments_start_date', 'start_date'),
    )

    # Create sessions table (scoring rounds)
    op.create_table(
        'sessions',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('tournament_id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(100), nullable=False),
        sa.Column('round_number', sa.Integer(), nullable=False),
        sa.Column('status', sa.String(20), default='active'),
        sa.Column('start_time', sa.DateTime(timezone=True)),
        sa.Column('end_time', sa.DateTime(timezone=True)),
        sa.Column('num_lanes', sa.Integer(), default=6),
        sa.Column('arrows_per_round', sa.Integer(), default=6),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), onupdate=sa.func.now()),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['tournament_id'], ['tournaments.id']),
        sa.Index('idx_sessions_tournament_id', 'tournament_id'),
        sa.Index('idx_sessions_status', 'status'),
    )

    # Create session_archers (archers participating in session)
    op.create_table(
        'session_archers',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('session_id', sa.Integer(), nullable=False),
        sa.Column('archer_name', sa.String(100), nullable=False),
        sa.Column('lane_number', sa.Integer()),
        sa.Column('total_score', sa.Integer(), default=0),
        sa.Column('registered_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['session_id'], ['sessions.id']),
        sa.Index('idx_session_archers_session_id', 'session_id'),
        sa.Index('idx_session_archers_lane', 'lane_number'),
    )

    # Create scores table
    op.create_table(
        'scores',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('session_id', sa.Integer(), nullable=False),
        sa.Column('session_archer_id', sa.Integer(), nullable=False),
        sa.Column('round_number', sa.Integer(), nullable=False),
        sa.Column('arrow_number', sa.Integer(), nullable=False),
        sa.Column('zone', sa.Integer(), nullable=False),
        sa.Column('points', sa.Integer(), nullable=False),
        sa.Column('image_path', sa.String(255)),
        sa.Column('validated_by_ai', sa.Boolean(), default=False),
        sa.Column('confidence', sa.Float()),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), onupdate=sa.func.now()),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['session_id'], ['sessions.id']),
        sa.ForeignKeyConstraint(['session_archer_id'], ['session_archers.id']),
        sa.Index('idx_scores_session_id', 'session_id'),
        sa.Index('idx_scores_session_archer_id', 'session_archer_id'),
        sa.Index('idx_scores_round_arrow', 'round_number', 'arrow_number'),
    )

    # Create cameras table
    op.create_table(
        'cameras',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(100), nullable=False),
        sa.Column('camera_type', sa.String(20), nullable=False),
        sa.Column('connection_url', sa.String(255)),
        sa.Column('status', sa.String(20), default='disconnected'),
        sa.Column('last_heartbeat', sa.DateTime(timezone=True)),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), onupdate=sa.func.now()),
        sa.PrimaryKeyConstraint('id'),
        sa.Index('idx_cameras_status', 'status'),
    )

    # Create camera_lane_assignments table
    op.create_table(
        'camera_lane_assignments',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('session_id', sa.Integer(), nullable=False),
        sa.Column('camera_id', sa.Integer(), nullable=False),
        sa.Column('lane_number', sa.Integer(), nullable=False),
        sa.Column('assigned_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['session_id'], ['sessions.id']),
        sa.ForeignKeyConstraint(['camera_id'], ['cameras.id']),
        sa.Index('idx_camera_assignments_session_lane', 'session_id', 'lane_number'),
    )

    # Create audit_logs table
    op.create_table(
        'audit_logs',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer()),
        sa.Column('action', sa.String(100), nullable=False),
        sa.Column('entity_type', sa.String(50), nullable=False),
        sa.Column('entity_id', sa.Integer()),
        sa.Column('details', sa.Text()),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id']),
        sa.Index('idx_audit_logs_user_id', 'user_id'),
        sa.Index('idx_audit_logs_action', 'action'),
        sa.Index('idx_audit_logs_created_at', 'created_at'),
    )


def downgrade() -> None:
    """Downgrade: Drop all tables."""
    op.drop_table('audit_logs')
    op.drop_table('camera_lane_assignments')
    op.drop_table('cameras')
    op.drop_table('scores')
    op.drop_table('session_archers')
    op.drop_table('sessions')
    op.drop_table('tournaments')
    op.drop_table('users')
