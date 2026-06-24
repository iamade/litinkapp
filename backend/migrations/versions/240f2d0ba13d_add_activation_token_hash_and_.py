"""add activation_token_hash and activation_token_expires_at to user

Revision ID: 240f2d0ba13d
Revises: c1d2e3f4g5h6
Create Date: 2026-06-11 08:40:55.003516

"""
from typing import Sequence, Union

from alembic import op
from sqlalchemy import engine_from_config
from sqlalchemy.engine import reflection
import sqlalchemy as sa
import sqlmodel
from sqlalchemy.dialects import postgresql
import logging

# revision identifiers, used by Alembic.
revision: str = '240f2d0ba13d'
down_revision: Union[str, Sequence[str], None] = 'c1d2e3f4g5h6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

logger = logging.getLogger(__name__)


def _table_exists(table_name: str) -> bool:
    conn = op.get_bind()
    insp = reflection.Inspector.from_engine(conn)
    return table_name in insp.get_table_names()


def _has_column(table_name: str, column_name: str) -> bool:
    if not _table_exists(table_name):
        return False
    conn = op.get_bind()
    insp = reflection.Inspector.from_engine(conn)
    cols = {c['name'] for c in insp.get_columns(table_name)}
    return column_name in cols


def _has_index(table_name: str, index_name: str) -> bool:
    if not _table_exists(table_name):
        return False
    conn = op.get_bind()
    insp = reflection.Inspector.from_engine(conn)
    idxs = {i['name'] for i in insp.get_indexes(table_name)}
    return index_name in idxs


def _has_constraint(table_name: str, constraint_name: str, constraint_type: str = None) -> bool:
    if not _table_exists(table_name):
        return False
    conn = op.get_bind()
    insp = reflection.Inspector.from_engine(conn)
    # Map constraint_type keywords to Alembic inspector methods
    if constraint_type == 'unique':
        cons = {c['name'] for c in insp.get_unique_constraints(table_name)}
    elif constraint_type == 'foreign_key':
        cons = {c['name'] for c in insp.get_foreign_keys(table_name)}
    elif constraint_type == 'primary_key':
        cons = set(insp.get_pk_constraint(table_name).get('constrained_columns', []))
        return constraint_name in cons
    else:
        # Generic: union of unique + check constraints
        cons = {c['name'] for c in insp.get_unique_constraints(table_name)}
        cons.update({c['name'] for c in insp.get_check_constraints(table_name) if 'name' in c})
    return constraint_name in cons


def upgrade() -> None:
    """Upgrade schema defensively for environments with partial table sets."""
    # 1. audiobook_chapters.error_message TEXT -> AutoString
    if _table_exists('audiobook_chapters') and _has_column('audiobook_chapters', 'error_message'):
        op.alter_column('audiobook_chapters', 'error_message',
                   existing_type=sa.TEXT(),
                   type_=sqlmodel.sql.sqltypes.AutoString(),
                   existing_nullable=True)
    else:
        logger.warning('Skipping audiobook_chapters.error_message alter: table/column missing.')

    # 2. audiobooks.error_message TEXT -> AutoString
    if _table_exists('audiobooks') and _has_column('audiobooks', 'error_message'):
        op.alter_column('audiobooks', 'error_message',
                   existing_type=sa.TEXT(),
                   type_=sqlmodel.sql.sqltypes.AutoString(),
                   existing_nullable=True)
    else:
        logger.warning('Skipping audiobooks.error_message alter: table/column missing.')

    # 3. drop_index ix_credit_failures_status
    if _has_index('credit_failures', 'ix_credit_failures_status'):
        op.drop_index(op.f('ix_credit_failures_status'), table_name='credit_failures')
    else:
        logger.warning('Skipping drop_index ix_credit_failures_status: index missing.')

    # 4. drop_constraint promo_codes_code_key unique
    if _has_constraint('promo_codes', 'promo_codes_code_key', 'unique'):
        op.drop_constraint(op.f('promo_codes_code_key'), 'promo_codes', type_='unique')
    else:
        logger.warning('Skipping drop_constraint promo_codes_code_key: constraint missing.')

    # 5. drop_index ix_promo_codes_code
    if _has_index('promo_codes', 'ix_promo_codes_code'):
        op.drop_index(op.f('ix_promo_codes_code'), table_name='promo_codes')
    else:
        logger.warning('Skipping drop_index ix_promo_codes_code: index missing.')

    # 6. create_index ix_promo_codes_code unique
    if _table_exists('promo_codes'):
        if not _has_index('promo_codes', 'ix_promo_codes_code'):
            op.create_index(op.f('ix_promo_codes_code'), 'promo_codes', ['code'], unique=True)
        else:
            logger.warning('Skipping create_index ix_promo_codes_code: index already exists.')
    else:
        logger.warning('Skipping create_index ix_promo_codes_code: table missing.')

    # 7. alter_column trailer_generations.completed_at TIMESTAMP -> DateTime
    if _table_exists('trailer_generations') and _has_column('trailer_generations', 'completed_at'):
        op.alter_column('trailer_generations', 'completed_at',
                   existing_type=postgresql.TIMESTAMP(timezone=True),
                   type_=sa.DateTime(),
                   existing_nullable=True)
    else:
        logger.warning('Skipping trailer_generations.completed_at alter: table/column missing.')

    # 8-10. user columns + index
    if _table_exists('user'):
        if not _has_column('user', 'activation_token_hash'):
            op.add_column('user', sa.Column('activation_token_hash', sqlmodel.sql.sqltypes.AutoString(length=128), nullable=True))
        else:
            logger.warning('Skipping add_column user.activation_token_hash: column already exists.')

        if not _has_column('user', 'activation_token_expires_at'):
            op.add_column('user', sa.Column('activation_token_expires_at', postgresql.TIMESTAMP(timezone=True), nullable=True))
        else:
            logger.warning('Skipping add_column user.activation_token_expires_at: column already exists.')

        if not _has_index('user', 'ix_user_activation_token_hash'):
            op.create_index(op.f('ix_user_activation_token_hash'), 'user', ['activation_token_hash'], unique=False)
        else:
            logger.warning('Skipping create_index ix_user_activation_token_hash: index already exists.')
    else:
        logger.warning('Skipping user activation_token_* operations: user table missing.')

    # 11. drop_index ix_user_downloads_downloaded_at
    if _has_index('user_downloads', 'ix_user_downloads_downloaded_at'):
        op.drop_index(op.f('ix_user_downloads_downloaded_at'), table_name='user_downloads')
    else:
        logger.warning('Skipping drop_index ix_user_downloads_downloaded_at: index missing.')

    # 12. alter_column video_generations.error_message TEXT -> AutoString
    if _table_exists('video_generations') and _has_column('video_generations', 'error_message'):
        op.alter_column('video_generations', 'error_message',
                   existing_type=sa.TEXT(),
                   type_=sqlmodel.sql.sqltypes.AutoString(),
                   existing_nullable=True)
    else:
        logger.warning('Skipping video_generations.error_message alter: table/column missing.')


def downgrade() -> None:
    """Downgrade schema defensively for environments with partial table sets."""
    # Reverse order of upgrade operations.
    if _table_exists('video_generations') and _has_column('video_generations', 'error_message'):
        op.alter_column('video_generations', 'error_message',
                   existing_type=sqlmodel.sql.sqltypes.AutoString(),
                   type_=sa.TEXT(),
                   existing_nullable=True)
    else:
        logger.warning('Skipping downgrade video_generations.error_message alter: table/column missing.')

    if _has_index('user_downloads', 'ix_user_downloads_downloaded_at'):
        op.create_index(op.f('ix_user_downloads_downloaded_at'), 'user_downloads', ['downloaded_at'], unique=False)
    else:
        logger.warning('Skipping downgrade create_index ix_user_downloads_downloaded_at: index missing.')

    if _table_exists('user'):
        if _has_index('user', 'ix_user_activation_token_hash'):
            op.drop_index(op.f('ix_user_activation_token_hash'), table_name='user')
        else:
            logger.warning('Skipping downgrade drop_index ix_user_activation_token_hash: index missing.')

        if _has_column('user', 'activation_token_expires_at'):
            op.drop_column('user', 'activation_token_expires_at')
        else:
            logger.warning('Skipping downgrade drop_column user.activation_token_expires_at: column missing.')

        if _has_column('user', 'activation_token_hash'):
            op.drop_column('user', 'activation_token_hash')
        else:
            logger.warning('Skipping downgrade drop_column user.activation_token_hash: column missing.')
    else:
        logger.warning('Skipping downgrade user activation_token_* operations: user table missing.')

    if _table_exists('trailer_generations') and _has_column('trailer_generations', 'completed_at'):
        op.alter_column('trailer_generations', 'completed_at',
                   existing_type=sa.DateTime(),
                   type_=postgresql.TIMESTAMP(timezone=True),
                   existing_nullable=True)
    else:
        logger.warning('Skipping downgrade trailer_generations.completed_at alter: table/column missing.')

    if _has_index('promo_codes', 'ix_promo_codes_code'):
        op.drop_index(op.f('ix_promo_codes_code'), table_name='promo_codes')
    else:
        logger.warning('Skipping downgrade drop_index ix_promo_codes_code: index missing.')

    if _table_exists('promo_codes'):
        if not _has_index('promo_codes', 'ix_promo_codes_code'):
            op.create_index(op.f('ix_promo_codes_code'), 'promo_codes', ['code'], unique=False)
        else:
            logger.warning('Skipping downgrade create_index ix_promo_codes_code: index already exists.')

        if not _has_constraint('promo_codes', 'promo_codes_code_key', 'unique'):
            op.create_unique_constraint(op.f('promo_codes_code_key'), 'promo_codes', ['code'], postgresql_nulls_not_distinct=False)
        else:
            logger.warning('Skipping downgrade create_unique_constraint promo_codes_code_key: constraint already exists.')
    else:
        logger.warning('Skipping downgrade promo_codes operations: table missing.')

    if not _has_index('credit_failures', 'ix_credit_failures_status'):
        op.create_index(op.f('ix_credit_failures_status'), 'credit_failures', ['status'], unique=False)
    else:
        logger.warning('Skipping downgrade create_index ix_credit_failures_status: index already exists.')

    if _table_exists('audiobooks') and _has_column('audiobooks', 'error_message'):
        op.alter_column('audiobooks', 'error_message',
                   existing_type=sqlmodel.sql.sqltypes.AutoString(),
                   type_=sa.TEXT(),
                   existing_nullable=True)
    else:
        logger.warning('Skipping downgrade audiobooks.error_message alter: table/column missing.')

    if _table_exists('audiobook_chapters') and _has_column('audiobook_chapters', 'error_message'):
        op.alter_column('audiobook_chapters', 'error_message',
                   existing_type=sqlmodel.sql.sqltypes.AutoString(),
                   type_=sa.TEXT(),
                   existing_nullable=True)
    else:
        logger.warning('Skipping downgrade audiobook_chapters.error_message alter: table/column missing.')
