# -*- coding: UTF-8 -*-
from __future__ import absolute_import

import os
import re
import requests
from .OpenSubtitles2Utilities import get_language_info
import os.path
import http.client
import json, random
import sys
from urllib.request import HTTPCookieProcessor, build_opener, install_opener, Request, urlopen
from urllib.parse import urlencode
from ..utilities import languageTranslate, getFileSize, log
from ..seeker import SubtitlesDownloadError, SubtitlesErrors

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Linux; Android 11; SM-G991B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Mobile Safari/537.36",
    "Mozilla/5.0 (iPhone; CPU iPhone OS 15_2 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/15.2 Mobile/15E148 Safari/604.1"
]

def get_random_ua():
    return random.choice(USER_AGENTS)
HDR = {
    "User-Agent": get_random_ua(),
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
    'Accept-Language': 'fr,fr-FR;q=0.8,en-US;q=0.5,en;q=0.3',
    'Content-Type': 'text/html; charset=UTF-8',
    'Host': 'www.opensubtitles.com',
    'Referer': 'https://www.opensubtitles.com',
    'Upgrade-Insecure-Requests': '1',
    'Connection': 'keep-alive',
    'Accept-Encoding': 'gzip, deflate'
}

s = requests.Session()

main_url = "https://www.opensubtitles.com"
debug_pretext = "opensubtitles.com"


BASE_URL = "https://api.opensubtitles.com/api/v1"

def get_opensubtitles_token():
    """Authenticate and get JWT token using credentials from SettingsProvider."""
    global settings_provider  # Ensure we're using the existing instance
    
    API_KEY = settings_provider.getSetting("OpenSubtitles_API_KEY")
    USERNAME = settings_provider.getSetting("OpenSubtitles_username")
    PASSWORD = settings_provider.getSetting("OpenSubtitles_password")
    #print(f"API Key: {API_KEY}, Username: {USERNAME}, Password: {PASSWORD}")
    if not API_KEY or not USERNAME or not PASSWORD:
        print("Error: Missing OpenSubtitles credentials.")
        return None

    url = f"{BASE_URL}/login"
    payload = {"username": USERNAME, "password": PASSWORD}
    headers = {
        "Content-Type": "application/json",
        "User-Agent": "odemdownloader v1.0",
        "Accept": "application/json",
        "Api-Key": API_KEY,
    }

    try:
        response = requests.post(url, json=payload, headers=headers)
        response.raise_for_status()
        data = response.json()
        return data.get("token")
    except requests.exceptions.RequestException as e:
        print("Error getting token:", e)
        return None

def get_url(url, referer=None):
    if referer is None:
        headers = {'User-agent': 'Mozilla/5.0 (Windows NT 6.1; WOW64; rv:6.0) Gecko/20100101 Firefox/6.0'}
    else:
        headers = {'User-agent': 'Mozilla/5.0 (Windows NT 6.1; WOW64; rv:6.0) Gecko/20100101 Firefox/6.0', 'Referer': referer}
    req = Request(url, None, headers)
    response = urlopen(req)
    content = response.read().decode('utf-8')
    response.close()
    content = content.replace('\n', '')
    return content


def get_rating(downloads):
    rating = int(downloads)
    if (rating < 50):
        rating = 1
    elif (rating >= 50 and rating < 100):
        rating = 2
    elif (rating >= 100 and rating < 150):
        rating = 3
    elif (rating >= 150 and rating < 200):
        rating = 4
    elif (rating >= 200 and rating < 250):
        rating = 5
    elif (rating >= 250 and rating < 300):
        rating = 6
    elif (rating >= 300 and rating < 350):
        rating = 7
    elif (rating >= 350 and rating < 400):
        rating = 8
    elif (rating >= 400 and rating < 450):
        rating = 9
    elif (rating >= 450):
        rating = 10
    return rating


def search_subtitles(file_original_path, title, tvshow, year, season, episode, set_temp, rar, lang1, lang2, lang3, stack):  # standard input
    languagefound = lang1
    #print(languagefound)
    language_info = get_language_info(languagefound)
    language_info1 = language_info['name']
    language_info2 = language_info['2et']
    language_info3 = language_info['3et']

    subtitles_list = []
    msg = ""

    if len(tvshow) == 0 and year:  # Movie
        searchstring = "%s (%s)" % (title, year)
        #print(("searchstring", searchstring))
        get_subtitles_list_movie(searchstring, language_info2, language_info1, subtitles_list)
    elif len(tvshow) > 0 and title == tvshow:  # Movie not in Library
        searchstring = "%s" % (tvshow)
        #print(("searchstring", searchstring))
        get_subtitles_list_tv(searchstring, tvshow, season, episode, language_info2, language_info1, subtitles_list)
    elif len(tvshow) > 0:  # TVShow
        searchstring = "%s S%#02dE%#02d" % (tvshow, int(season), int(episode))
        #print(("searchstring", searchstring))
        get_subtitles_list_tv(searchstring, tvshow, season, episode, language_info2, language_info1, subtitles_list)
    else:
        searchstring = title
        #print(("searchstring", searchstring))
        get_subtitles_list_movie(searchstring, language_info2, language_info1, subtitles_list)
    log(__name__, "%s Search string = %s" % (debug_pretext, searchstring))
    #get_subtitles_list(searchstring, language_info2, language_info1, subtitles_list)
    return subtitles_list, "", msg  # standard output


def download_subtitles(subtitles_list, pos, zip_subs, tmp_sub_dir, sub_folder, session_id, session=None):
    """Download subtitles and show remaining downloads as a message."""
    token = get_opensubtitles_token()
    global settings_provider
    API_KEY = settings_provider.getSetting("OpenSubtitles_API_KEY")
    #print(f"API_KEY_down: {API_KEY}")
    language = subtitles_list[pos]["language_name"]
    #print(f"language_down: {language}")
    file_id = subtitles_list[pos]["id"]
    #print(f"file_id_down: {file_id}")
    url = f"{BASE_URL}/download"
    
    headers = {
        "Authorization": f"Bearer {token}",
        "Api-Key": API_KEY,
        "Accept": "application/json",
    }
    payload = {"file_id": file_id}

    try:
        response = requests.post(url, json=payload, headers=headers)
        response.raise_for_status()
        data = response.json()
        #print(json.dumps(data, indent=4))
        download_url = data.get("link")
        #print(f"download_url: {download_url}")
        remaining_downloads = data.get("remaining")
        print(f"remaining_downloads: {remaining_downloads}")


    except requests.exceptions.RequestException as e:
        log(__name__, f"Error downloading subtitle: {e}")
        return None

        
    downloadlink = download_url
    if downloadlink:
        #print(downloadlink)
        log(__name__, "%s Downloadlink: %s " % (debug_pretext, downloadlink))
        viewstate = 0
        previouspage = 0
        subtitleid = 0
        typeid = "zip"
        filmid = 0
        postparams = urlencode({'__EVENTTARGET': 's$lc$bcr$downloadLink', '__EVENTARGUMENT': '', '__VIEWSTATE': viewstate, '__PREVIOUSPAGE': previouspage, 'subtitleId': subtitleid, 'typeId': typeid, 'filmId': filmid})
        log(__name__, "%s Fetching subtitles using url with referer header '%s' and post parameters '%s'" % (debug_pretext, downloadlink, postparams))
        response = s.get(downloadlink, data=postparams, headers=HDR, verify=False, allow_redirects=True)
        local_tmp_file = zip_subs
        try:
            log(__name__, "%s Saving subtitles to '%s'" % (debug_pretext, local_tmp_file))
            if not os.path.exists(tmp_sub_dir):
                os.makedirs(tmp_sub_dir)
            local_file_handle = open(local_tmp_file, 'wb')
            local_file_handle.write(response.content)
            local_file_handle.close()
            myfile = open(local_tmp_file, "rb")
            myfile.seek(0)
            if (myfile.read(1).decode('utf-8') == 'R'):
                typeid = "rar"
                packed = True
                log(__name__, "Discovered RAR Archive")
            else:
                myfile.seek(0)
                if (myfile.read(1).decode('utf-8') == 'P'):
                    typeid = "zip"
                    packed = True
                    log(__name__, "Discovered ZIP Archive")
                else:
                    typeid = "srt"
                    packed = False
                    subs_file = local_tmp_file
                    log(__name__, "Discovered a non-archive file")
            myfile.close()
            log(__name__, "%s Saving to %s" % (debug_pretext, local_tmp_file))
        except:
            log(__name__, "%s Failed to save subtitle to %s" % (debug_pretext, local_tmp_file))
        if packed:
            subs_file = typeid
        log(__name__, "%s Subtitles saved to '%s'" % (debug_pretext, local_tmp_file))
        return packed, language, subs_file  # standard output


def get_subtitles_list_movie(searchstring, languageshort, languagelong, subtitles_list):
    """Fetch subtitle list for movies from OpenSubtitles API."""
    
    token = get_opensubtitles_token()
    if not token:
        print("Error: Failed to authenticate with OpenSubtitles API.")
        return

    global settings_provider
    API_KEY = settings_provider.getSetting("OpenSubtitles_API_KEY")

    url = f"{BASE_URL}/subtitles"
    params = {
        "query": searchstring,
        "type": "movie",  # Explicitly specify movie type
        "languages": languageshort
    }
    headers = {
        "Authorization": f"Bearer {token}",
        "Api-Key": API_KEY,
        "Accept": "application/json",
    }

    try:
        response = requests.get(url, params=params, headers=headers)
        response.raise_for_status()
        data = response.json()

        # Extract subtitles from the response
        for subtitle in data.get("data", []):
            attributes = subtitle.get("attributes", {})
            feature_details = attributes.get("feature_details", {})
            uploader = attributes.get("uploader", {})
            files = attributes.get("files", [])

            file_id = files[0]["file_id"] if files else None
            #print(f"file_id: {file_id}")
            filename = attributes.get("release", "Unknown")
            download_count = attributes.get("download_count", 0)
            rating = get_rating(download_count)
            imdb_id = feature_details.get("imdb_id", "N/A")
            tmdb_id = feature_details.get("tmdb_id", "N/A")
            uploader_name = uploader.get("name", "Anonymous")
            upload_date = attributes.get("upload_date", "Unknown")
            subtitle_url = attributes.get("url", "")

            subtitles_list.append({
                "rating": str(rating),
                "no_files": len(files),
                "filename": filename,
                "sync": False,
                "id": file_id,
                "language_flag": f"flags/{languageshort}.gif",
                "language_name": languagelong,
                "imdb_id": imdb_id,
                "tmdb_id": tmdb_id,
                "uploader": uploader_name,
                "upload_date": upload_date,
                "url": subtitle_url
            })
            log(__name__, f"{debug_pretext} Subtitles found: {filename} (id = {file_id})")

    except requests.exceptions.RequestException as e:
        log(__name__, f"Error fetching subtitles: {e}")


def get_subtitles_list_tv(searchstring, tvshow, season, episode, languageshort, languagelong, subtitles_list):
    """Fetch subtitle list for TV episodes from OpenSubtitles API."""
    
    token = get_opensubtitles_token()
    if not token:
        print("Error: Failed to authenticate with OpenSubtitles API.")
        return

    global settings_provider
    API_KEY = settings_provider.getSetting("OpenSubtitles_API_KEY")

    url = f"{BASE_URL}/subtitles"
    params = {
        "query": tvshow,  # Use only the TV show title
        "type": "episode",  # Specify TV episode search
        "season_number": season,
        "episode_number": episode,
        "languages": languageshort
    }
    headers = {
        "Authorization": f"Bearer {token}",
        "Api-Key": API_KEY,
        "Accept": "application/json",
    }

    try:
        response = requests.get(url, params=params, headers=headers)
        response.raise_for_status()
        data = response.json()

        # Extract subtitles from the response
        for subtitle in data.get("data", []):
            attributes = subtitle.get("attributes", {})
            feature_details = attributes.get("feature_details", {})
            uploader = attributes.get("uploader", {})
            files = attributes.get("files", [])

            file_id = files[0]["file_id"] if files else None
            #print(f"file_id: {file_id}")
            filename = attributes.get("release", "Unknown")
            download_count = attributes.get("download_count", 0)
            rating = get_rating(download_count)
            imdb_id = feature_details.get("imdb_id", "N/A")
            tmdb_id = feature_details.get("tmdb_id", "N/A")
            parent_title = feature_details.get("parent_title", "Unknown Show")
            upload_date = attributes.get("upload_date", "Unknown")
            subtitle_url = attributes.get("url", "")

            subtitles_list.append({
                "rating": str(rating),
                "no_files": len(files),
                "filename": filename,
                "sync": False,
                "id": file_id,
                "language_flag": f"flags/{languageshort}.gif",
                "language_name": languagelong,
                "imdb_id": imdb_id,
                "tmdb_id": tmdb_id,
                "tv_show": parent_title,
                "season": season,
                "episode": episode,
                "upload_date": upload_date,
                "url": subtitle_url
            })
            log(__name__, f"{debug_pretext} Subtitles found: {filename} (id = {file_id})")

    except requests.exceptions.RequestException as e:
        log(__name__, f"Error fetching subtitles: {e}")


