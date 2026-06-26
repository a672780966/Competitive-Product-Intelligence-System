"""P0 Reality Alignment — Tests against overclaim.

Verifies that documentation and API endpoints accurately represent the
current system state (mock/stub mode) and do not claim AI-powered
capabilities that are not yet implemented.
"""

from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)

# Project root for doc file checks
PROJECT_ROOT = Path(__file__).resolve().parents[2]


def _read(path_relative: str) -> str:
    """Read a file relative to the project root."""
    return (PROJECT_ROOT / path_relative).read_text(encoding="utf-8")


# ── API endpoint tests ──────────────────────────────────────────────


def test_provider_status_endpoint_exists():
    """The /api/v1/system/provider-status endpoint must exist and return 200."""
    r = client.get("/api/v1/system/provider-status")
    assert r.status_code == 200
    data = r.json()
    assert "current_search_provider" in data
    assert "current_llm_provider" in data
    assert "is_mock_mode" in data


def test_provider_status_shows_expected_defaults():
    """By default LLM_PROVIDER=stub and SEARCH_PROVIDER=duckduckgo."""
    r = client.get("/api/v1/system/provider-status")
    data = r.json()
    assert data["current_llm_provider"] == "stub"
    assert data["current_search_provider"] == "duckduckgo"


def test_provider_status_has_collector_runtimes():
    """The collector_runtimes block must be present and contain direct_http."""
    r = client.get("/api/v1/system/provider-status")
    data = r.json()
    assert "collector_runtimes" in data
    assert "direct_http" in data["collector_runtimes"]
    assert data["collector_runtimes"]["direct_http"]["enabled"] is True


def test_provider_status_has_llm_details():
    """LLM provider details must include the expected fields."""
    r = client.get("/api/v1/system/provider-status")
    data = r.json()
    llm = data["llm_provider_details"]
    assert "configured" in llm
    assert "has_api_key" in llm
    assert "has_base_url" in llm
    assert "has_model" in llm


def test_provider_status_has_search_details():
    """Search provider details must include the expected fields."""
    r = client.get("/api/v1/system/provider-status")
    data = r.json()
    search = data["search_provider_details"]
    assert "configured" in search
    assert "real_available" in search
    assert "duckduckgo_verified" in search


def test_provider_status_reports_duckduckgo_unverified():
    """DuckDuckGo is listed as code-ready but marked unverified."""
    r = client.get("/api/v1/system/provider-status")
    data = r.json()
    assert data["search_provider_details"]["duckduckgo_verified"] is False


# ── Documentation overclaim tests ───────────────────────────────────


def test_readme_no_overclaim_ai_powered():
    """Verify README does not claim AI-powered as if real.

    The hero section and core descriptions should reflect the actual
    state (Mock/Stub/Provider-Ready mode).
    """
    content = _read("README.md")
    # Should reference stub/mock/provider-ready rather than claiming AI-driven
    assert (
        "Stub/Mock" in content
        or "Mock Mode" in content
        or "Stub Mode" in content
        or "Provider-Ready" in content
    ), (
        "README.md must contain 'Stub/Mock', 'Mock Mode', 'Stub Mode',"
        " or 'Provider-Ready' indicating the current state"
    )


def test_readme_no_false_ai_driven_claim():
    """The hero section should not claim AI-driven capabilities as real."""
    content = _read("README.md")
    # The phrase "AI 驱动的" should not appear in the hero context
    assert "AI 驱动的竞品信息自动采集" not in content, (
        "README.md hero section still claims 'AI 驱动的竞品信息自动采集'"
    )


def test_release_notes_no_overclaim():
    """RELEASE_NOTES.md should mention stub or pending status."""
    content = _read("release/RELEASE_NOTES.md")
    assert "stub" in content.lower() or "pending" in content.lower(), (
        "RELEASE_NOTES.md must mention 'stub' or 'pending' state"
    )


def test_release_notes_no_ai_powered():
    """RELEASE_NOTES.md should not claim AI-powered extraction as real."""
    content = _read("release/RELEASE_NOTES.md")
    assert "AI-Powered Structured Extraction" not in content, (
        "RELEASE_NOTES.md still claims 'AI-Powered Structured Extraction'"
    )


def test_changelog_no_ai_powered_discovery():
    """CHANGELOG.md should not claim 'AI-powered discovery'."""
    content = _read("release/CHANGELOG.md")
    assert "AI-powered discovery" not in content, (
        "CHANGELOG.md still claims 'AI-powered discovery'"
    )


def test_discovery_page_has_mock_indicator():
    """DiscoveryPage.tsx must include a mock-mode indicator for the user."""
    content = _read("frontend/src/features/discovery/DiscoveryPage.tsx")
    assert "Mock Mode" in content or "mock" in content.lower(), (
        "DiscoveryPage.tsx must contain 'Mock Mode' or 'mock' indicator"
    )


def test_english_readme_no_overclaim():
    """English README should reflect current mock/stub state."""
    content = _read("docs/README.en.md")
    assert "Stub" in content or "Mock" in content, (
        "docs/README.en.md must reference stub or mock mode"
    )


def test_japanese_readme_no_overclaim():
    """Japanese README should reflect current mock/stub state."""
    content = _read("docs/README.ja.md")
    assert "Mock" in content or "Stub" in content, (
        "docs/README.ja.md must reference mock or stub mode"
    )


def test_korean_readme_no_overclaim():
    """Korean README should reflect current mock/stub state."""
    content = _read("docs/README.ko.md")
    assert "Mock" in content or "Stub" in content, (
        "docs/README.ko.md must reference mock or stub mode"
    )
