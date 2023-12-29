from flask import Flask,render_template,request,jsonify,redirect
from datetime import datetime 
import slugify
from operator import attrgetter
import yt_dlp
from flask_socketio import SocketIO
from utils.database import db,Song
from utils.search import search_title_on_deezer,search_youtube,album_detail_deezer

app = Flask(__name__)
socketio = SocketIO(app)

db.connect()
if not db.table_exists("song"):
    db.create_tables([Song])

@socketio.on('connect')
def handle_connect():
    print('Client socketio connected')

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

@app.route("/history")
def history():
    history = Song.select().where(Song.downloaded == True).order_by(Song.downloaded_on.desc())
    return render_template("history.html",history=history)

@app.route("/download_song",methods=["POST"])
def download_song():
    try:
        data : dict = request.get_json()
        song = data.get("title")
        socketio.emit('download_progress', {'progress': 'Récupération des informations sur le titre'}, namespace='/')
        title,artist,cover = search_title_on_deezer(song)
        song_object,_ = Song.get_or_create(title=title,artist_name=artist)
        song_object.cover_path = cover
        song_object.save()
        socketio.emit('download_progress', {'progress': 'Recherche youtube'}, namespace='/')
        url = search_youtube(title,artist)
        song_object.url = url
        song_object.save()
        socketio.emit('download_progress', {'progress': 'Téléchargement du contenu'}, namespace='/')
        output_path = download_youtube_video(url,title,artist)
        song_object.filepath = output_path
        song_object.downloaded = True
        song_object.downloaded_on = datetime.now()
        song_object.save()
        return jsonify({"status" : "200","title_downloaded" : f"{title} - {artist}","cover_path" : cover})
    except:
        print("An error occured")
        return jsonify({"status" : "500"})
    
@app.route("/suggest_song",methods=["POST"])
def suggest_song():
    try:
        data : dict = request.get_json()
        song = data.get("title")
        object_in_db = Song.get_or_none(title=song)
        if object_in_db:
            print(f"found in db")
            title = object_in_db.title
            artist = object_in_db.artist_name
        else:
            print(f"found on deezer")
            title,artist,cover = search_title_on_deezer(song)
        return jsonify({"suggestion" : f"{title} - {artist}","cover_path" : cover})
    except:
        return jsonify({"error" : "Couldn't find any suggestion"})
    
@app.route("/suggest_album",methods=["POST"])
def suggest_album():
    try:
        data : dict = request.get_json()
        song = data.get("title")
        _,album_title,artist,_ = search_title_on_deezer(song,album=True)
        return jsonify({"suggestion" : f"{album_title} - {artist}"})
    except:
        return jsonify({"error" : "Couldn't find any suggestion"})

@app.route("/download_album",methods=["POST"])
def download_album():
    data : dict = request.get_json()
    album = data.get("title")
    album_id,album_title,artist,cover = search_title_on_deezer(album,True)
    url = f"https://deezerdevs-deezer.p.rapidapi.com/album/{album_id}"
    title,tracks = album_detail_deezer(album_id)
    for i,track in enumerate(tracks):
        try:
            socketio.emit('download_progress', {'progress': f'Downloading {i+1}/{len(tracks)} - {track.get("title")}'}, namespace='/')
            url = search_youtube(track.get("title"),artist)
            song_object,_ = Song.get_or_create(title=track.get("title"),artist_name=artist)
            song_object.cover_path = cover
            song_object.url = url
            output_path = download_youtube_video(url,track.get("title"),artist)
            song_object.filepath = output_path
            song_object.downloaded = True
            song_object.downloaded_on = datetime.now()
            song_object.save()
        except:
            print(f"Could not download {track.get('title')}")
    socketio.emit('download_progress', {'progress': f'Downloaded all album {album_title}'}, namespace='/')
    return jsonify({"status" : "200","title_downloaded" : f"{album_title} - {artist}","cover_path" : cover})


@app.route("/")
def index():
    return redirect("song")

if __name__ == "__main__":
    try:
        socketio.run(app,debug=True)
    except KeyboardInterrupt:
        db.close()