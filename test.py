import requests

# URL de l'endpoint que vous souhaitez atteindre
url = "http://127.0.0.1:5000/send_mp3_file"

# Données à envoyer avec la requête POST
data = {
    "output_path": "output/in-a-sentimental-mood-duke-ellington.mp3",
}

response = requests.post(url, json=data)

if response.status_code == 200:
    print("Requête POST réussie!")
    print("Réponse du serveur:", response.text)
else:
    print("Échec de la requête POST. Code de statut:", response.status_code)
