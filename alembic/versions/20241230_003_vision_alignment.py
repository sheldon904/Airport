"""Vision alignment - add PII, priority, communications, contacts.

Revision ID: 20241230_003
Revises: 20241229_002
Create Date: 2024-12-30

This migration adds:
- PII redaction columns to documents table
- Priority/health columns to transactions table
- Communication log table for tracking communications
- Contacts table for lightweight CRM
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB, UUID


# revision identifiers, used by Alembic.
revision = '20241230_003'
down_revision = '20241229_002'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # === Documents table - Privacy columns ===
    op.add_column('documents', sa.Column('redacted_data', JSONB, nullable=True))
    op.add_column('documents', sa.Column('pii_detected', JSONB, server_default='[]', nullable=False))
    op.add_column('documents', sa.Column('access_level', sa.String(50), server_default='organization', nullable=False))
    op.add_column('documents', sa.Column('is_confidential', sa.Boolean, server_default='false', nullable=False))

    # === Transactions table - Priority columns ===
    op.add_column('transactions', sa.Column('priority_score', sa.Integer, server_default='50', nullable=False))
    op.add_column('transactions', sa.Column('health_status', sa.String(20), server_default='on_track', nullable=False))

    # === Communication Log table ===
    op.create_table(
        'communication_log',
        sa.Column('id', UUID(as_uuid=True), primary_key=True),
        sa.Column('transaction_id', UUID(as_uuid=True), sa.ForeignKey('transactions.id', ondelete='SET NULL'), nullable=True),
        sa.Column('organization_id', UUID(as_uuid=True), sa.ForeignKey('organizations.id'), nullable=False),

        # Message details
        sa.Column('direction', sa.String(10), nullable=False),
        sa.Column('channel', sa.String(20), server_default='email', nullable=False),
        sa.Column('subject', sa.String(500), nullable=True),
        sa.Column('body_preview', sa.String(500), nullable=True),
        sa.Column('full_body', sa.Text, nullable=True),

        # Participants
        sa.Column('sender', sa.String(255), nullable=True),
        sa.Column('recipients', JSONB, server_default='[]', nullable=False),

        # Categorization
        sa.Column('topic', sa.String(100), nullable=True),

        # Status
        sa.Column('status', sa.String(50), server_default='sent', nullable=False),

        # Related entities
        sa.Column('related_document_id', UUID(as_uuid=True), sa.ForeignKey('documents.id', ondelete='SET NULL'), nullable=True),
        sa.Column('related_deadline_id', UUID(as_uuid=True), sa.ForeignKey('deadlines.id', ondelete='SET NULL'), nullable=True),

        # Extra data
        sa.Column('extra_data', JSONB, server_default='{}', nullable=False),

        # Timestamps
        sa.Column('sent_at', sa.DateTime, nullable=True),
        sa.Column('created_at', sa.DateTime, server_default=sa.func.now(), nullable=False),
    )

    # Communication log indices
    op.create_index('ix_communication_log_transaction_id', 'communication_log', ['transaction_id'])
    op.create_index('ix_communication_log_organization_id', 'communication_log', ['organization_id'])
    op.create_index('ix_communication_log_topic', 'communication_log', ['topic'])
    op.create_index('ix_communication_log_created_at', 'communication_log', ['created_at'])

    # === Contacts table ===
    op.create_table(
        'contacts',
        sa.Column('id', UUID(as_uuid=True), primary_key=True),
        sa.Column('organization_id', UUID(as_uuid=True), sa.ForeignKey('organizations.id'), nullable=False),

        # Contact info
        sa.Column('email', sa.String(255), nullable=True),
        sa.Column('phone', sa.String(20), nullable=True),
        sa.Column('full_name', sa.String(255), nullable=False),
        sa.Column('contact_type', sa.String(50), server_default='other', nullable=False),
        sa.Column('company', sa.String(255), nullable=True),

        # Source tracking
        sa.Column('source', sa.String(50), server_default='manual', nullable=False),

        # Transaction history
        sa.Column('transaction_count', sa.Integer, server_default='0', nullable=False),
        sa.Column('last_transaction_id', UUID(as_uuid=True), nullable=True),
        sa.Column('last_transaction_date', sa.Date, nullable=True),

        # Organization and categorization
        sa.Column('tags', JSONB, server_default='[]', nullable=False),
        sa.Column('notes', sa.Text, nullable=True),
        sa.Column('extra_data', JSONB, server_default='{}', nullable=False),

        # Timestamps
        sa.Column('created_at', sa.DateTime, server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime, server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
    )

    # Contacts indices
    op.create_index('ix_contacts_organization_id', 'contacts', ['organization_id'])
    op.create_index('ix_contacts_email', 'contacts', ['email'])
    op.create_index('ix_contacts_contact_type', 'contacts', ['contact_type'])

    # Unique constraint for email within organization
    op.create_unique_constraint('uq_contacts_org_email', 'contacts', ['organization_id', 'email'])


def downgrade() -> None:
    # Drop contacts table
    op.drop_constraint('uq_contacts_org_email', 'contacts', type_='unique')
    op.drop_index('ix_contacts_contact_type', 'contacts')
    op.drop_index('ix_contacts_email', 'contacts')
    op.drop_index('ix_contacts_organization_id', 'contacts')
    op.drop_table('contacts')

    # Drop communication_log table
    op.drop_index('ix_communication_log_created_at', 'communication_log')
    op.drop_index('ix_communication_log_topic', 'communication_log')
    op.drop_index('ix_communication_log_organization_id', 'communication_log')
    op.drop_index('ix_communication_log_transaction_id', 'communication_log')
    op.drop_table('communication_log')

    # Drop transactions columns
    op.drop_column('transactions', 'health_status')
    op.drop_column('transactions', 'priority_score')

    # Drop documents columns
    op.drop_column('documents', 'is_confidential')
    op.drop_column('documents', 'access_level')
    op.drop_column('documents', 'pii_detected')
    op.drop_column('documents', 'redacted_data')
