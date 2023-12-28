from flask import Flask,render_template,request,jsonify,send_file
import requests
import slugify
import configparser
import yt_dlp
from youtubesearchpython import VideosSearch
from flask_socketio import SocketIO

app = Flask(__name__)
socketio = SocketIO(app)

config = configparser.ConfigParser()
config.read("config.ini")
api_key = config["API"]['api_key']
headers = {
            "X-RapidAPI-Key": api_key,
            "X-RapidAPI-Host": "deezerdevs-deezer.p.rapidapi.com"
}

@socketio.on('connect')
def handle_connect():
    print('Client socketio connected')

def search_on_deezer(query,album=False):
    url = "https://deezerdevs-deezer.p.rapidapi.com/search"
    querystring = {"q" : query}
    response = requests.get(url,params=querystring,headers=headers)
    json = response.json().get("data")[0]
    artist = json.get("artist")
    if album:
        return (json.get('album').get('id'),artist.get('name'))
    else:
        return (json.get("title"),artist.get('name'))

def search_youtube(title,artist):
    videosSearch = VideosSearch(f"{title} - {artist}",limit=1)
    res = videosSearch.result().get("result")[0]
    return res.get("link")

def download_youtube_video(url,title,artist):
    ydl_opts = {
        'format': 'bestaudio/best',
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '192',
        }],
        'outtmpl': f"output/{slugify.slugify(title + '-' + artist)}"
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        ydl.download([url])

    return f"output/{slugify.slugify(title + '-' + artist)}.mp3"

@app.route("/song")
def song():
    return render_template("song.html")

@app.route("/album")
def album():
    return render_template("album.html")

@app.route("/test")
def test():
    return send_file("downloader.zip",as_attachment=True)

@app.route("/download/<path:filename>", methods=["GET"])
def download_file(filename):
    # Assurez-vous que filename est sécurisé pour éviter des problèmes de sécurité
    # Vous pouvez également spécifier le dossier dans lequel les fichiers sont stockés
    file_path = filename

    # Utilisez send_file pour envoyer le fichier en tant que téléchargement
    return send_file(file_path, as_attachment=True)

@app.route("/download_song",methods=["POST"])
def download_song():
    try:
        data : dict = request.get_json()
        song = data.get("title")
        title,artist = search_on_deezer(song)
        socketio.emit('download_progress', {'progress': 'Informations sur le titre récupérées'}, namespace='/')
        url = search_youtube(title,artist)
        socketio.emit('download_progress', {'progress': 'Lien youtube récupéré'}, namespace='/')
        output_path = download_youtube_video(url,title,artist)
        socketio.emit('download_progress', {'progress': 'Contenu téléchargé'}, namespace='/')
        print(f"Found title for {song} : {title} - {artist}")
        return jsonify({"status" : "200","title_downloaded" : f"{title} - {artist}","output_path" : output_path})
    except:
        print("An error occured")
        return jsonify({"status" : "500"})
    
@app.route("/suggest_song",methods=["POST"])
def suggest_song():
    try:
        data : dict = request.get_json()
        song = data.get("title")
        title,artist = search_on_deezer(song)
        return jsonify({"suggestion" : f"{title} - {artist}"})
    except:
        return jsonify({"error" : "Couldn't find any suggestion"})

@app.route("/download_album",methods=["POST"])
def download_album():
    data : dict = request.get_json()
    album = data.get("title")
    album_id,artist = search_on_deezer(album,True)
    url = f"https://deezerdevs-deezer.p.rapidapi.com/album/{album_id}"
    response = requests.get(url,headers = headers)
    json : dict = response.json()
    title = json.get("title")
    print(f"Found album {title}")
    tracks = json.get("tracks").get("data")
    tracks_titles = []
    for track in tracks:
        try:
            url = search_youtube(track.get("title"),artist)
            output_path = download_youtube_video(url,track.get("title"),artist)
        except:
            print(f"Could not download {track.get('title')}")
    return jsonify({"status" : "200"})


@app.route("/")
def index():
    return render_template("index.html")

if __name__ == "__main__":
    socketio.run(app,debug=True)