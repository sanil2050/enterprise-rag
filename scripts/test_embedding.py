from app.ingestion.embedder import generate_embedding


text = "Employees receive annual leave according to company policy."

embedding = generate_embedding(text)

print("Embedding generated successfully.")
print("Dimensions:", len(embedding))
print("First 10 values:", embedding[:10])