"""Add soft delete to transactions and fix audit cascade

Revision ID: 002_audit_soft_delete
Revises: 001_initial
Create Date: 2024-12-29

This migration:
1. Adds soft delete columns (deleted_at, deleted_by) to transactions
2. Adds transaction metadata columns (is_hoa, is_condo, is_financed)
3. Changes audit_logs.transaction_id FK from CASCADE to SET NULL
4. Adds index on transactions.deleted_at

These changes are required for compliance:
- RESPA/TRID: 3 years audit retention
- Florida F.S. 475.5015: 5 years broker record retention
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = '002_audit_soft_delete'
down_revision: Union[str, None] = '001_initial'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add soft delete columns to transactions
    op.add_column('transactions', sa.Column('deleted_at', sa.DateTime, nullable=True))
    op.add_column('transactions', sa.Column('deleted_by', postgresql.UUID(as_uuid=True), nullable=True))

    # Add transaction metadata columns for conditional compliance
    op.add_column('transactions', sa.Column('is_hoa', sa.Boolean, server_default='false', nullable=False))
    op.add_column('transactions', sa.Column('is_condo', sa.Boolean, server_default='false', nullable=False))
    op.add_column('transactions', sa.Column('is_financed', sa.Boolean, server_default='true', nullable=False))

    # Add foreign key for deleted_by
    op.create_foreign_key(
        'fk_transactions_deleted_by_users',
        'transactions', 'users',
        ['deleted_by'], ['id']
    )

    # Add index on deleted_at for efficient soft-delete queries
    op.create_index('ix_transactions_deleted_at', 'transactions', ['deleted_at'])

    # Change audit_logs.transaction_id FK from CASCADE to SET NULL
    # First drop the existing constraint
    op.drop_constraint('audit_logs_transaction_id_fkey', 'audit_logs', type_='foreignkey')

    # Re-create with SET NULL
    op.create_foreign_key(
        'audit_logs_transaction_id_fkey',
        'audit_logs', 'transactions',
        ['transaction_id'], ['id'],
        ondelete='SET NULL'
    )


def downgrade() -> None:
    # Revert audit_logs FK to CASCADE
    op.drop_constraint('audit_logs_transaction_id_fkey', 'audit_logs', type_='foreignkey')
    op.create_foreign_key(
        'audit_logs_transaction_id_fkey',
        'audit_logs', 'transactions',
        ['transaction_id'], ['id'],
        ondelete='CASCADE'
    )

    # Drop index
    op.drop_index('ix_transactions_deleted_at', 'transactions')

    # Drop foreign key
    op.drop_constraint('fk_transactions_deleted_by_users', 'transactions', type_='foreignkey')

    # Drop columns
    op.drop_column('transactions', 'is_financed')
    op.drop_column('transactions', 'is_condo')
    op.drop_column('transactions', 'is_hoa')
    op.drop_column('transactions', 'deleted_by')
    op.drop_column('transactions', 'deleted_at')
