import requests,configparser
from youtubesearchpython import VideosSearch

config = configparser.ConfigParser()
config.read("config.ini")
api_key = config["API"]['api_key']
headers = {
            "X-RapidAPI-Key": api_key,
            "X-RapidAPI-Host": "deezerdevs-deezer.p.rapidapi.com"
}

def search_title_on_deezer(query,album=False):
    url = "https://deezerdevs-deezer.p.rapidapi.com/search"
    querystring = {"q" : query}
    response = requests.get(url,params=querystring,headers=headers)
    json = response.json().get("data")[0]
    artist = json.get("artist")
    cover = json.get("album").get("cover")
    if album:
        return (json.get('album').get('id'),json.get('album').get("title"),artist.get('name'),cover)
    else:
        return (json.get("title"),artist.get('name'),cover)
    
def album_detail_deezer(album_id):
    url = f"https://deezerdevs-deezer.p.rapidapi.com/album/{album_id}"
    response = requests.get(url,headers = headers)
    json : dict = response.json()
    title = json.get("title")
    print(f"Found album {title}")
    tracks = json.get("tracks").get("data")
    return (title,tracks)

def search_youtube(title,artist):
    videosSearch = VideosSearch(f"{title} - {artist}",limit=1)
    res = videosSearch.result().get("result")[0]
    return res.get("link")