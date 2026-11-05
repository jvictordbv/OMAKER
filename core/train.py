import os
import json
import torch
import torch.nn as nn
from torch.utils.data import Dataset, DataLoader
from sklearn.metrics import accuracy_score, f1_score, classification_report
from transformers import get_linear_schedule_with_warmup
from relation_extractor import RelationExtractorPURE

# Mapeamento de relações
REL2ID = {
    "trata": 0,
    "causa": 1,
    "previne": 2,
    "no_relation": 3
}
ID2REL = {v: k for k, v in REL2ID.items()}

class OMAKERRelationDataset(Dataset):
    def __init__(self, data_list):
        self.data = data_list

    def __len__(self):
        return len(self.data)

    def __getitem__(self, idx):
        item = self.data[idx]
        label_id = REL2ID.get(item["relation"], REL2ID["no_relation"])
        return item, label_id

def train_omaker_pure_e2e(
    data_path: str = "core/train_relations.json",
    epochs: int = 15,
    lr_encoder: float = 2e-5,
    lr_classifier: float = 1e-3,
    weight_decay: float = 0.01,
    batch_size: int = 2,
    gradient_accumulation_steps: int = 2,
    save_path: str = "omaker_pure.pt"
):
    print("🚀 Iniciando Treinamento End-to-End (Fine-Tuning Completo) do PURE / SpanBERT no OMAKER...\n")

    if os.path.exists(data_path):
        with open(data_path, "r", encoding="utf-8") as f:
            dataset_list = json.load(f)
        print(f"📦 Dataset carregado com sucesso: {len(dataset_list)} amostras de '{data_path}'.")
    else:
        print(f"⚠️ Arquivo '{data_path}' não encontrado. Verifique o caminho dos dados.")
        return

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"💻 Dispositivo ativo: {device}\n")

    # Inicializa o extrator de relações PURE
    model = RelationExtractorPURE(model_name="SpanBERT/spanbert-base-cased", num_relations=len(REL2ID))
    
    # Habilita gradientes para todas as camadas (Encoder + Classifier)
    for param in model.parameters():
        param.requires_grad = True

    model.float()  # Garante estabilidade numérica em float32
    model.to(device)

    dataset = OMAKERRelationDataset(dataset_list)
    dataloader = DataLoader(dataset, batch_size=batch_size, shuffle=True)

    # Otimização diferencial (learning rates distintos para encoder e classificador)
    optimizer_grouped_parameters = [
        {
            "params": [p for n, p in model.encoder.named_parameters()],
            "lr": lr_encoder,
            "weight_decay": weight_decay
        },
        {
            "params": [p for n, p in model.classifier.named_parameters()],
            "lr": lr_classifier,
            "weight_decay": weight_decay
        }
    ]

    optimizer = torch.optim.AdamW(optimizer_grouped_parameters)
    
    total_steps = (len(dataloader) // gradient_accumulation_steps) * epochs
    scheduler = get_linear_schedule_with_warmup(
        optimizer,
        num_warmup_steps=int(total_steps * 0.1),
        num_training_steps=max(total_steps, 1)
    )

    criterion = nn.CrossEntropyLoss()

    best_f1 = 0.0

    for epoch in range(epochs):
        model.train()
        total_loss = 0.0
        all_preds, all_targets = [], []
        optimizer.zero_grad()

        for step, (item_dict, label_tensor) in enumerate(dataloader):
            # Processa cada item do batch
            batch_loss = 0.0

            for i in range(len(label_tensor)):
                text = item_dict["text"][i]
                sub_name = item_dict["sub_name"][i]
                sub_type = item_dict["sub_type"][i]
                obj_name = item_dict["obj_name"][i]
                obj_type = item_dict["obj_type"][i]
                target = label_tensor[i].unsqueeze(0).to(device)

                s_start = text.find(sub_name)
                o_start = text.find(obj_name)
                if s_start == -1 or o_start == -1:
                    continue

                sub_span = (s_start, s_start + len(sub_name))
                obj_span = (o_start, o_start + len(obj_name))

                formatted_text = model.format_input_with_markers(text, sub_span, sub_type, obj_span, obj_type)
                inputs = model.tokenizer(formatted_text, return_tensors="pt").to(device)

                outputs = model.encoder(**inputs)
                sequence_output = outputs.last_hidden_state

                tokens = model.tokenizer.convert_ids_to_tokens(inputs["input_ids"][0])
                s_marker = f"<S:{sub_type.upper()}>"
                o_marker = f"<O:{obj_type.upper()}>"

                s_idx = tokens.index(s_marker) if s_marker in tokens else 1
                o_idx = tokens.index(o_marker) if o_marker in tokens else len(tokens) - 2

                sub_emb = sequence_output[0, s_idx, :]
                obj_emb = sequence_output[0, o_idx, :]

                pair_rep = torch.cat([sub_emb, obj_emb], dim=-1).unsqueeze(0).float()
                logits = model.classifier(pair_rep)

                loss = criterion(logits, target) / gradient_accumulation_steps
                loss.backward()

                batch_loss += loss.item() * gradient_accumulation_steps
                pred_id = torch.argmax(logits, dim=-1).item()
                all_preds.append(pred_id)
                all_targets.append(target.item())

            if (step + 1) % gradient_accumulation_steps == 0 or (step + 1) == len(dataloader):
                torch.nn.utils.clip_grad_norm_(model.parameters(), max_norm=1.0)
                optimizer.step()
                scheduler.step()
                optimizer.zero_grad()

            total_loss += batch_loss

        avg_loss = total_loss / len(dataloader) if len(dataloader) > 0 else 0.0
        acc = accuracy_score(all_targets, all_preds) if all_targets else 0.0
        f1 = f1_score(all_targets, all_preds, average="macro") if all_targets else 0.0

        print(f"Época {epoch+1:02d}/{epochs:02d} | Loss: {avg_loss:.4f} | Acurácia: {acc*100:.2f}% | Macro F1: {f1*100:.2f}%")

        if f1 >= best_f1:
            best_f1 = f1
            torch.save(model.state_dict(), save_path)

    print(f"\n✅ Treinamento concluído com sucesso! Melhores pesos salvos em '{save_path}' (Melhor Macro F1: {best_f1*100:.2f}%).")

if __name__ == "__main__":
    train_omaker_pure_e2e(epochs=15, save_path="omaker_pure.pt")
