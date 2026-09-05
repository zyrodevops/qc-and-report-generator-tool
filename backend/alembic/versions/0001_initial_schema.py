"""Initial migration: 7 core tables, sequences, constraints, and audit immutability triggers

Revision ID: 0001_initial_schema
Revises:
Create Date: 2026-09-04 13:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '0001_initial_schema'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. Enable pgcrypto extension for gen_random_uuid()
    op.execute('CREATE EXTENSION IF NOT EXISTS "pgcrypto";')

    # 2. users table
    op.create_table(
        'users',
        sa.Column('id', sa.UUID(), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('email', sa.String(length=255), nullable=False),
        sa.Column('hashed_password', sa.String(length=255), nullable=False),
        sa.Column('full_name', sa.String(length=255), nullable=False),
        sa.Column('role', sa.String(length=64), server_default='surveyor', nullable=False),
        sa.Column('is_active', sa.Boolean(), server_default=sa.text('true'), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('clock_timestamp()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('clock_timestamp()'), nullable=False),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_users')),
        sa.UniqueConstraint('email', name=op.f('uq_users_email'))
    )
    op.create_index(op.f('ix_users_email'), 'users', ['email'], unique=True)

    # 3. templates table
    op.create_table(
        'templates',
        sa.Column('id', sa.String(length=128), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('family', sa.String(length=64), nullable=False),
        sa.Column('mode', sa.String(length=16), nullable=False),
        sa.Column('block_sequence', postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'[]'::jsonb"), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('clock_timestamp()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('clock_timestamp()'), nullable=False),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_templates'))
    )
    op.create_index('ix_templates_family_mode', 'templates', ['family', 'mode'], unique=False)
    op.create_index(op.f('ix_templates_family'), 'templates', ['family'], unique=False)

    # 4. reports table
    op.create_table(
        'reports',
        sa.Column('id', sa.UUID(), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('report_number', sa.String(length=64), nullable=False),
        sa.Column('family', sa.String(length=64), nullable=False),
        sa.Column('state', sa.String(length=32), server_default='DRAFT', nullable=False),
        sa.Column('template_id', sa.String(length=128), nullable=False),
        sa.Column('status', sa.String(length=32), server_default='DRAFT', nullable=False),
        sa.Column('block_state', postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'{}'::jsonb"), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('clock_timestamp()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('clock_timestamp()'), nullable=False),
        sa.ForeignKeyConstraint(['template_id'], ['templates.id'], name=op.f('fk_reports_template_id_templates'), ondelete='RESTRICT'),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_reports')),
        sa.UniqueConstraint('report_number', name='uq_reports_report_number')
    )
    op.create_index(op.f('ix_reports_family'), 'reports', ['family'], unique=False)
    op.create_index(op.f('ix_reports_status'), 'reports', ['status'], unique=False)
    op.create_index(op.f('ix_reports_template_id'), 'reports', ['template_id'], unique=False)
    op.create_index(op.f('ix_reports_created_at'), 'reports', ['created_at'], unique=False)
    op.create_index(
        'ix_reports_block_state_gin',
        'reports',
        ['block_state'],
        unique=False,
        postgresql_using='gin',
        postgresql_ops={'block_state': 'jsonb_path_ops'}
    )

    # 5. assets table
    op.create_table(
        'assets',
        sa.Column('id', sa.String(length=64), nullable=False),
        sa.Column('report_id', sa.UUID(), nullable=False),
        sa.Column('kind', sa.String(length=32), nullable=False),
        sa.Column('sha256', sa.CHAR(length=64), nullable=False),
        sa.Column('original_path', sa.Text(), nullable=False),
        sa.Column('derived_paths', postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'{}'::jsonb"), nullable=False),
        sa.Column('exif', postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'{}'::jsonb"), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('clock_timestamp()'), nullable=False),
        sa.ForeignKeyConstraint(['report_id'], ['reports.id'], name=op.f('fk_assets_report_id_reports'), ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_assets'))
    )
    op.create_index(op.f('ix_assets_report_id'), 'assets', ['report_id'], unique=False)
    op.create_index(op.f('ix_assets_kind'), 'assets', ['kind'], unique=False)
    op.create_index(op.f('ix_assets_sha256'), 'assets', ['sha256'], unique=False)

    # 6. audit table (Identity BIGINT, Immutable)
    op.create_table(
        'audit',
        sa.Column('id', sa.BigInteger(), sa.Identity(always=True), nullable=False),
        sa.Column('report_id', sa.UUID(), nullable=True),
        sa.Column('at', sa.DateTime(timezone=True), server_default=sa.text('clock_timestamp()'), nullable=False),
        sa.Column('actor', sa.String(length=255), nullable=False),
        sa.Column('action', sa.String(length=64), nullable=False),
        sa.Column('path', sa.String(length=255), nullable=True),
        sa.Column('before', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('after', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.ForeignKeyConstraint(['report_id'], ['reports.id'], name=op.f('fk_audit_report_id_reports'), ondelete='RESTRICT'),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_audit'))
    )
    op.create_index(op.f('ix_audit_report_id'), 'audit', ['report_id'], unique=False)
    op.create_index(op.f('ix_audit_at'), 'audit', ['at'], unique=False)
    op.create_index(op.f('ix_audit_actor'), 'audit', ['actor'], unique=False)
    op.create_index(op.f('ix_audit_action'), 'audit', ['action'], unique=False)

    # 7. clauses table
    op.create_table(
        'clauses',
        sa.Column('id', sa.String(length=128), nullable=False),
        sa.Column('key', sa.String(length=128), nullable=False),
        sa.Column('version', sa.Integer(), server_default='1', nullable=False),
        sa.Column('text_with_slots', sa.Text(), nullable=False),
        sa.Column('conditions', postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'{}'::jsonb"), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('clock_timestamp()'), nullable=False),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_clauses')),
        sa.UniqueConstraint('key', 'version', name='uq_clauses_key_version')
    )
    op.create_index(op.f('ix_clauses_key'), 'clauses', ['key'], unique=False)

    # 8. report_sequences table
    op.create_table(
        'report_sequences',
        sa.Column('year', sa.Integer(), nullable=False),
        sa.Column('current_val', sa.Integer(), server_default='0', nullable=False),
        sa.CheckConstraint('current_val >= 0', name='chk_report_sequences_current_val'),
        sa.CheckConstraint('year >= 2000 AND year <= 2100', name='chk_report_sequences_year'),
        sa.PrimaryKeyConstraint('year', name=op.f('pk_report_sequences'))
    )

    # 9. PostgreSQL Triggers: Audit Immutability (block UPDATE, DELETE, TRUNCATE)
    op.execute("""
        CREATE OR REPLACE FUNCTION trg_fn_audit_prevent_modification()
        RETURNS TRIGGER AS $$
        BEGIN
            RAISE EXCEPTION 'Table audit is append-only / strictly immutable. Operation % is forbidden.', TG_OP
            USING ERRCODE = '55000';
            RETURN NULL;
        END;
        $$ LANGUAGE plpgsql;

        CREATE TRIGGER trg_audit_immutable_row
        BEFORE UPDATE OR DELETE ON audit
        FOR EACH ROW
        EXECUTE FUNCTION trg_fn_audit_prevent_modification();

        CREATE TRIGGER trg_audit_immutable_truncate
        BEFORE TRUNCATE ON audit
        FOR EACH STATEMENT
        EXECUTE FUNCTION trg_fn_audit_prevent_modification();
    """)

    # 10. PostgreSQL Triggers: automatic updated_at timestamp update
    op.execute("""
        CREATE OR REPLACE FUNCTION trg_fn_set_updated_at()
        RETURNS TRIGGER AS $$
        BEGIN
            NEW.updated_at = clock_timestamp();
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;

        CREATE TRIGGER trg_reports_updated_at
        BEFORE UPDATE ON reports
        FOR EACH ROW
        EXECUTE FUNCTION trg_fn_set_updated_at();

        CREATE TRIGGER trg_templates_updated_at
        BEFORE UPDATE ON templates
        FOR EACH ROW
        EXECUTE FUNCTION trg_fn_set_updated_at();

        CREATE TRIGGER trg_users_updated_at
        BEFORE UPDATE ON users
        FOR EACH ROW
        EXECUTE FUNCTION trg_fn_set_updated_at();
    """)


def downgrade() -> None:
    # 1. Drop triggers and functions
    op.execute("DROP TRIGGER IF EXISTS trg_users_updated_at ON users;")
    op.execute("DROP TRIGGER IF EXISTS trg_templates_updated_at ON templates;")
    op.execute("DROP TRIGGER IF EXISTS trg_reports_updated_at ON reports;")
    op.execute("DROP FUNCTION IF EXISTS trg_fn_set_updated_at();")
    op.execute("DROP TRIGGER IF EXISTS trg_audit_immutable_truncate ON audit;")
    op.execute("DROP TRIGGER IF EXISTS trg_audit_immutable_row ON audit;")
    op.execute("DROP FUNCTION IF EXISTS trg_fn_audit_prevent_modification();")

    # 2. Drop tables in reverse foreign key order
    op.drop_table('report_sequences')
    op.drop_table('clauses')
    op.drop_table('audit')
    op.drop_table('assets')
    op.drop_table('reports')
    op.drop_table('templates')
    op.drop_table('users')
