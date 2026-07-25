"""Add immutable v1.7 speech-pipeline lineage records.

Revision ID: 0013_v170_speech_pipeline
Revises: 0012_report_runtime_fields
Create Date: 2026-07-25
"""

from alembic import op
import sqlalchemy as sa


revision = "0013_v170_speech_pipeline"
down_revision = "0012_report_runtime_fields"
branch_labels = None
depends_on = None


def _lineage_columns() -> list[sa.Column]:
    return [
        sa.Column("record_key", sa.String(length=256), primary_key=True),
        sa.Column("organization_id", sa.String(length=64), sa.ForeignKey("organizations.organization_id"), nullable=False),
        sa.Column("session_id", sa.String(length=64), sa.ForeignKey("sessions.session_id"), nullable=False),
    ]


def upgrade() -> None:
    op.add_column("audio_files", sa.Column("source_asset_version", sa.Integer(), server_default="1", nullable=False))
    op.add_column("audio_files", sa.Column("current_normalized_asset_version", sa.Integer(), nullable=True))
    op.add_column("audio_files", sa.Column("current_normalized_checksum_sha256", sa.String(length=64), nullable=True))
    op.create_index(
        "ix_audio_files_current_normalized_checksum_sha256",
        "audio_files",
        ["current_normalized_checksum_sha256"],
    )

    op.add_column("transcripts", sa.Column("asr_profile", sa.JSON(), nullable=True))
    op.add_column("transcripts", sa.Column("asr_provenance", sa.JSON(), nullable=True))
    op.add_column("transcripts", sa.Column("raw_speaker_labels", sa.JSON(), server_default="[]", nullable=False))
    op.add_column("transcripts", sa.Column("speech_pipeline_payload", sa.JSON(), server_default="{}", nullable=False))

    for name, type_ in (
        ("speaker_mapping_id", sa.String(length=128)),
        ("speaker_mapping_version", sa.Integer()),
        ("attestation_id", sa.String(length=128)),
        ("attestation_version", sa.Integer()),
        ("chat_export_id", sa.String(length=128)),
        ("chat_export_version", sa.Integer()),
        ("tokenizer_profile_id", sa.String(length=128)),
        ("tokenizer_profile_version", sa.Integer()),
        ("tokenizer_profile_checksum_sha256", sa.String(length=64)),
    ):
        op.add_column("feature_sets", sa.Column(name, type_, nullable=True))
    for name in ("speaker_mapping_id", "attestation_id", "chat_export_id", "tokenizer_profile_id"):
        op.create_index(f"ix_feature_sets_{name}", "feature_sets", [name])
    op.create_index(
        "ix_feature_sets_tokenizer_profile_checksum_sha256",
        "feature_sets",
        ["tokenizer_profile_checksum_sha256"],
    )

    op.create_table(
        "normalized_audio_assets",
        *_lineage_columns(),
        sa.Column("source_audio_file_id", sa.String(length=64), sa.ForeignKey("audio_files.audio_file_id"), nullable=False),
        sa.Column("source_asset_version", sa.Integer(), nullable=False),
        sa.Column("asset_version", sa.Integer(), nullable=False),
        sa.Column("source_checksum_sha256", sa.String(length=64), nullable=False),
        sa.Column("normalized_checksum_sha256", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("source_audio_file_id", "asset_version", name="uq_normalized_audio_assets_source_version"),
    )
    op.create_index("ix_normalized_audio_assets_organization_id", "normalized_audio_assets", ["organization_id"])
    op.create_index("ix_normalized_audio_assets_session_id", "normalized_audio_assets", ["session_id"])
    op.create_index("ix_normalized_audio_assets_source_audio_file_id", "normalized_audio_assets", ["source_audio_file_id"])
    op.create_index("ix_normalized_audio_assets_source_checksum_sha256", "normalized_audio_assets", ["source_checksum_sha256"])
    op.create_index("ix_normalized_audio_assets_normalized_checksum_sha256", "normalized_audio_assets", ["normalized_checksum_sha256"])
    op.create_index("ix_normalized_audio_assets_status", "normalized_audio_assets", ["status"])

    _create_transcript_artifact_table(
        "speaker_mappings",
        "mapping_id",
        "mapping_version",
        "uq_speaker_mappings_id_version",
        extra_columns=[],
    )
    _create_transcript_artifact_table(
        "transcript_attestations",
        "attestation_id",
        "attestation_version",
        "uq_transcript_attestations_id_version",
        extra_columns=[
            sa.Column("speaker_mapping_id", sa.String(length=128), nullable=False),
            sa.Column("speaker_mapping_version", sa.Integer(), nullable=False),
        ],
    )
    _create_transcript_artifact_table(
        "limitation_acknowledgments",
        "acknowledgment_id",
        "acknowledgment_version",
        "uq_limitation_acknowledgments_id_version",
        extra_columns=[
            sa.Column("limitation_code", sa.String(length=128), nullable=False),
            sa.Column("validator_version", sa.String(length=128), nullable=False),
        ],
    )
    _create_transcript_artifact_table(
        "chat_exports",
        "export_id",
        "export_version",
        "uq_chat_exports_id_version",
        extra_columns=[
            sa.Column("canonical_checksum_sha256", sa.String(length=64), nullable=False),
            sa.Column(
                "source_audio_file_id",
                sa.String(length=64),
                sa.ForeignKey("audio_files.audio_file_id"),
                nullable=False,
            ),
            sa.Column("source_asset_version", sa.Integer(), nullable=False),
            sa.Column("source_checksum_sha256", sa.String(length=64), nullable=False),
            sa.Column("normalized_asset_version", sa.Integer(), nullable=False),
            sa.Column("normalized_checksum_sha256", sa.String(length=64), nullable=False),
            sa.Column("round_trip_status", sa.String(length=32), nullable=False),
        ],
    )
    _create_transcript_artifact_table(
        "findings_results",
        "findings_id",
        "findings_version",
        "uq_findings_results_id_version",
        extra_columns=[
            sa.Column("speaker_mapping_id", sa.String(length=128), nullable=False),
            sa.Column("speaker_mapping_version", sa.Integer(), nullable=False),
            sa.Column("attestation_id", sa.String(length=128), nullable=False),
            sa.Column("attestation_version", sa.Integer(), nullable=False),
            sa.Column("chat_export_id", sa.String(length=128), nullable=False),
            sa.Column("chat_export_version", sa.Integer(), nullable=False),
            sa.Column(
                "source_audio_file_id",
                sa.String(length=64),
                sa.ForeignKey("audio_files.audio_file_id"),
                nullable=False,
            ),
            sa.Column("source_asset_version", sa.Integer(), nullable=False),
            sa.Column("source_checksum_sha256", sa.String(length=64), nullable=False),
            sa.Column("normalized_asset_version", sa.Integer(), nullable=False),
            sa.Column("normalized_checksum_sha256", sa.String(length=64), nullable=False),
            sa.Column("chat_export_checksum_sha256", sa.String(length=64), nullable=False),
            sa.Column("algorithm_checksum_sha256", sa.String(length=64), nullable=False),
            sa.Column("tokenizer_profile_id", sa.String(length=128), nullable=True),
            sa.Column("tokenizer_profile_version", sa.Integer(), nullable=True),
            sa.Column("tokenizer_profile_checksum_sha256", sa.String(length=64), nullable=True),
            sa.Column("feature_schema_version", sa.String(length=128), nullable=False),
        ],
    )


def _create_transcript_artifact_table(
    table_name: str,
    resource_id: str,
    version: str,
    constraint_name: str,
    *,
    extra_columns: list[sa.Column],
) -> None:
    op.create_table(
        table_name,
        *_lineage_columns(),
        sa.Column(resource_id, sa.String(length=128), nullable=False),
        sa.Column(version, sa.Integer(), nullable=False),
        sa.Column("transcript_id", sa.String(length=64), sa.ForeignKey("transcripts.transcript_id"), nullable=False),
        sa.Column("transcript_version", sa.Integer(), nullable=False),
        *extra_columns,
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint(resource_id, version, name=constraint_name),
    )
    op.create_index(f"ix_{table_name}_organization_id", table_name, ["organization_id"])
    op.create_index(f"ix_{table_name}_session_id", table_name, ["session_id"])
    op.create_index(f"ix_{table_name}_{resource_id}", table_name, [resource_id])
    op.create_index(f"ix_{table_name}_transcript_id", table_name, ["transcript_id"])
    op.create_index(f"ix_{table_name}_status", table_name, ["status"])
    if table_name == "transcript_attestations":
        op.create_index("ix_transcript_attestations_speaker_mapping_id", table_name, ["speaker_mapping_id"])
    elif table_name == "limitation_acknowledgments":
        op.create_index("ix_limitation_acknowledgments_limitation_code", table_name, ["limitation_code"])
        op.create_index("ix_limitation_acknowledgments_validator_version", table_name, ["validator_version"])
    elif table_name == "chat_exports":
        op.create_index("ix_chat_exports_canonical_checksum_sha256", table_name, ["canonical_checksum_sha256"])
        op.create_index("ix_chat_exports_round_trip_status", table_name, ["round_trip_status"])
        for column_name in (
            "source_audio_file_id",
            "source_checksum_sha256",
            "normalized_asset_version",
            "normalized_checksum_sha256",
        ):
            op.create_index(f"ix_chat_exports_{column_name}", table_name, [column_name])
    elif table_name == "findings_results":
        op.create_index("ix_findings_results_feature_schema_version", table_name, ["feature_schema_version"])
        for column_name in (
            "speaker_mapping_id",
            "speaker_mapping_version",
            "attestation_id",
            "attestation_version",
            "chat_export_id",
            "chat_export_version",
            "source_audio_file_id",
            "source_asset_version",
            "source_checksum_sha256",
            "normalized_asset_version",
            "normalized_checksum_sha256",
            "chat_export_checksum_sha256",
            "algorithm_checksum_sha256",
            "tokenizer_profile_id",
            "tokenizer_profile_version",
            "tokenizer_profile_checksum_sha256",
        ):
            op.create_index(
                f"ix_findings_results_{column_name}",
                table_name,
                [column_name],
            )


def downgrade() -> None:
    for table_name in (
        "findings_results",
        "chat_exports",
        "limitation_acknowledgments",
        "transcript_attestations",
        "speaker_mappings",
        "normalized_audio_assets",
    ):
        op.drop_table(table_name)
    for name in (
        "speaker_mapping_id",
        "attestation_id",
        "chat_export_id",
        "tokenizer_profile_id",
        "tokenizer_profile_checksum_sha256",
    ):
        op.drop_index(f"ix_feature_sets_{name}", table_name="feature_sets")
    for name in (
        "tokenizer_profile_checksum_sha256",
        "tokenizer_profile_version",
        "tokenizer_profile_id",
        "chat_export_version",
        "chat_export_id",
        "attestation_version",
        "attestation_id",
        "speaker_mapping_version",
        "speaker_mapping_id",
    ):
        op.drop_column("feature_sets", name)
    op.drop_column("transcripts", "raw_speaker_labels")
    op.drop_column("transcripts", "speech_pipeline_payload")
    op.drop_column("transcripts", "asr_provenance")
    op.drop_column("transcripts", "asr_profile")
    op.drop_index(
        "ix_audio_files_current_normalized_checksum_sha256",
        table_name="audio_files",
    )
    op.drop_column("audio_files", "current_normalized_checksum_sha256")
    op.drop_column("audio_files", "current_normalized_asset_version")
    op.drop_column("audio_files", "source_asset_version")
