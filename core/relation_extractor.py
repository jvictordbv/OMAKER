import torch
import torch.nn as nn
from transformers import AutoTokenizer, AutoModel

class RelationExtractorPURE(nn.Module):
    """
    Módulo de Extração de Relações para o OMAKER baseado na arquitetura PURE.
    Utiliza Typed Entity Markers e codificação contextual (SpanBERT/BioBERT).
    """
    def __init__(self, model_name: str = "SpanBERT/spanbert-base-cased", num_relations: int = 10):
        super(RelationExtractorPURE, self).__init__()
        self.tokenizer = AutoTokenizer.from_pretrained(model_name)
        self.encoder = AutoModel.from_pretrained(model_name, use_safetensors=True)

        # Marcadores de entidade tipados (Typed Entity Markers - PURE)
        self.special_tokens = [
            "<S:DRUG>", "</S:DRUG>", "<O:SYMPTOM>", "</O:SYMPTOM>",
            "<S:DISEASE>", "</S:DISEASE>", "<O:DISEASE>", "</O:DISEASE>",
            "<S:GENE>", "</S:GENE>", "<O:GENE>", "</O:GENE>"
        ]
        self.tokenizer.add_special_tokens({'additional_special_tokens': self.special_tokens})
        self.encoder.resize_token_embeddings(len(self.tokenizer))

        hidden_size = self.encoder.config.hidden_size

        # Concatenação da representação do par de marcadores [h_sujeito; h_objeto]
        self.classifier = nn.Sequential(
            nn.Linear(hidden_size * 2, hidden_size),
            nn.ReLU(),
            nn.Dropout(0.1),
            nn.Linear(hidden_size, num_relations)
        )

    def format_input_with_markers(self, text: str, sub_span: tuple, sub_type: str, obj_span: tuple, obj_type: str) -> str:
        """
        Insere marcadores tipados ao redor das entidades sujeito e objeto no texto.
        Exemplo: "O <S:DRUG> Paracetamol </S:DRUG> alivia a <O:SYMPTOM> febre </O:SYMPTOM>."
        """
        s_start, s_end = sub_span
        o_start, o_end = obj_span

        m_s_open, m_s_close = f"<S:{sub_type.upper()}>", f"</S:{sub_type.upper()}>"
        m_o_open, m_o_close = f"<O:{obj_type.upper()}>", f"</O:{obj_type.upper()}>"

        if s_start < o_start:
            formatted = (text[:s_start] + f"{m_s_open} " + text[s_start:s_end] + f" {m_s_close}" +
                         text[s_end:o_start] + f"{m_o_open} " + text[o_start:o_end] + f" {m_o_close}" + text[o_end:])
        else:
            formatted = (text[:o_start] + f"{m_o_open} " + text[o_start:o_end] + f" {m_o_close}" +
                         text[o_end:s_start] + f"{m_s_open} " + text[s_start:s_end] + f" {m_s_close}" + text[s_end:])

        return formatted

    def extract_relation_triple(self, text: str, sub_name: str, sub_type: str, obj_name: str, obj_type: str, relation_labels: list):
        """
        Executa a inferência para um par de entidades no texto de um artigo e retorna o tripleto.
        """
        # Busca insensível a maiúsculas/minúsculas para evitar erro de substring
        s_start = text.lower().find(sub_name.lower())
        o_start = text.lower().find(obj_name.lower())

        if s_start == -1 or o_start == -1:
            print(f"⚠️ Aviso: '{sub_name}' ou '{obj_name}' não foi encontrado no texto fornecido.")
            return None, 0.0

        sub_span = (s_start, s_start + len(sub_name))
        obj_span = (o_start, o_start + len(obj_name))

        # 1. Formata o texto com marcadores de posição e tipo
        formatted_text = self.format_input_with_markers(text, sub_span, sub_type, obj_span, obj_type)
        inputs = self.tokenizer(formatted_text, return_tensors="pt")

        # 2. Passagem pelo encoder contextual (SpanBERT)
        with torch.no_grad():
            outputs = self.encoder(**inputs)
            sequence_output = outputs.last_hidden_state

        # 3. Localização dos vetores dos marcadores
        tokens = self.tokenizer.convert_ids_to_tokens(inputs["input_ids"][0])
        s_marker, o_marker = f"<S:{sub_type.upper()}>", f"<O:{obj_type.upper()}>"

        s_idx = tokens.index(s_marker) if s_marker in tokens else 1
        o_idx = tokens.index(o_marker) if o_marker in tokens else len(tokens) - 2

        sub_emb = sequence_output[0, s_idx, :]
        obj_emb = sequence_output[0, o_idx, :]

        # 4. Concatenação e classificação
        pair_rep = torch.cat([sub_emb, obj_emb], dim=-1).unsqueeze(0)
        pair_rep = pair_rep.to(dtype=next(self.classifier.parameters()).dtype)

        logits = self.classifier(pair_rep)
        probs = torch.softmax(logits, dim=-1)
        pred_idx = torch.argmax(probs, dim=-1).item()

        relation_name = relation_labels[pred_idx] if pred_idx < len(relation_labels) else "no_relation"
        return (sub_name, relation_name, obj_name), probs[0, pred_idx].item()


if __name__ == "__main__":
    print("🚀 Testando o RelationExtractorPURE no OMAKER...")

    # 1. Instancia o extrator com SpanBERT
    extrator = RelationExtractorPURE(model_name="SpanBERT/spanbert-base-cased")

    # 2. Exemplo de frase de um artigo científico
    texto_artigo = "O Paracetamol alivia e trata a febre rapidamente em pacientes adultos."

    # 3. Executa a inferência
    tripleto, confianca = extrator.extract_relation_triple(
        text=texto_artigo,
        sub_name="Paracetamol",
        sub_type="DRUG",
        obj_name="febre",
        obj_type="SYMPTOM",
        relation_labels=["trata", "causa", "previne", "no_relation"]
    )

    if tripleto is not None:
        print("\n--- Resultado da Extração ---")
        print(f"📌 Tripleto identificado: {tripleto}")
        print(f"📊 Confiança do modelo: {confianca:.4f}")
    else:
        print("\n❌ Falha na extração (verifique os nomes das entidades e o texto).")