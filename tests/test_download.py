import hashlib

import pytest
import torch

from omaker.relations import download as dl

PAYLOAD = b"pesos do modelo " * 1000
SHA = hashlib.sha256(PAYLOAD).hexdigest()


def _chunks(body, n, fail):
    for i in range(0, len(body), n):
        yield body[i:i + n]
    if fail:
        raise ConnectionError("a conexão caiu")


class FakeResponse:
    def __init__(self, status, body, fail=False):
        self.status_code, self._body, self._fail = status, body, fail
        self.headers = {"Content-Length": str(len(body))}

    def raise_for_status(self):
        if self.status_code >= 400:
            raise RuntimeError(f"HTTP {self.status_code}")

    def iter_content(self, chunk_size):
        return _chunks(self._body, chunk_size, self._fail)

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


class FakeSession:
    """Serve PAYLOAD; com Range, só o resto (206). Com fail_after, a primeira resposta cai no meio."""

    def __init__(self, fail_after=None):
        self.ranges, self.fail_after = [], fail_after

    def get(self, url, headers=None, stream=True, timeout=None):
        start = int((headers or {}).get("Range", "bytes=0-")[6:-1] or 0)
        self.ranges.append(start)
        body, fail = PAYLOAD[start:], False
        if self.fail_after is not None:
            body, fail, self.fail_after = body[:self.fail_after], True, None
        return FakeResponse(206 if start else 200, body, fail)


def test_download_verifies_and_renames(tmp_path):
    dest = tmp_path / "m" / "omaker_pure.pt"
    seen = []
    dl.download_file("http://x/m.pt", dest, SHA, progress=seen.append, session=FakeSession())
    assert dest.read_bytes() == PAYLOAD and not dl.partial_path(dest).exists()
    assert seen[-1] == pytest.approx(1.0)


def test_download_resumes_after_a_drop(tmp_path):
    dest = tmp_path / "omaker_pure.pt"
    session = FakeSession(fail_after=5000)
    with pytest.raises(ConnectionError):
        dl.download_file("http://x/m.pt", dest, SHA, session=session)
    assert dl.partial_path(dest).stat().st_size == 5000
    dl.download_file("http://x/m.pt", dest, SHA, session=session)
    assert session.ranges == [0, 5000] and dest.read_bytes() == PAYLOAD


def test_download_rejects_a_wrong_hash(tmp_path):
    dest = tmp_path / "omaker_pure.pt"
    with pytest.raises(ValueError, match="sha256"):
        dl.download_file("http://x/m.pt", dest, "0" * 64, session=FakeSession())
    assert not dest.exists() and not dl.partial_path(dest).exists()


def test_ensure_skips_when_disabled_or_present(tmp_path, monkeypatch):
    dest = tmp_path / "omaker_pure.pt"
    monkeypatch.setenv("OMAKER_NO_DOWNLOAD", "1")
    assert dl.ensure_pure_checkpoint(dest, lambda _m: None) is False
    dest.write_bytes(b"x")
    assert dl.ensure_pure_checkpoint(dest, lambda _m: None) is True


def test_ensure_downloads_model_and_calibration(tmp_path, monkeypatch):
    monkeypatch.delenv("OMAKER_NO_DOWNLOAD", raising=False)
    calls = []

    def fake_download(url, dest, sha256, progress=None, session=None):
        calls.append((url, dest.name, sha256))
        dest.write_bytes(b"ok")

    monkeypatch.setattr(dl, "download_file", fake_download)
    monkeypatch.setattr(dl, "_sha256", lambda _p: dl.PURE_MODEL["sha256"])   # o arquivo falso faz papel do publicado
    assert dl.ensure_pure_checkpoint(tmp_path / "omaker_pure.pt", lambda _m: None) is True
    assert [c[1] for c in calls] == ["omaker_pure.pt", "omaker_pure.calibration.json"]
    assert calls[0][2] == dl.PURE_MODEL["sha256"]


def test_ensure_reports_failure_without_raising(tmp_path, monkeypatch):
    monkeypatch.delenv("OMAKER_NO_DOWNLOAD", raising=False)

    def boom(*a, **k):
        raise ConnectionError("sem internet")

    monkeypatch.setattr(dl, "download_file", boom)
    logs = []
    assert dl.ensure_pure_checkpoint(tmp_path / "omaker_pure.pt", logs.append) is False
    assert any("sem internet" in line for line in logs)


def test_export_strips_training_texts(tmp_path):
    from omaker.relations import release
    from omaker.relations.data import text_fingerprint

    run = tmp_path / "run"
    run.mkdir()
    torch.save({"state_dict": {"w": torch.zeros(2)}, "model_name": "m", "rel2id": {}, "entity_types": [],
                "train_texts": ["Aspirin prevents stroke."]}, run / "model.pt")
    (run / "model.calibration.json").write_text('{"temperature": 2.0, "threshold": 0.4}', encoding="utf-8")
    out = release.export(run, tmp_path / "dist")
    ckpt = torch.load(out["checkpoint"], map_location="cpu", weights_only=True)
    assert "train_texts" not in ckpt and ckpt["train_text_hashes"] == [text_fingerprint("Aspirin prevents stroke.")]
    assert (tmp_path / "dist" / "omaker_pure.calibration.json").is_file()
    assert out["sha256"] == hashlib.sha256(out["checkpoint"].read_bytes()).hexdigest()
    assert out["sha256"] in (tmp_path / "dist" / "SHA256SUMS").read_text(encoding="utf-8")
    assert b"\r" not in (tmp_path / "dist" / "SHA256SUMS").read_bytes()   # sha256sum -c lê no Linux


def test_published_hashes_are_filled_in():
    import re
    for key in ("sha256", "calibration_sha256"):
        assert re.fullmatch(r"[0-9a-f]{64}", dl.PURE_MODEL[key]), key


def _published_model(tmp_path, monkeypatch, sha=None):
    """Checkpoint já baixado (sem a calibração) e downloads falsos registrados em calls."""
    monkeypatch.delenv("OMAKER_NO_DOWNLOAD", raising=False)
    dest = tmp_path / "omaker_pure.pt"
    dest.write_bytes(b"pesos")
    monkeypatch.setattr(dl, "_sha256", lambda _p: sha or dl.PURE_MODEL["sha256"])
    calls = []
    monkeypatch.setattr(dl, "download_file", lambda url, d, sha256, progress=None, session=None:
                        calls.append(d.name) or d.write_bytes(b"{}"))
    return dest, calls


def test_missing_calibration_of_the_published_model_is_downloaded_again(tmp_path, monkeypatch):
    """Se a calibração falhou numa vez anterior, a próxima execução baixa só ela."""
    dest, calls = _published_model(tmp_path, monkeypatch)
    assert dl.ensure_pure_checkpoint(dest, lambda _m: None) is True
    assert calls == ["omaker_pure.calibration.json"]


def test_calibration_is_not_downloaded_for_another_model(tmp_path, monkeypatch):
    """Um checkpoint próprio não recebe a calibração do modelo publicado."""
    dest, calls = _published_model(tmp_path, monkeypatch, sha="f" * 64)
    assert dl.ensure_pure_checkpoint(dest, lambda _m: None) is True
    assert calls == []


def test_calibration_failure_keeps_the_model_and_says_so(tmp_path, monkeypatch):
    dest, _calls = _published_model(tmp_path, monkeypatch)

    def boom(url, d, sha256, progress=None, session=None):
        raise ConnectionError("sem internet")

    monkeypatch.setattr(dl, "download_file", boom)
    logs = []
    assert dl.ensure_pure_checkpoint(dest, logs.append) is True   # o PURE roda, sem calibração
    assert any("without calibration" in line and "sem internet" in line for line in logs), logs
