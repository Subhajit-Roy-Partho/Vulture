"""CV profile expansion

Revision ID: 0002_cv_profile_expansion
Revises: 0001_initial_schema
Create Date: 2026-02-14

"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "0002_cv_profile_expansion"
down_revision = "0001_initial_schema"
branch_labels = None
depends_on = None


def _has_table(insp: sa.Inspector, table: str) -> bool:
    return table in insp.get_table_names()


def _has_column(insp: sa.Inspector, table: str, column: str) -> bool:
    if not _has_table(insp, table):
        return False
    cols = {c["name"] for c in insp.get_columns(table)}
    return column in cols


def _ensure_index(table: str, name: str, columns: list[str]) -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    existing = {idx["name"] for idx in insp.get_indexes(table)}
    if name not in existing:
        op.create_index(name, table, columns, unique=False)


def upgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)

    if _has_table(insp, "question_bank"):
        with op.batch_alter_table("question_bank", schema=None) as batch_op:
            if not _has_column(insp, "question_bank", "section"):
                batch_op.add_column(
                    sa.Column("section", sa.String(length=120), nullable=False, server_default="general")
                )
            if not _has_column(insp, "question_bank", "importance"):
                batch_op.add_column(
                    sa.Column("importance", sa.String(length=20), nullable=False, server_default="medium")
                )
            if not _has_column(insp, "question_bank", "is_cv_derived"):
                batch_op.add_column(
                    sa.Column("is_cv_derived", sa.Boolean(), nullable=False, server_default=sa.false())
                )

    bind = op.get_bind()
    insp = sa.inspect(bind)

    if _has_table(insp, "profile_answers"):
        with op.batch_alter_table("profile_answers", schema=None) as batch_op:
            if not _has_column(insp, "profile_answers", "source"):
                batch_op.add_column(
                    sa.Column("source", sa.String(length=120), nullable=False, server_default="manual")
                )
            if not _has_column(insp, "profile_answers", "verification_state"):
                batch_op.add_column(
                    sa.Column(
                        "verification_state",
                        sa.String(length=40),
                        nullable=False,
                        server_default="verified",
                    )
                )
            if not _has_column(insp, "profile_answers", "source_section"):
                batch_op.add_column(
                    sa.Column(
                        "source_section",
                        sa.String(length=120),
                        nullable=False,
                        server_default="general",
                    )
                )
            if not _has_column(insp, "profile_answers", "evidence_json"):
                batch_op.add_column(
                    sa.Column("evidence_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'"))
                )

    bind = op.get_bind()
    insp = sa.inspect(bind)

    if _has_table(insp, "educations"):
        with op.batch_alter_table("educations", schema=None) as batch_op:
            if not _has_column(insp, "educations", "thesis_title"):
                batch_op.add_column(sa.Column("thesis_title", sa.Text(), nullable=False, server_default=""))
            if not _has_column(insp, "educations", "advisor"):
                batch_op.add_column(sa.Column("advisor", sa.String(length=255), nullable=False, server_default=""))
            if not _has_column(insp, "educations", "lab"):
                batch_op.add_column(sa.Column("lab", sa.String(length=255), nullable=False, server_default=""))

    bind = op.get_bind()
    insp = sa.inspect(bind)

    if _has_table(insp, "experiences"):
        with op.batch_alter_table("experiences", schema=None) as batch_op:
            if not _has_column(insp, "experiences", "advisor"):
                batch_op.add_column(sa.Column("advisor", sa.String(length=255), nullable=False, server_default=""))
            if not _has_column(insp, "experiences", "skills_json"):
                batch_op.add_column(
                    sa.Column("skills_json", sa.JSON(), nullable=False, server_default=sa.text("'[]'"))
                )
            if not _has_column(insp, "experiences", "impact_summary"):
                batch_op.add_column(sa.Column("impact_summary", sa.Text(), nullable=False, server_default=""))

    bind = op.get_bind()
    insp = sa.inspect(bind)

    if not _has_table(insp, "publications"):
        op.create_table(
            "publications",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("profile_id", sa.Integer(), sa.ForeignKey("profiles.id", ondelete="CASCADE"), nullable=False),
            sa.Column("title", sa.Text(), nullable=False),
            sa.Column("venue", sa.String(length=255), nullable=False, server_default=""),
            sa.Column("publication_year", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("status", sa.String(length=80), nullable=False, server_default=""),
            sa.Column("doi", sa.String(length=255), nullable=False, server_default=""),
            sa.Column("url", sa.String(length=800), nullable=False, server_default=""),
            sa.Column("authors_json", sa.JSON(), nullable=False, server_default=sa.text("'[]'")),
            sa.Column("contribution", sa.Text(), nullable=False, server_default=""),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        )
    _ensure_index("publications", "ix_publications_profile_id", ["profile_id"])

    if not _has_table(insp, "awards_honors"):
        op.create_table(
            "awards_honors",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("profile_id", sa.Integer(), sa.ForeignKey("profiles.id", ondelete="CASCADE"), nullable=False),
            sa.Column("title", sa.String(length=255), nullable=False),
            sa.Column("issuer", sa.String(length=255), nullable=False, server_default=""),
            sa.Column("award_year", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("details", sa.Text(), nullable=False, server_default=""),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        )
    _ensure_index("awards_honors", "ix_awards_honors_profile_id", ["profile_id"])

    if not _has_table(insp, "conference_presentations"):
        op.create_table(
            "conference_presentations",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("profile_id", sa.Integer(), sa.ForeignKey("profiles.id", ondelete="CASCADE"), nullable=False),
            sa.Column("name", sa.String(length=255), nullable=False),
            sa.Column("event_year", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("role", sa.String(length=120), nullable=False, server_default=""),
            sa.Column("details", sa.Text(), nullable=False, server_default=""),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        )
    _ensure_index("conference_presentations", "ix_conference_presentations_profile_id", ["profile_id"])

    if not _has_table(insp, "teaching_mentoring"):
        op.create_table(
            "teaching_mentoring",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("profile_id", sa.Integer(), sa.ForeignKey("profiles.id", ondelete="CASCADE"), nullable=False),
            sa.Column("role", sa.String(length=255), nullable=False),
            sa.Column("organization", sa.String(length=255), nullable=False, server_default=""),
            sa.Column("term", sa.String(length=120), nullable=False, server_default=""),
            sa.Column("start_date", sa.Date(), nullable=True),
            sa.Column("end_date", sa.Date(), nullable=True),
            sa.Column("details", sa.Text(), nullable=False, server_default=""),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        )
    _ensure_index("teaching_mentoring", "ix_teaching_mentoring_profile_id", ["profile_id"])

    if not _has_table(insp, "service_outreach"):
        op.create_table(
            "service_outreach",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("profile_id", sa.Integer(), sa.ForeignKey("profiles.id", ondelete="CASCADE"), nullable=False),
            sa.Column("role", sa.String(length=255), nullable=False, server_default=""),
            sa.Column("organization", sa.String(length=255), nullable=False, server_default=""),
            sa.Column("event_name", sa.String(length=255), nullable=False, server_default=""),
            sa.Column("event_year", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("details", sa.Text(), nullable=False, server_default=""),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        )
    _ensure_index("service_outreach", "ix_service_outreach_profile_id", ["profile_id"])

    if not _has_table(insp, "additional_projects"):
        op.create_table(
            "additional_projects",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("profile_id", sa.Integer(), sa.ForeignKey("profiles.id", ondelete="CASCADE"), nullable=False),
            sa.Column("title", sa.String(length=255), nullable=False),
            sa.Column("summary", sa.Text(), nullable=False, server_default=""),
            sa.Column("skills_json", sa.JSON(), nullable=False, server_default=sa.text("'[]'")),
            sa.Column("impact", sa.Text(), nullable=False, server_default=""),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        )
    _ensure_index("additional_projects", "ix_additional_projects_profile_id", ["profile_id"])

    if not _has_table(insp, "cv_import_runs"):
        op.create_table(
            "cv_import_runs",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("profile_id", sa.Integer(), sa.ForeignKey("profiles.id", ondelete="CASCADE"), nullable=False),
            sa.Column("input_format", sa.String(length=40), nullable=False, server_default="latex"),
            sa.Column("scope", sa.String(length=40), nullable=False, server_default="all"),
            sa.Column("status", sa.String(length=40), nullable=False, server_default="created"),
            sa.Column("warnings_json", sa.JSON(), nullable=False, server_default=sa.text("'[]'")),
            sa.Column("raw_text_hash", sa.String(length=64), nullable=False, server_default=""),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        )
    _ensure_index("cv_import_runs", "ix_cv_import_runs_profile_id", ["profile_id"])

    if not _has_table(insp, "cv_import_items"):
        op.create_table(
            "cv_import_items",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("import_run_id", sa.Integer(), sa.ForeignKey("cv_import_runs.id", ondelete="CASCADE"), nullable=False),
            sa.Column("profile_id", sa.Integer(), sa.ForeignKey("profiles.id", ondelete="CASCADE"), nullable=False),
            sa.Column("section", sa.String(length=120), nullable=False),
            sa.Column("item_key", sa.String(length=255), nullable=False, server_default=""),
            sa.Column("payload_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
            sa.Column("created_question_hash", sa.String(length=64), nullable=False, server_default=""),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        )
    _ensure_index("cv_import_items", "ix_cv_import_items_import_run_id", ["import_run_id"])
    _ensure_index("cv_import_items", "ix_cv_import_items_profile_id", ["profile_id"])


def downgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)

    if _has_table(insp, "cv_import_items"):
        idxs = {idx["name"] for idx in insp.get_indexes("cv_import_items")}
        if "ix_cv_import_items_profile_id" in idxs:
            op.drop_index("ix_cv_import_items_profile_id", table_name="cv_import_items")
        if "ix_cv_import_items_import_run_id" in idxs:
            op.drop_index("ix_cv_import_items_import_run_id", table_name="cv_import_items")
        op.drop_table("cv_import_items")

    bind = op.get_bind()
    insp = sa.inspect(bind)
    if _has_table(insp, "cv_import_runs"):
        idxs = {idx["name"] for idx in insp.get_indexes("cv_import_runs")}
        if "ix_cv_import_runs_profile_id" in idxs:
            op.drop_index("ix_cv_import_runs_profile_id", table_name="cv_import_runs")
        op.drop_table("cv_import_runs")

    bind = op.get_bind()
    insp = sa.inspect(bind)
    if _has_table(insp, "additional_projects"):
        idxs = {idx["name"] for idx in insp.get_indexes("additional_projects")}
        if "ix_additional_projects_profile_id" in idxs:
            op.drop_index("ix_additional_projects_profile_id", table_name="additional_projects")
        op.drop_table("additional_projects")

    bind = op.get_bind()
    insp = sa.inspect(bind)
    if _has_table(insp, "service_outreach"):
        idxs = {idx["name"] for idx in insp.get_indexes("service_outreach")}
        if "ix_service_outreach_profile_id" in idxs:
            op.drop_index("ix_service_outreach_profile_id", table_name="service_outreach")
        op.drop_table("service_outreach")

    bind = op.get_bind()
    insp = sa.inspect(bind)
    if _has_table(insp, "teaching_mentoring"):
        idxs = {idx["name"] for idx in insp.get_indexes("teaching_mentoring")}
        if "ix_teaching_mentoring_profile_id" in idxs:
            op.drop_index("ix_teaching_mentoring_profile_id", table_name="teaching_mentoring")
        op.drop_table("teaching_mentoring")

    bind = op.get_bind()
    insp = sa.inspect(bind)
    if _has_table(insp, "conference_presentations"):
        idxs = {idx["name"] for idx in insp.get_indexes("conference_presentations")}
        if "ix_conference_presentations_profile_id" in idxs:
            op.drop_index("ix_conference_presentations_profile_id", table_name="conference_presentations")
        op.drop_table("conference_presentations")

    bind = op.get_bind()
    insp = sa.inspect(bind)
    if _has_table(insp, "awards_honors"):
        idxs = {idx["name"] for idx in insp.get_indexes("awards_honors")}
        if "ix_awards_honors_profile_id" in idxs:
            op.drop_index("ix_awards_honors_profile_id", table_name="awards_honors")
        op.drop_table("awards_honors")

    bind = op.get_bind()
    insp = sa.inspect(bind)
    if _has_table(insp, "publications"):
        idxs = {idx["name"] for idx in insp.get_indexes("publications")}
        if "ix_publications_profile_id" in idxs:
            op.drop_index("ix_publications_profile_id", table_name="publications")
        op.drop_table("publications")

    bind = op.get_bind()
    insp = sa.inspect(bind)
    if _has_table(insp, "experiences"):
        with op.batch_alter_table("experiences", schema=None) as batch_op:
            if _has_column(insp, "experiences", "impact_summary"):
                batch_op.drop_column("impact_summary")
            if _has_column(insp, "experiences", "skills_json"):
                batch_op.drop_column("skills_json")
            if _has_column(insp, "experiences", "advisor"):
                batch_op.drop_column("advisor")

    bind = op.get_bind()
    insp = sa.inspect(bind)
    if _has_table(insp, "educations"):
        with op.batch_alter_table("educations", schema=None) as batch_op:
            if _has_column(insp, "educations", "lab"):
                batch_op.drop_column("lab")
            if _has_column(insp, "educations", "advisor"):
                batch_op.drop_column("advisor")
            if _has_column(insp, "educations", "thesis_title"):
                batch_op.drop_column("thesis_title")

    bind = op.get_bind()
    insp = sa.inspect(bind)
    if _has_table(insp, "profile_answers"):
        with op.batch_alter_table("profile_answers", schema=None) as batch_op:
            if _has_column(insp, "profile_answers", "evidence_json"):
                batch_op.drop_column("evidence_json")
            if _has_column(insp, "profile_answers", "source_section"):
                batch_op.drop_column("source_section")
            if _has_column(insp, "profile_answers", "verification_state"):
                batch_op.drop_column("verification_state")
            if _has_column(insp, "profile_answers", "source"):
                batch_op.drop_column("source")

    bind = op.get_bind()
    insp = sa.inspect(bind)
    if _has_table(insp, "question_bank"):
        with op.batch_alter_table("question_bank", schema=None) as batch_op:
            if _has_column(insp, "question_bank", "is_cv_derived"):
                batch_op.drop_column("is_cv_derived")
            if _has_column(insp, "question_bank", "importance"):
                batch_op.drop_column("importance")
            if _has_column(insp, "question_bank", "section"):
                batch_op.drop_column("section")
