from core.hybrid_engine import OntologyResult
from core.owl_builder import ReasonerStatus
from ui.messages import completion_message


def test_completion_message_never_claims_validation_when_unavailable():
    nivel, titulo, texto = completion_message(OntologyResult("x.owl", ReasonerStatus.UNAVAILABLE, 3))
    assert nivel == "warning" and "não foi validad" in texto and "x.owl" in texto


def test_completion_message_consistent():
    nivel, _, texto = completion_message(OntologyResult("x.owl", ReasonerStatus.CONSISTENT, 3))
    assert nivel == "info" and "validad" in texto


def test_completion_message_inconsistent():
    nivel, _, texto = completion_message(OntologyResult("x.owl", ReasonerStatus.INCONSISTENT, 3))
    assert nivel == "warning" and "inconsisten" in texto
