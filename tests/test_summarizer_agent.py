import pytest
from pathlib import Path
from veronica import Assistant, AssistantConfig
from veronica.local_ai import LocalAIBackend

def make_assistant(tmp_path: Path) -> Assistant:
    return Assistant(
        AssistantConfig(data_dir=tmp_path),
        ai_backend=LocalAIBackend(),
    )

def test_summarizer_agent_trigger_and_parsing(tmp_path: Path, monkeypatch) -> None:
    assistant = make_assistant(tmp_path)

    # Mock response object for requests.get
    class FakeResponse:
        status_code = 200
        text = """
        <html>
            <head><title>Test Article</title></head>
            <body>
                <header>Navigation Bar Content</header>
                <main>
                    <h1>The Future of Local AI</h1>
                    <p>Veronica is an assistant running completely locally. It is designed to be extensible and private.</p>
                </main>
                <footer>Footer links & copy</footer>
            </body>
        </html>
        """

    class FakeRequests:
        @staticmethod
        def get(url, headers=None, timeout=None):
            assert "example.com" in url
            return FakeResponse()

    # Apply mock
    monkeypatch.setattr("veronica.summarizer_agent._optional_module", lambda name: FakeRequests if name == "requests" else None)

    # Execute request
    response = assistant.respond("summarize URL https://example.com/local-ai")

    # Assertions
    assert "Web Summary (example.com)" in response
    assert "Veronica is an assistant running completely locally." in response
    assert "Navigation Bar Content" not in response  # Stripped header
    assert "Footer links" not in response  # Stripped footer

def test_summarizer_invalid_url(tmp_path: Path) -> None:
    assistant = make_assistant(tmp_path)
    response = assistant.respond("summarize URL invalid-url-no-dot")
    assert "Invalid URL" in response
