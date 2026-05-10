import tts.tts as module


class FakeStream:
    def __init__(self, engines, language):
        self.engines = engines
        self.language = language
        self.fed = []
        self.played = False
        self.stopped = False

    def feed(self, text):
        self.fed.append(text)

    def play_async(self):
        self.played = True

    def is_playing(self):
        return True

    def stop(self):
        self.stopped = True


def test_tts_uses_piper_when_mpv_is_missing(monkeypatch) -> None:
    created = {}

    monkeypatch.setattr(
        module,
        "_find_executable",
        lambda name: "C:/Dev/WavyOS/.venv/Scripts/piper.exe" if name == "piper" else None,
    )
    monkeypatch.setattr(module, "_load_piper_voice_model", lambda: None)
    monkeypatch.setattr(module, "EdgeEngine", lambda: created.setdefault("edge", object()))
    monkeypatch.setattr(module, "GTTSEngine", lambda voice: created.setdefault("gtts", object()))
    monkeypatch.setattr(module, "GTTSVoice", lambda **kwargs: object())
    monkeypatch.setattr(module, "PiperVoice", lambda path: ("voice", path))
    monkeypatch.setattr(
        module,
        "PiperEngine",
        lambda *, piper_path, voice: created.setdefault(
            "piper",
            ("piper", piper_path, voice),
        ),
    )
    monkeypatch.setattr(module, "TextToAudioStream", FakeStream)

    tts = module.TTS()

    assert "edge" not in created
    assert "gtts" not in created
    assert created["piper"][1].endswith("piper.exe")
    assert tts.stream.engines == [created["piper"]]


def test_tts_play_and_stop_noop_without_available_engines(monkeypatch) -> None:
    monkeypatch.setattr(module, "_load_realtime_tts", lambda: True)
    monkeypatch.setattr(module, "_find_executable", lambda name: None)

    tts = module.TTS()
    tts.play("hello")
    tts.stop()

    assert tts.stream is None
