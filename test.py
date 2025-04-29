import ollama

model_name = "gemma3:1b"
# Define the user input prompt

prompt = "hi"
# Run the model and get a response

response = ollama.chat(model=model_name, messages=[{"role": "user", "content": prompt}])

# Print the response
print("AI Response:", response["message"]["content"])

