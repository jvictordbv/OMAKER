"""Builds an OWL/RDF-XML ontology from (subject, type, relation, object, type, confidence) triples."""
import xml.etree.ElementTree as ET
from urllib.parse import quote

from core.labels import ENTITY_TYPES, NO_RELATION, REL2ID

RDF_NS = "http://www.w3.org/1999/02/22-rdf-syntax-ns#"
RDFS_NS = "http://www.w3.org/2000/01/rdf-schema#"
OWL_NS = "http://www.w3.org/2002/07/owl#"
BASE_URI = "http://omaker.org/ontology/medical#"

TYPE_MAP = {"DRUG": "Drug", "SYMPTOM": "Symptom", "DISEASE": "Disease", "GENE": "Gene"}
ROOT_CLASS = "BiomedicalEntity"
PROPERTIES = [r for r in REL2ID if r != NO_RELATION]  # treats, causes, prevents
# Only 'treats' and 'prevents' are restricted to drugs; 'causes' also holds for diseases/symptoms.
PROPERTY_DOMAIN = {"treats": "Drug", "prevents": "Drug"}


def _iri(name: str) -> str:
    return BASE_URI + quote(name.strip().replace(" ", "_"), safe="_-")


def build_owl_ontology(triplets, output_file="omaker_generated.owl", log=print):
    ET.register_namespace("rdf", RDF_NS)
    ET.register_namespace("rdfs", RDFS_NS)
    ET.register_namespace("owl", OWL_NS)
    ET.register_namespace("omaker", BASE_URI)

    root = ET.Element(f"{{{RDF_NS}}}RDF")
    ET.SubElement(root, f"{{{OWL_NS}}}Ontology").set(f"{{{RDF_NS}}}about", BASE_URI.rstrip("#"))

    for cname in [ROOT_CLASS] + [TYPE_MAP[t] for t in ENTITY_TYPES]:
        cls = ET.SubElement(root, f"{{{OWL_NS}}}Class")
        cls.set(f"{{{RDF_NS}}}about", BASE_URI + cname)
        if cname != ROOT_CLASS:
            ET.SubElement(cls, f"{{{RDFS_NS}}}subClassOf").set(f"{{{RDF_NS}}}resource", BASE_URI + ROOT_CLASS)

    for pname in PROPERTIES:
        prop = ET.SubElement(root, f"{{{OWL_NS}}}ObjectProperty")
        prop.set(f"{{{RDF_NS}}}about", BASE_URI + pname)
        if pname in PROPERTY_DOMAIN:
            ET.SubElement(prop, f"{{{RDFS_NS}}}domain").set(f"{{{RDF_NS}}}resource", BASE_URI + PROPERTY_DOMAIN[pname])
        ET.SubElement(prop, f"{{{RDFS_NS}}}range").set(f"{{{RDF_NS}}}resource", BASE_URI + ROOT_CLASS)

    individuals = {}  # canonical key (lowercase) -> element

    def get_individual(name, etype):
        key = " ".join(name.lower().split())
        if key in individuals:
            return individuals[key]
        el = ET.SubElement(root, f"{{{OWL_NS}}}NamedIndividual")
        el.set(f"{{{RDF_NS}}}about", _iri(key))
        ET.SubElement(el, f"{{{RDF_NS}}}type").set(
            f"{{{RDF_NS}}}resource", BASE_URI + TYPE_MAP.get(etype.upper(), ROOT_CLASS)
        )
        ET.SubElement(el, f"{{{RDFS_NS}}}label").text = name.strip()  # original spelling preserved
        individuals[key] = el
        return el

    seen, added = set(), 0
    for sub, sub_t, rel, obj, obj_t, conf in triplets:
        if rel not in PROPERTIES:
            continue
        key = (" ".join(sub.lower().split()), rel, " ".join(obj.lower().split()))
        if key in seen:
            continue
        seen.add(key)
        sub_el = get_individual(sub, sub_t)
        get_individual(obj, obj_t)
        ET.SubElement(sub_el, f"{{{BASE_URI}}}{rel}").set(f"{{{RDF_NS}}}resource", _iri(key[2]))
        log(f"  Axiom: {sub} --[{rel}]--> {obj} (confidence: {conf:.2%})")
        added += 1

    tree = ET.ElementTree(root)
    ET.indent(tree)
    tree.write(output_file, encoding="utf-8", xml_declaration=True)
    log(f"OWL ontology written to {output_file} ({added} axioms).")
    return output_file


if __name__ == "__main__":
    demo = [
        ("Paracetamol", "DRUG", "treats", "fever", "SYMPTOM", 0.985),
        ("Aspirin", "DRUG", "prevents", "myocardial infarction", "DISEASE", 0.962),
    ]
    build_owl_ontology(demo, "omaker_generated.owl")
