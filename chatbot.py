import json
import os
import requests
import threading
import tempfile
from io import BytesIO
import pygame
from flask import Flask, request, jsonify, send_from_directory
import uuid
from docx import Document
from chromadb import Client
from chromadb.utils import embedding_functions

pygame.mixer.init()

# ChatGPT and Eleven Labs API setup
CHATGPT_API_KEY = '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'
CHATGPT_API_URL = 'https://api.openai.com/v1/chat/completions'
ELEVEN_LABS_API_KEY = 'b4934a9a6cc403063e19de7a89366a0b'

messages = [{"role": "user", "content": "Hello!"}]

def get_chatgpt_response(messages):
    headers = {
        'Content-Type': 'application/json',
        'Authorization': f'Bearer {CHATGPT_API_KEY}'
    }

    data = {
        'model': 'gpt-4',
        'messages': messages,
    }

    response = requests.post(CHATGPT_API_URL, headers=headers, json=data)
    response.raise_for_status()
    response_text = response.json()['choices'][0]['message']['content']
    return response_text.strip()

def get_voice_response(text, voice_id):
    print("Generating voice response...")

    url = f"https://api.elevenlabs.io/v1/text-to-speech/2NGJWkG9EcUo1IE29eN8/stream"
    headers = {
        "Accept": "*/*",
        "Content-Type": "application/json",
        "xi-api-key": ELEVEN_LABS_API_KEY
    }

    data = {
        "text": text,
        "model_id": "eleven_monolingual_v1",
        "voice_settings": {
            "stability": 0,
            "similarity_boost": 0
        }
    }

    response = requests.post(url, json=data, headers=headers, stream=True)

    # Save the audio data to a temporary file
    with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as temp_file:
        for chunk in response.iter_content(chunk_size=1024):
            if chunk:
                temp_file.write(chunk)
        temp_file.flush()

    # Load the audio data into pygame.mixer and play it
    pygame.mixer.music.load(temp_file.name)
    pygame.mixer.music.play()
    while pygame.mixer.music.get_busy():
        pygame.time.Clock().tick(10)

    pygame.mixer.music.unload()
    os.unlink(temp_file.name)
    print("Voice response generated and played.")

def process_files(folders):
    documents = []
    for folder in folders:
        for filename in os.listdir(folder):
            file_path = os.path.join(folder, filename)
            if filename.endswith(".docx"):
                doc = Document(file_path)
                text = "\n".join([p.text for p in doc.paragraphs])
            elif filename.endswith(".txt"):
                with open(file_path, 'r', encoding='utf-8') as file:
                    text = file.read()
            else:
                continue
            documents.append(text)
    return documents

# Initialize ChromaDB client and collection
from chromadb.utils import embedding_functions

embedding_func = embedding_functions.SentenceTransformerEmbeddingFunction(model_name="all-MiniLM-L6-v2")
chroma_client = Client()
collection = chroma_client.create_collection("my_collection", embedding_function=embedding_func)

# Set up the embedding function
embedding_func = embedding_functions.SentenceTransformerEmbeddingFunction(model_name="all-MiniLM-L6-v2")

# Process and index the files
folders = ["transcriptions", "tweets", "personality"]
documents = process_files(folders)

# Add documents to the collection
for i, text in enumerate(documents):
    collection.add(documents=[text], ids=[str(i)])

app = Flask(__name__)

@app.route('/your_chatbot_endpoint', methods=['POST'])
def chatbot_endpoint():
    user_input = request.json['userText']
    messages.append({"role": "user", "content": user_input})
    response_text = get_chatgpt_response(messages)
    messages.append({"role": "assistant", "content": response_text})

    voice_id = '2NGJWkG9EcUo1IE29eN8'
    threading.Thread(target=get_voice_response, args=(response_text, voice_id)).start()

    chatbot_id = len(messages)
    messages.append({"role": "assistant", "content": "BunchuBot is typing...", "id": chatbot_id})

    return jsonify(chatbotResponse=response_text, chatbotId=chatbot_id)

@app.route('/')
def index():
    return send_from_directory('static', 'index.html')

@app.route('/<path:filename>')
def static_files(filename):
    return send_from_directory('static', filename)

if __name__ == '__main__':
    app.run(debug=True)

