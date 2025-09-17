import os
import json
import uuid
from langchain_openai import AzureOpenAIEmbeddings
from qdrant_client import qdrant_client, models
from dotenv import load_dotenv
from rich import print
from rich.progress import Progress, track

load_dotenv()

collection_name = os.getenv("QDRANT_COLLECTION")
client = qdrant_client.QdrantClient(
    url=os.getenv("QDRANT_URL"),
    api_key=os.getenv("QDRANT_API_KEY")
)

text_embedding_small_3 = AzureOpenAIEmbeddings(
    model="text-embedding-3-small",
    api_key=os.getenv("AZURE_OPENAI_API_KEY"),
    azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
    api_version=os.getenv("AZURE_OPENAI_VERSION"),
    dimensions=1536,
)
bm25_embedding_model = models.SparseTextEmbedding("Qdrant/bm25")
colbert_embedding_model = models.LateInteractionTextEmbedding("colbert-ir/colbertv2.0")

def reinitialize_collection():
    client.delete_collection(collection_name=collection_name)
    client.create_collection(
        collection_name=collection_name,
        vectors_config={
            "text-embedding-3-small": models.VectorParams(
                size=1536,
                distance=models.Distance.COSINE
            ),
            "colbert": models.VectorParams(
                size=128,
                distance=models.Distance.COSINE,
                multivector_config=models.MultiVectorConfig(
                    comparator=models.MultiVectorComparator.MAX_SIM
                ),
                hnsw_config=models.HnswConfigDiff(m=0)  # Disable HNSW for reranking
            )
        },
        sparse_vectors_config={
            "bm25": models.SparseVectorParams(modifier=models.Modifier.IDF)
        }
    )
    print("Created collection")

    # --- Load a.json
    with open("a.json", "r", encoding="utf-8") as f:
        raw_points = json.load(f)

    # --- Rebuild points with regenerated vectors
    new_points = []
    with Progress() as progress:
        task = progress.add_task("[cyan]Embedding and preparing points...", total=len(raw_points))

        for point in raw_points:
            payload = point.get("payload", {})
            doc_id = str(uuid.uuid4())
            text = payload.get("page_content")

            if not text:
                progress.advance(task)
                continue

            try:
                dense_vector = text_embedding_small_3.embed_query(text)
                sparse_vector = next(bm25_embedding_model.query_embed(text)).as_object()
                colbert_vector = next(colbert_embedding_model.query_embed(text))
                # sparse_vector = bm25_embedding_model.embed_text(text).as_object()
                # colbert_vector = colbert_embedding_model.embed_text(text)
                # sparse_vector = list(bm25_embedding_model.embed([text]))[0].as_object()
                # colbert_vector = list(colbert_embedding_model.embed([text]))[0]

                point = models.PointStruct(
                        id=doc_id,
                        payload=payload,
                        vector={
                            "text-embedding-3-small": dense_vector,
                            "colbert": colbert_vector,
                            "bm25": sparse_vector,
                        },
                    )

                new_points.append(
                    point
                )

                client.upsert(
                    collection_name=collection_name,
                    points=[point]
                )
            except Exception as e:
                print(f"[red]Error embedding point {doc_id}: {e}[/red]")

            progress.advance(task)

    # --- Upload back to Qdrant

    print(f"✅ Successfully reinserted {len(new_points)} points into collection '{collection_name}'")

query = "total debt"
file_ids = [
    "2356e66b-1268-476a-af37-731afcecf452",
]

# reinitialize_collection()

# result = client.scroll(
#     collection_name=collection_name,
#     limit=100,
#     offset=0,
# )
# print(result)

document = json.load(open("a.json", "w"))

exit(0)

results = client.query_points(
    limit=5,
    collection_name=collection_name,
    query=next(colbert_embedding_model.query_embed(query)),
    using="colbert",
    prefetch=[
        models.Prefetch(
            query=text_embedding_small_3.embed_query(query),
            using="text-embedding-3-small",
            limit=20,
        ),
        models.Prefetch(
            query=models.SparseVector(**next(bm25_embedding_model.query_embed(query)).as_object()),
            using="bm25",
            limit=20,
        ),
    ],
    query_filter=models.Filter(
        must=[
            models.FieldCondition(
                key="metadata.file_id",
                match=models.MatchAny(any=file_ids),
            ),
            # models.FieldCondition(
            #     key="metadata.page_number",
            #     match=models.MatchAny(any=[324]),
            # ),
            models.FieldCondition(
                key="metadata.type",
                match=models.MatchValue(value="text"),
            ),
        ]
    ),
    with_payload=True,
)

for r in results:
    # print(r.payload)
    print(r)
    print("----")
