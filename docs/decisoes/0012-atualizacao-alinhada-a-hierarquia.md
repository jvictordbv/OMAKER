# 0012. Atualização alinhada à hierarquia da ontologia externa

- **Status:** Aceita
- **Data:** 2026-11-12
- **Decidido por:** Gustavo

## Contexto

O Atualizador acrescenta entidades e relações a uma ontologia que já existe, por exemplo a Symptom Ontology (`omaker/resources/symp.owl`). A revisão de 2026-11-09 mostrou que, ao atualizar uma cópia da `symp.owl`, o OMAKER criava `http://purl.obolibrary.org/obo/symp.owl#Drug` e as demais classes-base dentro do namespace da SYMP, ao lado da hierarquia de sintomas que ela já tem. "Nausea" virava indivíduo de uma classe Symptom paralela, e não da classe `nausea` da própria SYMP. Além disso, o `AllDisjoint` entre classes-base era aplicado também a classes da ontologia alheia.

## Decisão

- Quando a ontologia aberta não foi gerada pelo OMAKER (`is_external`), as entidades são encaixadas nas classes que ela já tem.
- O casamento é exato, depois de normalizar (minúsculas, espaços e `_` iguais), por `rdfs:label`, `oboInOwl:hasExactSynonym` e nome da classe (`build_label_index`, `aligned_class`).
- Classes obsoletas (`owl:deprecated`) são ignoradas.
- Uma classe só é usada se estiver no ramo do tipo da entidade: um DRUG nunca vira instância de um sintoma.
- As subclasses propostas pelo LLM também reaproveitam uma classe existente com o mesmo rótulo.
- O que não existe na ontologia externa (Drug, Disease, a raiz, as propriedades e os indivíduos) é criado no namespace do OMAKER, `http://www.mestrado.edu/ontologias/omaker#`.
- O `AllDisjoint` vale só entre classes do OMAKER.
- Ontologias novas, geradas pelo OMAKER, saem como antes.

## Alternativas consideradas

- **Manter o comportamento anterior.** Produz uma ontologia consistente para o raciocinador, mas com duas hierarquias para a mesma coisa, o que derrota o propósito de atualizar uma ontologia de referência.
- **Casamento aproximado (por semelhança de texto ou de vetores).** Não foi implementado nesta versão: um casamento errado põe a entidade na classe errada sem aviso, o que é pior do que criar um indivíduo na classe-base.

## Consequências

### Positivas

- Na `symp.owl`, "nausea" vira indivíduo da classe `nausea`, "back pain" vira indivíduo de `backache` (sinônimo exato), e a subclasse "Pain" proposta pelo LLM é o próprio `pain` da SYMP.
- Ponta a ponta numa cópia da `symp.owl`, com o HermiT real: ontologia consistente, sem `symp.owl#Drug`, recurso original intacto.
- Atualizar duas vezes dá o mesmo resultado, inclusive depois de salvar e reabrir.

### Negativas e riscos

- O casamento exato perde variações: "nauseas", "back-pain" ou uma grafia diferente viram indivíduos da classe-base do OMAKER, fora da hierarquia da SYMP.
- O alinhamento depende de a ontologia externa ter rótulos e sinônimos em inglês ([0001](0001-pipeline-em-ingles.md)).
- A ontologia atualizada mistura dois namespaces, o da fonte e o do OMAKER, o que precisa ser explicado a quem a abre no Protégé.

## Referências

- `omaker/ontology/alignment.py` (`is_external`, `build_label_index`, `aligned_class`), `omaker/ontology/builder.py`.
- Testes: `tests/test_alignment.py::test_symp_update_reuses_symptom_and_has_no_parallel_classes`, `tests/test_alignment.py::test_instance_typed_by_exact_synonym`, `tests/test_alignment.py::test_match_outside_entity_branch_is_ignored`, `tests/test_alignment.py::test_reused_class_not_in_alldisjoint`, `tests/test_alignment.py::test_idempotent_after_save_and_reload`.
- [PR #6](https://github.com/jvictordbv/OMAKER/pull/6) (alinhamento), [PR #7](https://github.com/jvictordbv/OMAKER/pull/7) (`AllDisjoint` não repetido a cada atualização).
- Notas internas do projeto: revisão do código de 2026-11-09 (item 9).
