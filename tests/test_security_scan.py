from pathlib import Path


def test_secret_scanner_blocks_committed_high_risk_tokens(tmp_path):
    from scripts.security_scan import scan_paths

    risky = tmp_path / "service.py"
    token = "sk-" + "proj-" + "abcdefghijklmnopqrstuvwxyz0123456789"
    risky.write_text(
        f'OPENAI_API_KEY = "{token}"\n',
        encoding="utf-8",
    )

    findings = scan_paths([risky])

    assert findings
    assert findings[0].relative_path == str(risky)
    assert "OpenAI API key" in findings[0].message
    assert "sk-proj" not in findings[0].message


def test_security_workflow_runs_secret_and_dependency_scans():
    workflow = Path(".github/workflows/deploy.yml").read_text(encoding="utf-8")

    assert "python scripts/security_scan.py" in workflow
    assert "npm audit --audit-level=high" in workflow
    assert "pip-audit" in workflow
