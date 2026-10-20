import os
import json
import torch
import torch.nn as nn
from torch.utils.data import Dataset, DataLoader
from sklearn.metrics import accuracy_score, f1_score
from relation_extractor import RelationExtractorPURE

# 1. MAPEAMENTO DE RÓTULOS DE RELAÇÃO
REL2ID = {
    "trata": 0,
    "causa": 1,
    "previne": 2,
    "no_relation": 3
}
ID2REL = {v: k for k, v in REL2ID.items()}

# 2. CONJUNTO DE DADOS DE EXEMPLO PARA O OMAKER
EXEMPLO_DATASET = [
    {
        "text": "O Paracetamol alivia e trata a febre rapidamente em pacientes adultos.",
        "sub_name": "Paracetamol", "sub_type": "DRUG",
        "obj_name": "febre", "obj_type": "SYMPTOM",
        "relation": "trata"
    },
    {
        "text": "O uso continuado de Aspirina previne o infarto agudo do miocárdio.",
        "sub_name": "Aspirina", "sub_type": "DRUG",
        "obj_name": "infarto", "obj_type": "DISEASE",
        "relation": "previne"
    },
    {
        "text": "O consumo de álcool causa cirrose hepática em pacientes predispostos.",
        "sub_name": "álcool", "sub_type": "DRUG",
        "obj_name": "cirrose hepática", "obj_type": "DISEASE",
        "relation": "causa"
    },
    {
        "text": "O Ibuprofeno trata a inflamação nas articulações.",
        "sub_name": "Ibuprofeno", "sub_type": "DRUG",
        "obj_name": "inflamação", "obj_type": "SYMPTOM",
        "relation": "trata"
    },
    {
        "text": "O paciente tomou Paracetamol e apresentou tontura pela manhã.",
        "sub_name": "Paracetamol", "sub_type": "DRUG",
        "obj_name": "tontura", "obj_type": "SYMPTOM",
        "relation": "causa"
    },
    {
        "text": "A vacina contra gripe previne a infecção viral em idosos.",
        "sub_name": "vacina contra gripe", "sub_type": "DRUG",
        "obj_name": "infecção viral", "obj_type": "DISEASE",
        "relation": "previne"
    },
    {
        "text": "O médico mencionou o Paracetamol e a febre no prontuário.",
        "sub_name": "Paracetamol", "sub_type": "DRUG",
        "obj_name": "febre", "obj_type": "SYMPTOM",
        "relation": "no_relation"
    }
]

# 3. CLASS DATASET PYTORCH
class OMAKERRelationDataset(Dataset):
    def __init__(self, data_list):
        self.data = data_list

    def __len__(self):
        return len(self.data)

    def __getitem__(self, idx):
        item = self.data[idx]
        label_id = REL2ID.get(item["relation"], REL2ID["no_relation"])
        return item, label_id


def train_omaker_pure(data_path: str = None, epochs: int = 5, lr: float = 2e-5, save_path: str = "omaker_pure.pt"):
    print("🚀 Iniciando o treinamento do extrator de relações PURE/SpanBERT no OMAKER...\n")
    
    # Carrega dados do arquivo JSON se fornecido, senão usa o dataset interno
    if data_path and os.path.exists(data_path):
        with open(data_path, "r", encoding="utf-8") as f:
            dataset_list = json.load(f)
        print(f"📦 Carregado {len(dataset_list)} exemplos de '{data_path}'.")
    else:
        dataset_list = EXEMPLO_DATASET
        print(f"📦 Usando dataset de exemplo com {len(dataset_list)} amostras.")

    # Dispositivo (GPU se disponível, senão CPU)
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"💻 Dispositivo de processamento: {device}\n")

    # Inicializa o modelo
    num_relations = len(REL2ID)
    model = RelationExtractorPURE(model_name="SpanBERT/spanbert-base-cased", num_relations=num_relations)
    model.to(device)

    # dataset e dataloader
    dataset = OMAKERRelationDataset(dataset_list)
    dataloader = DataLoader(dataset, batch_size=1, shuffle=True)

    # Otimizador AdamW e Função de Perda (Cross Entropy)
    optimizer = torch.optim.AdamW(model.parameters(), lr=lr)
    criterion = nn.CrossEntropyLoss()

    # Loop de Treinamento
    for epoch in range(epochs):
        model.train()
        total_loss = 0.0
        all_preds = []
        all_targets = []

        for item_dict, label_tensor in dataloader:
            optimizer.zero_grad()
            
            # Extrai valores do dicionário (batch size = 1)
            text = item_dict["text"][0]
            sub_name = item_dict["sub_name"][0]
            sub_type = item_dict["sub_type"][0]
            obj_name = item_dict["obj_name"][0]
            obj_type = item_dict["obj_type"][0]
            target_label = label_tensor.to(device)

            s_start = text.find(sub_name)
            o_start = text.find(obj_name)

            if s_start == -1 or o_start == -1:
                continue

            sub_span = (s_start, s_start + len(sub_name))
            obj_span = (o_start, o_start + len(obj_name))

            # Formata texto com Typed Entity Markers
            formatted_text = model.format_input_with_markers(text, sub_span, sub_type, obj_span, obj_type)
            inputs = model.tokenizer(formatted_text, return_tensors="pt").to(device)

            # Passagem pelo encoder
            outputs = model.encoder(**inputs)
            sequence_output = outputs.last_hidden_state

            # Localização dos tokens marcadores
            tokens = model.tokenizer.convert_ids_to_tokens(inputs["input_ids"][0])
            s_marker = f"<S:{sub_type.upper()}>"
            o_marker = f"<O:{obj_type.upper()}>"

            s_idx = tokens.index(s_marker) if s_marker in tokens else 1
            o_idx = tokens.index(o_marker) if o_marker in tokens else len(tokens) - 2

            sub_emb = sequence_output[0, s_idx, :]
            obj_emb = sequence_output[0, o_idx, :]

            # Concatenação e representação do par
            pair_rep = torch.cat([sub_emb, obj_emb], dim=-1).unsqueeze(0)
            pair_rep = pair_rep.to(device=device, dtype=next(model.classifier.parameters()).dtype)

            # Classificação
            logits = model.classifier(pair_rep)
            loss = criterion(logits, target_label)

            # Backpropagation
            loss.backward()
            optimizer.step()

            total_loss += loss.item()

            # Salva predição
            pred_id = torch.argmax(logits, dim=-1).item()
            all_preds.append(pred_id)
            all_targets.append(target_label.item())

        avg_loss = total_loss / len(dataloader) if len(dataloader) > 0 else 0.0
        acc = accuracy_score(all_targets, all_preds) if all_targets else 0.0
        f1 = f1_score(all_targets, all_preds, average="micro") if all_targets else 0.0

        print(f"Época {epoch+1}/{epochs} | Loss: {avg_loss:.4f} | Acurácia: {acc*100:.2f}% | F1-Score: {f1*100:.2f}%")

    # Salva os pesos do modelo treinado
    torch.save(model.state_dict(), save_path)
    print(f"\n✅ Modelo treinado salvo com sucesso em: '{save_path}'")


if __name__ == "__main__":
    train_omaker_pure(epochs=5, lr=2e-5, save_path="omaker_pure.pt")
