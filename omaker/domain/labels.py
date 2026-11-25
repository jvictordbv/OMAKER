"""Shared constants for the OMAKER relation-extraction pipeline.

Everything that must stay identical between training, inference and the OWL
export lives here, so there is a single source of truth.
"""

# Encoder (English). Change it here and nowhere else.
# The revisions are Hugging Face commits: a new upload by the model's author does not change OMAKER.
# Changing a model means changing its revision too (the "sha" of https://huggingface.co/api/models/<name>).
MODEL_NAME = "SpanBERT/spanbert-base-cased"
MODEL_REVISION = "b436fe68816aa04256692ce7e27711bf6be15513"

# Biomedical NER used to find entities in raw text.
NER_MODEL_NAME = "d4data/biomedical-ner-all"
NER_MODEL_REVISION = "015a4050c9ac99722e61c547aa9b4282bcbedc7f"

# Entity types. Every (S|O) x type marker is generated from this list.
ENTITY_TYPES = ("DRUG", "SYMPTOM", "DISEASE", "GENE")

# Relation labels. Order defines the class ids: changing it invalidates checkpoints.
REL2ID = {
    "treats": 0,
    "causes": 1,
    "prevents": 2,
    "no_relation": 3,
}
ID2REL = {v: k for k, v in REL2ID.items()}
NO_RELATION = "no_relation"

# Which (subject_type, object_type) pairs are worth classifying.
ALLOWED_TYPE_PAIRS = {
    ("DRUG", "SYMPTOM"),
    ("DRUG", "DISEASE"),
    ("DISEASE", "SYMPTOM"),
    ("SYMPTOM", "DISEASE"),
}

# Minimum confidence to keep a predicted triple.
DEFAULT_CONFIDENCE_THRESHOLD = 0.70

DEFAULT_CHECKPOINT = "omaker_pure.pt"


def marker_tokens():
    """All typed entity markers: <S:DRUG>, </S:DRUG>, <O:DRUG>, ..."""
    tokens = []
    for role in ("S", "O"):
        for etype in ENTITY_TYPES:
            tokens.append(f"<{role}:{etype}>")
            tokens.append(f"</{role}:{etype}>")
    return tokens


# OWL layer (kept here so importing the engine does not require owlready2)
ROOT_CLASS = "BiomedicalEntity"
BASE_CLASSES = {"DRUG": "Drug", "SYMPTOM": "Symptom", "DISEASE": "Disease", "GENE": "Gene"}
# relation -> required subject base class (None = unrestricted)
RELATION_DOMAIN = {"treats": "Drug", "prevents": "Drug", "causes": None}
