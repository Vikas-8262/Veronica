import pytest
from pathlib import Path
from veronica import Assistant, AssistantConfig
from veronica.local_ai import LocalAIBackend

def make_assistant(tmp_path: Path) -> Assistant:
    return Assistant(
        AssistantConfig(data_dir=tmp_path),
        ai_backend=LocalAIBackend(),
    )

def test_email_agent_missing_credentials(tmp_path: Path, monkeypatch) -> None:
    assistant = make_assistant(tmp_path)
    
    # Ensure credentials are deleted in this test context
    monkeypatch.delenv("EMAIL_USER", raising=False)
    monkeypatch.delenv("EMAIL_PASS", raising=False)
    
    resp = assistant.respond("send email to test@example.com with subject Hello")
    assert "requires EMAIL_USER and EMAIL_PASS" in resp

def test_email_agent_send_and_read_mocked(tmp_path: Path, monkeypatch) -> None:
    assistant = make_assistant(tmp_path)
    
    monkeypatch.setenv("EMAIL_USER", "sender@gmail.com")
    monkeypatch.setenv("EMAIL_PASS", "app-password-123")
    
    # Mock SMTP_SSL
    smtp_instances = []
    class MockSMTP:
        def __init__(self, host, port):
            self.host = host
            self.port = port
            smtp_instances.append(self)
        def login(self, user, password):
            self.user = user
            self.password = password
        def send_message(self, msg):
            self.msg = msg
        def quit(self):
            pass

    # Mock IMAP4_SSL
    imap_instances = []
    class MockIMAP:
        def __init__(self, host):
            self.host = host
            imap_instances.append(self)
        def login(self, user, password):
            self.user = user
            self.password = password
        def select(self, folder):
            self.folder = folder
        def search(self, charset, criteria):
            assert criteria == 'UNSEEN'
            # Returns search tuple
            return "OK", [b"1 2"]
        def fetch(self, e_id, format):
            # Return a simple mock email data
            import email.message
            msg = email.message.EmailMessage()
            msg["Subject"] = f"Test Mail {e_id.decode()}"
            msg["From"] = "friend@gmail.com"
            msg.set_content("Hi there!")
            return "OK", [(None, msg.as_bytes())]
        def logout(self):
            pass

    monkeypatch.setattr("veronica.email_agent.smtplib.SMTP_SSL", MockSMTP)
    monkeypatch.setattr("veronica.email_agent.imaplib.IMAP4_SSL", MockIMAP)
    
    # 1. Test Send Email
    send_resp = assistant.respond("send email to target@gmail.com subject Great news body Project is successful")
    assert "successfully" in send_resp.lower()
    assert len(smtp_instances) == 1
    assert smtp_instances[0].user == "sender@gmail.com"
    assert smtp_instances[0].msg["To"] == "target@gmail.com"
    assert smtp_instances[0].msg["Subject"] == "Great news"
    
    # 2. Test Check / Read Email
    read_resp = assistant.respond("check inbox")
    assert "friend@gmail.com" in read_resp
    assert "Test Mail 2" in read_resp
