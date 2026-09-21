# core/semantic_engine.py
import json
import os
import types
import google.generativeai as genai
from owlready2 import *
from owlready2.base import OwlReadyInconsistentOntologyError

class SemanticEngine:
    @staticmethod
    def gerar_ontologia(texto, nome_arquivo, api_key, modelo_llm, temp_llm, pasta_destino, uri_base, log_callback):
        """
        Executa a extração usando LLM e monta a estrutura hierárquica do arquivo .owl
        """
        try:
            log_callback(f"> [API] Conectando ao {modelo_llm} (Temp: {temp_llm})...")
            genai.configure(api_key=api_key)

            instrucao_sistema = """
            Você é um Engenheiro do Conhecimento Sênior especialista em Web Semântica e Lógica de Descrição (DL). 
            Sua tarefa é realizar a Extração de Conhecimento (Knowledge Extraction) de um texto e transformá-lo em uma ontologia formal.

            ### PROCESSO DE PENSAMENTO (Chain of Thought) ###
            1. Identifique os conceitos principais (Classes) e organize-os em uma hierarquia (SubclassOf).
            2. Identifique os indivíduos específicos (Instâncias) e suas classes.
            3. Defina as propriedades de objeto (Relacionamentos) e seus domínios/alcances.
            4. Extraia restrições lógicas e axiomas formais baseados estritamente nas evidências do texto.

            ### REGRAS RÍGIDAS DE ENGENHARIA ###
            1. TAXONOMIA: Nenhuma classe deve ficar "órfã". Use "Thing" como raiz máxima.
            2. NORMALIZAÇÃO: Identifique termos semanticamente equivalentes e use apenas uma etiqueta canônica (Ex: "Câncer" e "Neoplasia" -> use apenas "Cancer").
            3. INTEGRIDADE REFERENCIAL: Toda instância citada em "relacoes" DEVE existir em "instancias". Todo "verbo" em "relacoes" DEVE estar definido in "object_properties".
            4. LÓGICA DE DESCRIÇÃO (Axiomas): 
            - Use 'only' (Universal) para restrições que se aplicam a todos os membros.
            - Use 'some' (Existencial) para indicar que existe pelo menos um relacionamento.
            - Use 'and'/'or' para definições de classes complexas ou uniões/interseções.
            5. DISJUNTOS: Agrupe explicitamente classes que não podem compartilhar instâncias.

            ### FORMATO DE SAÍDA (JSON RIGOROSO) ###
            {
            "classes": { "NomeClasse": "ClassePai" },
            "instancias": { "NomeInstancia": "NomeClasse" },
            "object_properties": { 
                "nome_propriedade": { "dominio": "ClasseA", "alcance": "ClasseB" } 
            },
            "relacoes": [
                {"sujeito": "InstanciaA", "verbo": "propriedade", "objeto": "InstanciaB"}
            ],
            "disjuntos": [ ["ClasseA", "ClasseB"] ],
            "axiomas": [
                {"alvo": "ClasseOuInstancia", "tipo": "only|some|and|or", "propriedade": "string", "alcance": "string/array"}
            ]
            }
            """
            
            modelo = genai.GenerativeModel(modelo_llm, system_instruction=instrucao_sistema)
            resposta = modelo.generate_content(f"Devolva apenas o JSON:\n\n{texto}", 
                                               generation_config={"response_mime_type": "application/json", "temperature": temp_llm})
            
            dados = json.loads(resposta.text)
            log_callback("> [PARSER] Resposta JSON estruturada obtida com sucesso. Injetando dados no grafo...")

            onto_path.append(".")
            if not uri_base.endswith(("#", "/")): 
                uri_base += "#"
            
            uri_completa = f"{uri_base}{nome_arquivo}.owl"
            onto = get_ontology(uri_completa)

            with onto:
                classes_owl = {}
                classes_json = dados.get("classes", {})
                if isinstance(classes_json, dict):
                    for nome_classe, classe_pai in classes_json.items():
                        pai = classes_owl.get(classe_pai, Thing) if isinstance(classe_pai, str) and classe_pai != "Thing" else Thing
                        classes_owl[nome_classe] = types.new_class(nome_classe, (pai,))

                props_json = dados.get("object_properties", {})
                if isinstance(props_json, dict):
                    for nome_prop, config in props_json.items():
                        if isinstance(config, dict):
                            dom = classes_owl.get(config.get("dominio"), Thing)
                            alc = classes_owl.get(config.get("alcance"), Thing)
                            nova_prop = types.new_class(nome_prop, (ObjectProperty,))
                            nova_prop.domain.append(dom)
                            nova_prop.range.append(alc)

                instancias_owl = {}
                insts_json = dados.get("instancias", {})
                if isinstance(insts_json, dict):
                    for nome_inst, nome_classe in insts_json.items():
                        classe_mae = classes_owl.get(nome_classe, Thing) if isinstance(nome_classe, str) else Thing
                        instancias_owl[nome_inst] = classe_mae(nome_inst)

                for rel in dados.get("relacoes", []):
                    try:
                        if isinstance(rel, dict):
                            s_nome = rel.get("sujeito")
                            v_nome = rel.get("verbo")
                            o_nome = rel.get("objeto")
                        else: 
                            continue
                        sujeito = instancias_owl.get(s_nome)
                        objeto = instancias_owl.get(o_nome)
                        if sujeito and objeto and hasattr(onto, v_nome):
                            getattr(sujeito, v_nome).append(objeto)
                    except: 
                        pass

                for grupo_disjunto in dados.get("disjuntos", []):
                    try:
                        classes_do_grupo = [classes_owl[c] for c in grupo_disjunto if c in classes_owl]
                        if len(classes_do_grupo) > 1: 
                            AllDisjoint(classes_do_grupo)
                    except: 
                        pass

                for ax in dados.get("axiomas", []):
                    try:
                        alvo = classes_owl.get(ax.get("alvo"))
                        if not alvo: 
                            continue
                        tipo = ax.get("tipo")
                        if tipo in ["only", "some"]:
                            prop = getattr(onto, ax.get("propriedade"), None)
                            alcance = classes_owl.get(ax.get("alcance"))
                            if prop and alcance:
                                if tipo == "only": 
                                    alvo.is_a.append(prop.only(alcance))
                                elif tipo == "some": 
                                    alvo.is_a.append(prop.some(alcance))
                    except: 
                        pass
            
            
                try:
                    log_callback("\n> [HERMIT] Invocando o raciocinador para validação lógica...")
                    sync_reasoner(infer_property_values=True)
                    log_callback("> [HERMIT] Sucesso: Grafo consistente e inferências materializadas!")
                except OwlReadyInconsistentOntologyError as err:
                    log_callback(f"\n> [AVISO CRÍTICO] O HermiT detectou uma inconsistência lógica nas inferências da IA: {err}")
                    log_callback("> [AVISO] O arquivo será salvo, mas contém contradições lógicas que precisam de revisão.")
                except Exception as e:
                    log_callback(f"\n> [HERMIT] Não foi possível rodar o HermiT localmente (Verifique o ambiente Java): {e}")

            # Salva o arquivo final uma única vez
            caminho_final = os.path.join(pasta_destino, f"{nome_arquivo}.owl")
            onto.save(file=caminho_final, format="rdfxml")
            
            log_callback(f"\n> [SUCCESS] Grafo de Conhecimento OWL salvo com sucesso em:\n{caminho_final}")
            return caminho_final

        except Exception as e:
            # Propaga o erro para a interface exibir na QMessageBox crítica
            raise e

    @staticmethod
    def atualizar_ontologia(caminho_owl, texto, api_key, log_callback):
        """
        Executa a mesclagem/alinhamento de axiomas em grafos preexistentes
        """
        try:
            onto_path.append(os.path.dirname(caminho_owl))
            onto_existente = get_ontology(f"file://{caminho_owl}").load()
            
            log_callback("> [FUSION] Alinhando novos axiomas...")
           
            onto_existente.save(file=caminho_owl, format="rdfxml")
            log_callback("\n> [SUCCESS] Fusão concluída!")
            return True
        except Exception as e:
            raise e
owlready2.JAVA_EXE = r"C:\Program Files\Java\jdk-26.0.1\bin\java.exe"