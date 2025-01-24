import pandas as pd
import os
import torch
import numpy as np
from stqdm import stqdm
from transformers import AutoModel, AutoTokenizer
from sklearn.metrics.pairwise import cosine_similarity
from src.data_utils import ConceptMatch

## TO DO
## Add docstrings


class ModelHandler:
    def __init__(
        self, model_path="FremyCompany/BioLORD-2023", cache_dir="models/biolord"
    ):
        self.model_path = model_path
        self.cache_dir = cache_dir
        self.model = None
        self.tokenizer = None

    def load_model(self):
        """
        Load and/or cache BioLORD model and tokenizer
        """
        try:
            if not os.path.exists(self.cache_dir):
                os.makedirs(self.cache_dir)

            self.tokenizer = AutoTokenizer.from_pretrained(
                self.model_path, cache_dir=self.cache_dir
            )
            self.model = AutoModel.from_pretrained(
                self.model_path, cache_dir=self.cache_dir
            )

            if torch.backends.mps.is_available():
                print("[INFO] MPS is available")
                self.model.to("mps")
            elif torch.cuda.is_available():
                print("[INFO] CUDA is available")
                self.model.to("cuda")

            print(f"[INFO] Using device: {self.model.device}")

            return True, "Model loaded successfully"
        except Exception as e:
            return False, f"Error loading model: {e}"

    def generate_embedding(self, text):
        inputs = self.tokenizer(
            text, return_tensors="pt", padding=True, truncation=True, max_length=512
        )

        if torch.backends.mps.is_available() or torch.cuda.is_available():
            # Move the inputs to GPU acceleration if available
            device = self.model.device
            inputs = {key: value.to(device) for key, value in inputs.items()}

            with torch.no_grad():
                outputs = self.model(**inputs)

            # Move the output back to CPU before converting to numpy type
            return outputs.last_hidden_state.mean(dim=1).squeeze().cpu().numpy()

        else:
            with torch.no_grad():
                outputs = self.model(**inputs)

            return outputs.last_hidden_state.mean(dim=1).squeeze().numpy()

    def batch_generate_embeddings(self, texts, batch_size=32):
        embeddings = []
        for i in stqdm(range(0, len(texts), batch_size)):
            batch_texts = texts[i : i + batch_size]
            batch_embeddings = [self.generate_embedding(text) for text in batch_texts]
            embeddings.extend(batch_embeddings)
        return np.array(embeddings)

    def get_concept_similarities(self, source_table, target_table):
        try:
            source_texts = [concept.concept_name for concept in source_table.concepts]
            target_texts = [concept.concept_name for concept in target_table.concepts]

            # get embeddings
            print("Generating source embeddings...")
            source_embeddings = self.batch_generate_embeddings(source_texts)
            print("Generating target embeddings...")
            target_embeddings = self.batch_generate_embeddings(target_texts)

            # convert to tensors
            source_tensor = torch.tensor(source_embeddings, device=self.model.device)
            target_tensor = torch.tensor(target_embeddings, device=self.model.device)

            # numpy doesn't support gpu tensors
            source_cpu = source_tensor.cpu()
            target_cpu = target_tensor.cpu()

            # calculate similarities
            print("Calculating similarities...")
            similarities = cosine_similarity(source_cpu, target_cpu)

            return True, similarities

        except Exception as e:
            return False, f"Error calculating similarities: {e}"

    def generate_initial_matches(self, source_table, target_table, similarities):
        matches = []

        count_dict = {
            concept.source_key: concept.concept_count
            for concept in source_table.concepts
        }

        for i, row in enumerate(similarities):
            best_match_idx = np.argmax(row)
            matches.append(
                ConceptMatch(
                    source_key=source_table.concepts[i].source_key,
                    target_concept_id=target_table.concepts[best_match_idx].concept_id,
                    similarity_score=float(row[best_match_idx]),
                    confirmation_status="False",
                    first_confirmation_timestamp=None,
                    last_update_timestamp=None,
                )
            )

        # sorting by desc
        matches.sort(key=lambda x: count_dict[x.source_key], reverse=True)  # in place

        return matches
