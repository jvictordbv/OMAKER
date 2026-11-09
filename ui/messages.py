"""Texts shown to the user after building an ontology. Pure functions, no Qt."""
from __future__ import annotations

from core.hybrid_engine import OntologyResult
from core.owl_builder import ReasonerStatus


def completion_message(result: OntologyResult) -> tuple[str, str, str]:
    """Returns (nivel, titulo, texto); nivel is "info" or "warning". Never claims a validation
    that did not happen."""
    detalhe = f"Arquivo salvo em: {result.path}\nRelações novas: {result.relations_added}"
    if result.reasoner is ReasonerStatus.CONSISTENT:
        return ("info", "Ontologia concluída",
                f"Grafo gerado e validado pelo raciocinador HermiT: nenhuma contradição lógica encontrada.\n\n{detalhe}")
    if result.reasoner is ReasonerStatus.INCONSISTENT:
        return ("warning", "Ontologia inconsistente",
                "O raciocinador HermiT detectou que a ontologia é inconsistente. O arquivo foi salvo, "
                f"mas precisa de revisão.\n\n{detalhe}")
    return ("warning", "Ontologia gerada sem validação",
            "O grafo foi gerado, mas não foi validado: o raciocinador HermiT não pôde ser executado "
            f"(verifique se o Java está instalado).\n\n{detalhe}")
