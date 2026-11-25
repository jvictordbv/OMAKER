"""RNF-09: o OMAKER roda e grava arquivos em pastas cujo caminho tem acentos."""
import tomllib
from pathlib import Path

from omaker.ontology import builder as owl_builder
from omaker.pipeline.engine import HybridEngine

ROOT = Path(__file__).resolve().parents[1]


def test_project_is_not_installed_in_editable_mode():
    """Um .pth de instalação editável seria lido em cp1252 pelo Python 3.12 do Windows e quebraria com acentos."""
    pyproject = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    assert pyproject["tool"]["uv"]["package"] is False


def test_ontology_is_generated_and_updated_in_a_folder_with_accents(tmp_path, monkeypatch, sample_extraction):
    tax, triples = sample_extraction
    folder = tmp_path / "Projetos" / "acadêmicos" / "ação e coração"
    monkeypatch.setattr(owl_builder, "run_reasoner", lambda *a, **k: owl_builder.ReasonerStatus.UNAVAILABLE)

    first = HybridEngine.construir(tax, triples, "ontologia_é", str(folder), "http://t.org/", lambda _m: None)
    assert Path(first.path) == folder / "ontologia_é.owl" and Path(first.path).is_file()

    _world, onto = owl_builder.load_world_ontology(first.path)   # recarrega pelo caminho com acentos
    assert {i.label[0] for i in onto.individuals()} >= {"Aspirin", "stroke", "tumor"}

    monkeypatch.setattr(HybridEngine, "extrair", staticmethod(lambda *a, **k: (tax, triples)))
    second = HybridEngine.atualizar_ontologia(first.path, "texto", lambda _m: None)
    assert second.path == first.path and second.relations_added == 0   # nada novo: as triplas já estavam lá
    assert list(folder.glob("ontologia_é.backup-*.owl"))


def test_checkpoint_is_downloaded_to_a_folder_with_accents(tmp_path):
    import hashlib

    from omaker.relations import download as dl

    body = b"pesos " * 100

    class Resp:
        status_code, headers = 200, {"Content-Length": str(len(body))}

        def raise_for_status(self):
            pass

        def iter_content(self, _n):
            return iter([body])

        def __enter__(self):
            return self

        def __exit__(self, *exc):
            return False

    class Session:
        def get(self, *a, **k):
            return Resp()

    dest = tmp_path / "acadêmicos" / "modelos" / "omaker_pure.pt"
    dl.download_file("http://x/m.pt", dest, hashlib.sha256(body).hexdigest(), session=Session())
    assert dest.read_bytes() == body and not dl.partial_path(dest).exists()
