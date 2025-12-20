"""Initial database schema

Revision ID: 001_initial
Revises:
Create Date: 2024-12-20

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '001_initial'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Organizations table
    op.create_table(
        'organizations',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('license_number', sa.String(50), nullable=True),
        sa.Column('state', sa.String(2), nullable=False, server_default='FL'),
        sa.Column('subscription_tier', sa.String(50), server_default='starter'),
        sa.Column('subscription_status', sa.String(50), server_default='active'),
        sa.Column('settings', postgresql.JSONB, server_default='{}'),
        sa.Column('compliance_config', postgresql.JSONB, server_default='{}'),
        sa.Column('created_at', sa.DateTime, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime, server_default=sa.func.now(), onupdate=sa.func.now()),
    )

    # Users table
    op.create_table(
        'users',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('organization_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('organizations.id'), nullable=False),
        sa.Column('email', sa.String(255), unique=True, nullable=False),
        sa.Column('hashed_password', sa.String(255), nullable=False),
        sa.Column('full_name', sa.String(255), nullable=False),
        sa.Column('role', sa.String(50), server_default='agent'),
        sa.Column('phone', sa.String(20), nullable=True),
        sa.Column('license_number', sa.String(50), nullable=True),
        sa.Column('notification_preferences', postgresql.JSONB, server_default='{}'),
        sa.Column('is_active', sa.Boolean, server_default='true'),
        sa.Column('email_verified', sa.Boolean, server_default='false'),
        sa.Column('created_at', sa.DateTime, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime, server_default=sa.func.now(), onupdate=sa.func.now()),
        sa.Column('last_login_at', sa.DateTime, nullable=True),
    )
    op.create_index('ix_users_organization_id', 'users', ['organization_id'])
    op.create_index('ix_users_email', 'users', ['email'])

    # Transactions table
    op.create_table(
        'transactions',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('organization_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('organizations.id'), nullable=False),
        sa.Column('created_by', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('status', sa.String(50), server_default='draft'),
        sa.Column('transaction_type', sa.String(50), nullable=False),
        sa.Column('property_address', postgresql.JSONB, nullable=False),
        sa.Column('purchase_price', sa.Numeric(12, 2), nullable=True),
        sa.Column('year_built', sa.Integer, nullable=True),
        sa.Column('effective_date', sa.Date, nullable=True),
        sa.Column('closing_date', sa.Date, nullable=True),
        sa.Column('parties', postgresql.JSONB, server_default='[]'),
        sa.Column('notes', sa.Text, nullable=True),
        sa.Column('created_at', sa.DateTime, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime, server_default=sa.func.now(), onupdate=sa.func.now()),
    )
    op.create_index('ix_transactions_organization_id', 'transactions', ['organization_id'])
    op.create_index('ix_transactions_status', 'transactions', ['status'])
    op.create_index('ix_transactions_closing_date', 'transactions', ['closing_date'])

    # Documents table
    op.create_table(
        'documents',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('transaction_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('transactions.id'), nullable=False),
        sa.Column('uploaded_by', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('document_type', sa.String(50), nullable=False),
        sa.Column('filename', sa.String(255), nullable=False),
        sa.Column('storage_path', sa.String(500), nullable=False),
        sa.Column('content_type', sa.String(100), server_default='application/pdf'),
        sa.Column('file_size', sa.Integer, nullable=True),
        sa.Column('status', sa.String(50), server_default='uploaded'),
        sa.Column('extracted_data', postgresql.JSONB, nullable=True),
        sa.Column('extraction_confidence', sa.Float, nullable=True),
        sa.Column('needs_review_reason', sa.Text, nullable=True),
        sa.Column('verified_at', sa.DateTime, nullable=True),
        sa.Column('verified_by', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id'), nullable=True),
        sa.Column('uploaded_at', sa.DateTime, server_default=sa.func.now()),
    )
    op.create_index('ix_documents_transaction_id', 'documents', ['transaction_id'])
    op.create_index('ix_documents_status', 'documents', ['status'])

    # Deadlines table
    op.create_table(
        'deadlines',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('transaction_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('transactions.id'), nullable=False),
        sa.Column('source_document_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('documents.id'), nullable=True),
        sa.Column('deadline_type', sa.String(50), nullable=False),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('description', sa.Text, nullable=True),
        sa.Column('due_date', sa.Date, nullable=False),
        sa.Column('status', sa.String(50), server_default='upcoming'),
        sa.Column('reminder_days', postgresql.JSONB, server_default='[7, 3, 1]'),
        sa.Column('last_reminder_sent', sa.DateTime, nullable=True),
        sa.Column('completed_at', sa.DateTime, nullable=True),
        sa.Column('completed_by', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id'), nullable=True),
        sa.Column('notes', sa.Text, nullable=True),
        sa.Column('created_at', sa.DateTime, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime, server_default=sa.func.now(), onupdate=sa.func.now()),
    )
    op.create_index('ix_deadlines_transaction_id', 'deadlines', ['transaction_id'])
    op.create_index('ix_deadlines_due_date', 'deadlines', ['due_date'])
    op.create_index('ix_deadlines_status', 'deadlines', ['status'])

    # Checklists table
    op.create_table(
        'checklists',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('transaction_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('transactions.id'), nullable=False, unique=True),
        sa.Column('template_id', sa.String(100), nullable=False),
        sa.Column('items', postgresql.JSONB, server_default='[]'),
        sa.Column('created_at', sa.DateTime, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime, server_default=sa.func.now(), onupdate=sa.func.now()),
    )

    # Audit logs table
    op.create_table(
        'audit_logs',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('transaction_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('transactions.id'), nullable=True),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id'), nullable=True),
        sa.Column('action', sa.String(100), nullable=False),
        sa.Column('agent_type', sa.String(50), nullable=True),
        sa.Column('resource_type', sa.String(50), nullable=True),
        sa.Column('resource_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('details', postgresql.JSONB, server_default='{}'),
        sa.Column('ip_address', sa.String(50), nullable=True),
        sa.Column('user_agent', sa.String(500), nullable=True),
        sa.Column('created_at', sa.DateTime, server_default=sa.func.now()),
    )
    op.create_index('ix_audit_logs_transaction_id', 'audit_logs', ['transaction_id'])
    op.create_index('ix_audit_logs_created_at', 'audit_logs', ['created_at'])
    op.create_index('ix_audit_logs_action', 'audit_logs', ['action'])

    # Job queue table for background processing
    op.create_table(
        'job_queue',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('job_type', sa.String(100), nullable=False),
        sa.Column('status', sa.String(50), server_default='pending'),
        sa.Column('priority', sa.Integer, server_default='0'),
        sa.Column('payload', postgresql.JSONB, nullable=False),
        sa.Column('result', postgresql.JSONB, nullable=True),
        sa.Column('error', sa.Text, nullable=True),
        sa.Column('attempts', sa.Integer, server_default='0'),
        sa.Column('max_attempts', sa.Integer, server_default='3'),
        sa.Column('scheduled_at', sa.DateTime, server_default=sa.func.now()),
        sa.Column('started_at', sa.DateTime, nullable=True),
        sa.Column('completed_at', sa.DateTime, nullable=True),
        sa.Column('created_at', sa.DateTime, server_default=sa.func.now()),
    )
    op.create_index('ix_job_queue_status_priority', 'job_queue', ['status', 'priority', 'scheduled_at'])
    op.create_index('ix_job_queue_job_type', 'job_queue', ['job_type'])


def downgrade() -> None:
    op.drop_table('job_queue')
    op.drop_table('audit_logs')
    op.drop_table('checklists')
    op.drop_table('deadlines')
    op.drop_table('documents')
    op.drop_table('transactions')
    op.drop_table('users')
    op.drop_table('organizations')
