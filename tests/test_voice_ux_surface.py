from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_browser_voice_ux_surface_and_parity_doc():
    voice = (ROOT / "frontend/src/voice.ts").read_text()
    controls = (ROOT / "frontend/src/VoiceControls.tsx").read_text()
    main = (ROOT / "frontend/src/main.tsx").read_text()
    parity = (ROOT / "docs/cursor-audit/FEATURE_PARITY.md").read_text()
    assert "detectSpeechCapability" in voice
    assert "humanConnectionStatus" in voice
    assert "Web Speech API" in voice
    assert "Voice playback unavailable" in voice
    assert "DictationButton" in controls and "SpeakReplyButton" in controls
    assert "Start dictation" in controls or "Dictate" in controls
    assert "DictationButton" in main and "SpeakReplyButton" in main
    assert "Refresh connection status" in main
    assert "Status guide" in main
    assert "Partial" in parity and "Voice" in parity
    assert "realtime" in parity.lower() or "duplex" in parity.lower()
