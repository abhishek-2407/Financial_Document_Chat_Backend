
# class FinBERTEmbeddings(Embeddings):
#     def __init__(self, model, tokenizer):
#         self.model = model
#         self.tokenizer = tokenizer
#         self.embedding_dim = 768

#     def embed_documents(self, texts: List[str]) -> List[List[float]]:
#         embeddings = get_finbert_embeddings(texts, self.model, self.tokenizer)
#         return embeddings.tolist()

#     def embed_query(self, text: str) -> List[float]:
#         embeddings = get_finbert_embeddings([text], self.model, self.tokenizer)
#         return embeddings[0].tolist()

# from transformers import AutoModel, AutoTokenizer
# import torch

# model_name = "ProsusAI/finbert"
# tokenizer = AutoTokenizer.from_pretrained(model_name)
# model = AutoModel.from_pretrained(model_name)

# def get_finbert_embeddings(texts, model, tokenizer):
#     # Tokenize the input texts
#     encoded_input = tokenizer(
#         texts, 
#         padding=True, 
#         truncation=True, 
#         max_length=512, 
#         return_tensors='pt'
#     )

#     # Generate embeddings using the model
#     with torch.no_grad():
#         output = model(**encoded_input)

#     # Extract [CLS] token embeddings as sentence-level representation
#     embeddings = output.last_hidden_state[:, 0, :].numpy()

#     return embeddings

# # Create FinBERT embedding wrapper
# embeddings = FinBERTEmbeddings(model, tokenizer)
