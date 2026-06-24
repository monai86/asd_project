import pytest

from app.services.notification_safety import NotificationSafetyError, sanitize_notification_text, validate_notification


def test_notification_safety_allows_generic_operational_message():
    notification = validate_notification(
        subject="Transcript review is ready",
        body="A transcript draft is ready for review in the clinical workspace.",
    )

    assert notification.subject == "Transcript review is ready"
    assert notification.body == "A transcript draft is ready for review in the clinical workspace."


@pytest.mark.parametrize(
    ("body", "blocked_term"),
    [
        ("Case C-CHILD-SECRET is ready.", "C-CHILD-SECRET"),
        ("Transcript line: CHI: I want blue truck.", "CHI:"),
        ("Audio file child_real_name_session.wav uploaded.", "child_real_name_session.wav"),
        ("Storage key sessions/case-1/audio.raw failed.", "sessions/case-1/audio.raw"),
        ("Contact guardian@example.com about this report.", "guardian@example.com"),
    ],
)
def test_notification_safety_blocks_clinical_or_identifier_content(body, blocked_term):
    with pytest.raises(NotificationSafetyError) as error:
        validate_notification(subject="Workspace update", body=body)

    assert blocked_term not in str(error.value)


def test_notification_sanitizer_replaces_sensitive_content_without_echoing_it():
    text = "Case C-CHILD-SECRET transcript CHI: I want car at sessions/case-1/audio.raw"

    sanitized = sanitize_notification_text(text)

    assert "C-CHILD-SECRET" not in sanitized
    assert "CHI:" not in sanitized
    assert "sessions/case-1/audio.raw" not in sanitized
    assert "[redacted]" in sanitized
