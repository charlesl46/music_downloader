from flask import Flask,render_template,request,jsonify,redirect
from datetime import datetime 
import slugify
import yt_dlp
import eyed3
from flask_socketio import SocketIO
from utils.database import db,Song,Settings
from utils.search import search_title_on_deezer,search_youtube,album_detail_deezer

app = Flask(__name__)
socketio = SocketIO(app)

@app.context_processor
def inject_settings():
    settings,_ = Settings.get_or_create(id=1)
    return dict(settings=settings)

db.connect()
if not db.table_exists("song"):
    db.create_tables([Song])
if not db.table_exists("settings"):
    db.create_tables([Settings])

@socketio.on('connect')
def handle_connect():
    print('Client socketio connected')

@app.route("/settings")
def settings():
    settings,_ = Settings.get_or_create(id=1)
    print(f"from db {settings.set_metadata}")
    return render_template("settings.html",settings=settings)

@app.route("/toggle_settings",methods=["POST"])
def toggle_settings():
    data : dict = request.get_json()
    setting_to_change = data.get("setting")
    sentences = {"show_history" : ("History won't be shown from now on","History will be shown from now on"),"set_metadata" : ("Metadata won't be set automatically on your files from now on","Metadata will be set automatically on your files from now on")}
    settings,_ = Settings.get_or_create(id=1)
    setattr(settings,setting_to_change,data.get("state"))
    settings.save()
    if data.get("state") == True:
        index = 1
    else:
        index = 0
    sentence = sentences.get(setting_to_change)[index]
    return jsonify({"status" : 200,"sentence" : sentence})

def download_youtube_video(url,title,artist,album,release_date):
    output = f"output/{slugify.slugify(title + '-' + artist)}"
    ydl_opts = {
        'format': 'bestaudio/best',
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '192',
        }],
        'outtmpl': output
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        ydl.download([url])        

    settings,_ = Settings.get_or_create(id=1)
    output_final = f"{output}.mp3"

    if settings.set_metadata:
        print(f"Setting metadata with {url,title,artist,album,release_date}")
        audiofile = eyed3.load(output_final)
        audiofile.tag.release_date = release_date
        audiofile.tag.artist = artist
        audiofile.tag.album = album
        audiofile.tag.title = title
        audiofile.tag.save()

    return output_final

@app.route("/song")
def song():
    settings,_ = Settings.get_or_create(id=1)
    return render_template("song.html",settings=settings)

@app.route("/album")
def album():
    settings,_ = Settings.get_or_create(id=1)
    return render_template("album.html",settings=settings)

@app.route("/history")
def history():
    history = Song.select().where(Song.downloaded == True).order_by(Song.downloaded_on.desc())
    settings,_ = Settings.get_or_create(id=1)
    if not settings.show_history:
        return redirect("song")
    else:
        return render_template("history.html",history=history)

@app.route("/download_song",methods=["POST"])
def download_song():
    try:
        data : dict = request.get_json()
        song = data.get("title")
        socketio.emit('download_progress', {'progress': 'Récupération des informations sur le titre'}, namespace='/')
        title,artist,cover,data = search_title_on_deezer(song)
        socketio.emit("title-data",{"release_date" : data.get("release_date"),"cover" : cover,"title" : title,"artist" : artist,"explicit_lyrics" : data.get("explicit_lyrics")})
        song_object,_ = Song.get_or_create(title=title,artist_name=artist)
        song_object.cover_path = cover
        song_object.save()
        socketio.emit('download_progress', {'progress': 'Recherche youtube'}, namespace='/')
        url = search_youtube(title,artist)
        song_object.url = url
        url_payload = url.replace("https://www.youtube.com/watch?v=","").strip()
        socketio.emit('youtube-url',{'url' : url_payload},namespace="/")
        song_object.save()
        socketio.emit('download_progress', {'progress': 'Téléchargement du contenu'}, namespace='/')
        output_path = download_youtube_video(url,title,artist,data.get("album_title"),data.get("release_date"))
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
            title,artist,cover,data = search_title_on_deezer(song)
        return jsonify({"suggestion" : f"{title} - {artist}","cover_path" : cover})
    except:
        return jsonify({"error" : "Couldn't find any suggestion"})
    
@app.route("/suggest_album",methods=["POST"])
def suggest_album():
    try:
        data : dict = request.get_json()
        song = data.get("title")
        _,album_title,artist,_,_ = search_title_on_deezer(song,album=True)
        return jsonify({"suggestion" : f"{album_title} - {artist}"})
    except:
        return jsonify({"error" : "Couldn't find any suggestion"})

@app.route("/download_album",methods=["POST"])
def download_album():
    data : dict = request.get_json()
    album = data.get("title")
    album_id,album_title,artist,cover,release_date = search_title_on_deezer(album,True)
    url = f"https://deezerdevs-deezer.p.rapidapi.com/album/{album_id}"
    title,tracks = album_detail_deezer(album_id)
    for i,track in enumerate(tracks):
        socketio.emit('download_progress', {'progress': f'Downloading {i+1}/{len(tracks)} - {track.get("title")}'}, namespace='/')
        url = search_youtube(track.get("title"),artist)
        song_object,_ = Song.get_or_create(title=track.get("title"),artist_name=artist)
        song_object.cover_path = cover
        song_object.url = url
        output_path = download_youtube_video(url,track.get("title"),artist,title,release_date)
        song_object.filepath = output_path
        song_object.downloaded = True
        song_object.downloaded_on = datetime.now()
        song_object.save()
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