import requests
import os
import re, json
from urllib.parse import quote_plus
from ..utilities import log
from .SubdlUtilities import get_language_info
from ..seeker import SubtitlesDownloadError, SubtitlesErrors

SEARCH_URL = "https://api.subdl.com/api/v1/subtitles"
DOWNLOAD_URL = "https://dl.subdl.com"



def get_subdl_api():
    global settings_provider  # Ensure we're using the existing instance
    API_KEY = settings_provider.getSetting("Subdl_API_KEY")
    if API_KEY:
        return API_KEY
    print("Error: SubDL API key is missing.")
    return None


def prepare_search_string(s):
    s = s.replace("'", "").strip()
    s = re.sub(r'\(\d\d\d\d\)$', '', s)  # remove year from title
    s = quote_plus(s)
    return s


def get_subtitles_list_movie(searchstring, title, languageshort, languagelong, subtitles_list):
    """Fetches subtitles from the SubDL API and adds them to subtitles_list."""
    
    API_KEY = get_subdl_api()
    if not API_KEY:
        print("Error: SubDL API key is missing.")
        return

    params = {
        "api_key": API_KEY,
        "film_name": searchstring,
        #"type": "tv" if tvshow else "movie",
        "imdb_id": None,
        #"season_number": season if tvshow else None,
        #"episode_number": episode if tvshow else None,
        #"year": year,
        "languages": languageshort,
        "subs_per_page": 50
        }

    response = requests.get(SEARCH_URL, params=params)
    json_data = response.json()
    print(json.dumps(json_data, indent=4))
    #print(json.dumps(json_data, indent=4))
    status = json_data["status"]
    if (status == True):
        try:
            all_subs_data = json_data["subtitles"]
            #print(json.dumps(all_subs_data, indent=4))
            for item in all_subs_data:
                try:
                    language = item["lang"]
                    filename = item["release_name"]
                    sync = False
                    id = item["url"]
                    link = (DOWNLOAD_URL) + id
                    print(language , filename , sync , id , link)
                    subtitles_list.append({'filename': filename, 'sync': False, 'id' : id, 'language_flag': languageshort, 'language_name': languagelong})
                except:
                    pass
        except json.JSONDecodeError:
            print("Error: Failed to decode JSON response.")
    return

def get_subtitles_list_tv(searchstring, tvshow, season, episode, languageshort, languagelong, subtitles_list):
    """Fetches subtitles from the SubDL API and adds them to subtitles_list."""
    
    API_KEY = get_subdl_api()
    if not API_KEY:
        print("Error: SubDL API key is missing.")
        return

    params = {
        "api_key": API_KEY,
        "file_name": searchstring,
        "type": "tv",
        "imdb_id": None,
        "season_number": season,
        "episode_number": episode,
        #"year": year,
        "languages": languageshort,
        "subs_per_page": 50
        }

    response = requests.get(SEARCH_URL, params=params)
    json_data = response.json()
    print(json.dumps(json_data, indent=4))
    #print(json.dumps(json_data, indent=4))
    status = json_data["status"]
    if (status == True):
        try:
            all_subs_data = json_data["subtitles"]
            #print(json.dumps(all_subs_data, indent=4))
            for item in all_subs_data:
                try:
                    language = item["lang"]
                    filename = item["release_name"]
                    sync = False
                    id = item["url"]
                    link = (DOWNLOAD_URL) + id
                    print(language , filename , sync , id , link)
                    subtitles_list.append({'filename': filename, 'sync': False, 'id' : id, 'language_flag': languageshort, 'language_name': languagelong})
                except:
                    pass
        except json.JSONDecodeError:
            print("Error: Failed to decode JSON response.")
    return


def search_subtitles(file_original_path, title, tvshow, year, season, episode, set_temp, rar, lang1, lang2, lang3, stack): #standard input
    languagefound = lang1
    language_info = get_language_info(languagefound)
    language_info1 = language_info['name']
    language_info2 = language_info['2et']
    language_info3 = language_info['3et']

    subtitles_list = []
    msg = ""   

    if len(tvshow) == 0 and year: # Movie
        searchstring = "%s (%s)" % (title, year)
        print(("searchstring", searchstring))
        get_subtitles_list_movie(searchstring, title, language_info2, language_info1, subtitles_list)
    elif len(tvshow) > 0 and title == tvshow: # Movie not in Library
        print(len(tvshow))
        #searchstring = "%s (%#02d%#02d)" % (tvshow, int(season), int(episode))
        searchstring = "%s" % (tvshow)
        print(("searchstring", searchstring))
        get_subtitles_list_tv(searchstring, tvshow, season, episode, language_info2, language_info1, subtitles_list)
    elif len(tvshow) > 0: # TVShow
        searchstring = "%s S%#02dE%#02d" % (tvshow, int(season), int(episode))
        print(("searchstring", searchstring))
        get_subtitles_list_tv(searchstring, tvshow, season, episode, language_info2, language_info1, subtitles_list)
    else:
        searchstring = title.replace(' ', '+').lower()
        print(("searchstring", searchstring))
        get_subtitles_list_movie(searchstring, title, language_info2, language_info1, subtitles_list)
    #get_subtitles_list(searchstring, title, language_info2, language_info1, subtitles_list)
    return subtitles_list, "", msg #standard output


def download_subtitles(subtitles_list, pos, zip_subs, tmp_sub_dir, sub_folder, session_id):
    subtitle_id = subtitles_list[pos]["id"]
    language = subtitles_list[pos]["language_name"]
    download_url = DOWNLOAD_URL  + subtitle_id
    response = requests.get(download_url, stream=True)
    local_tmp_file = zip_subs
    packed = False
    subs_file = ""

    if response.status_code == 200:
        os.makedirs(tmp_sub_dir, exist_ok=True)
        with open(local_tmp_file, 'wb') as file:
            for chunk in response.iter_content(chunk_size=1024):
                if chunk:
                    file.write(chunk)
        
        with open(local_tmp_file, "rb") as f:
            header = f.read(2)
            if header.startswith(b'R'):
                packed = True
                subs_file = "rar"
            elif header.startswith(b'P'):
                packed = True
                subs_file = "zip"
            else:
                subs_file = local_tmp_file
    
    return packed, language, subs_file
