import requests
import os
import re, json
from urllib.parse import quote_plus
from ..utilities import log
from .FoursubUtilities import get_language_info
from ..seeker import SubtitlesDownloadError, SubtitlesErrors
from bs4 import BeautifulSoup
import re


# URLs
HOMEPAGE_URL = "https://www.4subscene.com/"
SEARCH_URL = "https://www.4subscene.com/search"
SUBTITLES_URL = "https://www.4subscene.com/media_subtitles"
DOWNLOAD_URL = "https://www.4subscene.com/download?subtitle_id="
debug_pretext = ""

def get_csrf_token(session):
    """Fetch CSRF token from homepage."""
    response = session.get(HOMEPAGE_URL)
    if response.status_code == 200:
        soup = BeautifulSoup(response.text, "html.parser")
        token_input = soup.find("input", {"name": "_token"})
        return token_input["value"] if token_input else None
    return None

def search_subtitles(file_original_path, title, tvshow, year, season, episode, set_temp, rar, lang1, lang2, lang3, stack):
    log(__name__, "Starting search_subtitles - title: %s, tvshow: %s, season: %s, episode: %s" % (title, tvshow, season, episode))
    
    languages = [lang1, lang2, lang3]
    languages = [lang for lang in languages if lang]  # Remove empty values
    
    if tvshow:
        return search_tvshow(tvshow, int(season), int(episode), languages, file_original_path), "", ""
    elif title:
        return search_movie(title, year, languages, file_original_path), "", ""
    else:
        return [], "", ""

def search_movie(title, year, languages, filename):
    """Search for movie subtitles."""
    log(__name__, "Searching movie: %s, Year: %s" % (title, year))
    return search_media(title, languages)

def search_tvshow(title, season, episode, languages, filename):
    """Search for TV show subtitles and filter by season/episode."""
    log(__name__, "Searching TV show: %s, Season: %d, Episode: %d" % (title, season, episode))
    subtitles = search_media(title, languages)
    
    # Filter results to match season and episode
    filtered_subs = []
    for sub in subtitles:
        release_info = sub['filename']
        log(__name__, "Checking release_info: %s" % release_info)
        
        match = re.search(r"S(\d{1,2})E(\d{1,2})", release_info, re.IGNORECASE)
        if match:
            sub_season, sub_episode = int(match.group(1)), int(match.group(2))
            log(__name__, "Extracted - Season: %d, Episode: %d" % (sub_season, sub_episode))
            if sub_season == season and sub_episode == episode:
                log(__name__, "Matched subtitle: %s" % release_info)
                filtered_subs.append(sub)
    
    if not filtered_subs:
        log(__name__, "No matching subtitles found for S%02dE%02d" % (season, episode))
    
    return filtered_subs

def search_media(title, languages):
    """Generic function to search for subtitles on 4Subscene."""
    session = requests.Session()
    csrf_token = get_csrf_token(session)
    if not csrf_token:
        log(__name__, "Failed to retrieve CSRF token.")
        return []
    
    subtitles_list = []
    search_data = {
        "_token": csrf_token,
        "keyword": title,
        "search_in": "subtitle"
    }
    response = session.post(SEARCH_URL, data=search_data)
    if response.status_code != 200:
        log(__name__, "Search request failed with status: %d" % response.status_code)
        return []
    
    results = response.json()
    if not results.get("success"):
        log(__name__, "No results found for: %s" % title)
        return []
    
    soup = BeautifulSoup(results["html"], "html.parser")
    media_ids = [link["href"].split("/")[-1] for link in soup.find_all("a", href=True) if "/media/" in link["href"]]
    if not media_ids:
        log(__name__, "No media IDs found for: %s" % title)
        return []
    
    for media_id in media_ids:
        for lang in languages:
            log(__name__, "Fetching subtitles for media ID: %s, Language: %s" % (media_id, lang))
            subtitles_list.extend(get_subtitles_for_media(session, csrf_token, media_id, lang))
    
    return subtitles_list

def get_subtitles_for_media(session, csrf_token, media_id, language):
    """Fetch available subtitles for a given media ID."""
    log(__name__, "Fetching subtitles for media ID: %s, Language: %s" % (media_id, language))
    subtitles = []
    data = {
        "_token": csrf_token,
        "media_id": media_id,
        "subtitle_language": language,
        "length": 25
    }
    response = session.post(SUBTITLES_URL, data=data)
    if response.status_code == 200:
        json_data = response.json()
        for item in json_data.get("data", []):
            subtitles.append({
                'filename': item.get("release_info", "Unknown"),
                'id': item["id"],
                'language_flag': language,
                'language_name': language.capitalize(),
                'sync': False
            })
    return subtitles


def download_subtitles(subtitles_list, pos, zip_subs, tmp_sub_dir, sub_folder, session_id):
    """Download subtitle file from 4Subscene and handle different formats."""
    subtitle_id = subtitles_list[pos]["id"]
    download_url = f"{DOWNLOAD_URL}{subtitle_id}"
    response = requests.get(download_url)
    
    if response.status_code == 200:
        json_data = response.json()
        if "file_path" in json_data and "file_name" in json_data:
            file_url = json_data["file_path"]
            file_name = json_data["file_name"]
            
            os.makedirs(tmp_sub_dir, exist_ok=True)
            local_file_path = os.path.join(tmp_sub_dir, file_name)
            
            file_response = requests.get(file_url, stream=True)
            if file_response.status_code == 200:
                with open(local_file_path, 'wb') as file:
                    for chunk in file_response.iter_content(chunk_size=1024):
                        file.write(chunk)
                
                if file_name.endswith(".rar"):
                    return True, subtitles_list[pos]["language_name"], local_file_path
                elif file_name.endswith(".zip"):
                    return True, subtitles_list[pos]["language_name"], local_file_path
                else:
                    return False, subtitles_list[pos]["language_name"], local_file_path
    
    return False, "", ""