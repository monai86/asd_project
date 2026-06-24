from pathlib import Path


def test_backup_restore_runbook_defines_rpo_rto_and_drills():
    runbook = Path("docs/BACKUP_RESTORE_RUNBOOK.md").read_text(encoding="utf-8")

    assert "RPO: 15 minutes" in runbook
    assert "RTO: 4 hours" in runbook
    assert "python scripts/check_api_migrations.py" in runbook
    assert "restore drill" in runbook.lower()
    assert "audit" in runbook.lower()
