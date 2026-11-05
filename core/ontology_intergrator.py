import os
import xml.etree.ElementTree as ET

P1 = 'http'
P2 = '://'
RDF_NS = f'{P1}{P2}www.w3.org/1999/02/22-rdf-syntax-ns#'
RDFS_NS = f'{P1}{P2}www.w3.org/2000/01/rdf-schema#'
OWL_NS = f'{P1}{P2}www.w3.org/2002/07/owl#'
BASE_URI = f'{P1}{P2}omaker.org/ontology/medical#'

TYPE_MAP = {
    'DRUG': 'Medicamento',
    'SYMPTOM': 'Sintoma',
    'DISEASE': 'Doenca'
}

def build_owl_ontology(triplets, output_file='omaker_generated.owl'):
    print(' Iniciar integrador de ontologias OMAKER...')
    
    ET.register_namespace('rdf', RDF_NS)
    ET.register_namespace('rdfs', RDFS_NS)
    ET.register_namespace('owl', OWL_NS)

    root = ET.Element(f'{{{RDF_NS}}}RDF')

    onto_header = ET.SubElement(root, f'{{{OWL_NS}}}Ontology')
    onto_header.set(f'{{{RDF_NS}}}about', BASE_URI)

    classes = ['EntidadeBiomedica', 'Medicamento', 'Sintoma', 'Doenca']
    for cname in classes:
        cls_elem = ET.SubElement(root, f'{{{OWL_NS}}}Class')
        cls_elem.set(f'{{{RDF_NS}}}about', f'{BASE_URI}{cname}')
        if cname != 'EntidadeBiomedica':
            sub_elem = ET.SubElement(cls_elem, f'{{{RDFS_NS}}}subClassOf')
            sub_elem.set(f'{{{RDF_NS}}}resource', f'{BASE_URI}EntidadeBiomedica')

    properties = ['trata', 'causa', 'previne']
    for pname in properties:
        prop_elem = ET.SubElement(root, f'{{{OWL_NS}}}ObjectProperty')
        prop_elem.set(f'{{{RDF_NS}}}about', f'{BASE_URI}{pname}')

    created_individuals = {}

    def get_or_create_individual(name, ent_type):
        safe_name = name.replace(' ', '_').capitalize()
        if safe_name in created_individuals:
            return created_individuals[safe_name]
        
        cls_name = TYPE_MAP.get(ent_type.upper(), 'EntidadeBiomedica')
        ind_elem = ET.SubElement(root, f'{{{OWL_NS}}}NamedIndividual')
        ind_elem.set(f'{{{RDF_NS}}}about', f'{BASE_URI}{safe_name}')
        
        type_elem = ET.SubElement(ind_elem, f'{{{RDF_NS}}}type')
        type_elem.set(f'{{{RDF_NS}}}resource', f'{BASE_URI}{cls_name}')
        
        created_individuals[safe_name] = ind_elem
        return ind_elem

    added_axioms = 0
    for sub_name, sub_type, rel, obj_name, obj_type, conf in triplets:
        if rel == 'no_relation' or rel not in properties:
            continue

        sub_elem = get_or_create_individual(sub_name, sub_type)
        obj_elem = get_or_create_individual(obj_name, obj_type)
        obj_id = obj_name.replace(' ', '_').capitalize()

        rel_elem = ET.SubElement(sub_elem, f'{{{BASE_URI}}}{rel}')
        rel_elem.set(f'{{{RDF_NS}}}resource', f'{BASE_URI}{obj_id}')
        
        print(f'  Axioma inserido: {sub_name} --[{rel}]--> {obj_name} (Confianca: {conf:.2%})')
        added_axioms += 1

    tree = ET.ElementTree(root)
    tree.write(output_file, encoding='utf-8', xml_declaration=True)

    print(f'Ontologia OWL gerada com sucesso: {output_file} ({added_axioms} axiomas inseridos).')
    return output_file

if __name__ == '__main__':
    triplets_demo = [
        ('Paracetamol', 'DRUG', 'trata', 'febre', 'SYMPTOM', 0.985),
        ('Aspirina', 'DRUG', 'previne', 'infarto', 'DISEASE', 0.962),
        ('Ibuprofeno', 'DRUG', 'trata', 'inflamacao', 'SYMPTOM', 0.941)
    ]
    build_owl_ontology(triplets_demo, 'omaker_generated.owl')
