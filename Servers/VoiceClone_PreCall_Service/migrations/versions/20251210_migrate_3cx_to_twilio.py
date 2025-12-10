"""migrate from 3CX to Twilio schema

Revision ID: 001_3cx_to_twilio
Revises: 
Create Date: 2025-12-10 16:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '001_3cx_to_twilio'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Migrate from 3CX to Twilio naming."""
    
    # Rename threecx_call_id column to call_sid in call_log table
    op.alter_column(
        'call_log',
        'threecx_call_id',
        new_column_name='call_sid',
        existing_type=sa.String(255),
        existing_nullable=False,
        comment='Twilio call SID (replaces 3CX call ID)'
    )
    
    # Drop old index
    op.drop_index('ix_call_log_threecx_call_id', table_name='call_log')
    
    # Create new index
    op.create_index('ix_call_log_call_sid', 'call_log', ['call_sid'])
    
    # Update check constraint to include 'processing' status
    op.drop_constraint('call_log_status_check', 'call_log', type_='check')
    op.create_check_constraint(
        'call_log_status_check',
        'call_log',
        "status IN ('initiated', 'completed', 'failed', 'processing')"
    )
    
    # Update comment on call_id column
    op.alter_column(
        'call_log',
        'call_id',
        existing_type=sa.String(255),
        comment='ElevenLabs call ID or Twilio call SID'
    )


def downgrade() -> None:
    """Revert from Twilio to 3CX naming."""
    
    # Revert call_id comment
    op.alter_column(
        'call_log',
        'call_id',
        existing_type=sa.String(255),
        comment='ElevenLabs call ID'
    )
    
    # Revert check constraint
    op.drop_constraint('call_log_status_check', 'call_log', type_='check')
    op.create_check_constraint(
        'call_log_status_check',
        'call_log',
        "status IN ('initiated', 'completed', 'failed')"
    )
    
    # Drop new index
    op.drop_index('ix_call_log_call_sid', table_name='call_log')
    
    # Create old index
    op.create_index('ix_call_log_threecx_call_id', 'call_log', ['call_sid'])
    
    # Rename call_sid back to threecx_call_id
    op.alter_column(
        'call_log',
        'call_sid',
        new_column_name='threecx_call_id',
        existing_type=sa.String(255),
        existing_nullable=False,
        comment='3CX call ID'
    )
