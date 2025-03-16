# -*- coding: UTF-8 -*-
import sys
import os
import re
import json
import requests
from urllib.parse import quote_plus, unquote
from requests.packages.urllib3.exceptions import InsecureRequestWarning
from ..utilities import languageTranslate, log, getFileSize
from ..seeker import SubtitlesDownloadError, SubtitlesErrors

# Suppress insecure request warnings
requests.packages.urllib3.disable_warnings(InsecureRequestWarning)

# Constants
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 6.1; rv:109.0) Gecko/20100101 Firefox/115.0',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
    'Accept-Language': 'fr,fr-FR;q=0.8,en-US;q=0.5,en;q=0.3',
    'Content-Type': 'text/html; charset=UTF-8',
    'Host': 'subs.ath.cx',
    'Referer': 'http://subs.ath.cx',
    'Upgrade-Insecure-Requests': '1',
    'Connection': 'keep-alive',
    'Accept-Encoding': 'gzip, deflate'
}

SESSION = requests.Session()
MAIN_URL = "http://subs.ath.cx"
DEBUG_PRETEXT = "subs.ath.cx"

def get_url(url, referer=None):
    headers = {'User-Agent': HEADERS['User-Agent']}
    if referer:
        headers['Referer'] = referer
    
    response = SESSION.get(url, headers=headers, verify=False)
    return response.text.replace('\n', '')

def get_rating(downloads):
    return min(10, max(1, downloads // 50 + 1))

def search_subtitles(file_path, title, tvshow, year, season, episode, set_temp, rar, lang1, lang2, lang3, stack):
    subtitles_list = []
    msg = ""
    
    title = re.sub(r'[:,"&!?-]', '', title).replace("  ", " ").title()
    print(title)
    if tvshow:
        search_string = f"{tvshow} S{int(season):02d}E{int(episode):02d}" if title != tvshow else f"{tvshow} ({int(season):02d}{int(episode):02d})"
    else:
        search_string = f"{title} ({year})" if year else title
    
    log(__name__, f"{DEBUG_PRETEXT} Search string = {search_string}")
    get_subtitles_list(title, search_string, "ar", "Arabic", subtitles_list)
    return subtitles_list, "", msg

def download_subtitles(subtitles_list, pos, zip_subs, tmp_sub_dir, sub_folder, session_id):
    subtitle_info = subtitles_list[pos]
    language = subtitle_info["language_name"]
    subtitle_id = subtitle_info["id"]
    
    # Construct download link
    download_link = f"http://subs.ath.cx/subtitles/{subtitle_id}"
    log(__name__, f"{DEBUG_PRETEXT} Downloading from: {download_link}")

    try:
        response = SESSION.get(download_link, headers=HEADERS, verify=False, allow_redirects=True)
        response.raise_for_status()  # Ensure the request was successful
    except requests.RequestException as e:
        log(__name__, f"{DEBUG_PRETEXT} Download failed: {e}")
        return False, language, None  # Return failure

    # Ensure tmp directory exists
    os.makedirs(tmp_sub_dir, exist_ok=True)

    # Save file
    local_tmp_file = os.path.join(tmp_sub_dir, subtitle_id)  # Use proper filename
    try:
        with open(local_tmp_file, "wb") as file:
            file.write(response.content)

        log(__name__, f"{DEBUG_PRETEXT} Subtitles saved to: {local_tmp_file}")
    except Exception as e:
        log(__name__, f"{DEBUG_PRETEXT} Error saving subtitle: {e}")
        return False, language, None  # Return failure

    # Check file type (RAR, ZIP, or SRT)
    packed = False
    subs_file = local_tmp_file
    try:
        with open(local_tmp_file, "rb") as file:
            file_header = file.read(2).decode(errors="ignore")
            if file_header.startswith("R"):
                packed = True
                subs_file = "rar"
            elif file_header.startswith("PK"):
                packed = True
                subs_file = "zip"
            else:
                subs_file = local_tmp_file  # It's an SRT file
    except Exception as e:
        log(__name__, f"{DEBUG_PRETEXT} Error checking file type: {e}")
    
    log(__name__, f"{DEBUG_PRETEXT} Returning: packed={packed}, language={language}, subs_file={subs_file}")
    return packed, language, subs_file  # Standard output


def get_subtitles_list(title, search_string, lang_short, lang_long, subtitles_list):
    url = f'{MAIN_URL}/subtitles'
    log(__name__, f"{DEBUG_PRETEXT} Fetching: {url}")
    
    try:
        content = SESSION.get(url, headers=HEADERS, verify=False).text
    except requests.RequestException as e:
        log(__name__, f"{DEBUG_PRETEXT} Failed to fetch subtitles: {e}")
        return
    
    try:
        encoded_title = quote_plus(title).replace('+', '.')
        subtitles = re.findall(rf'(<td><a href.+?>{encoded_title}.+?</a></td>)', content, re.IGNORECASE)
        
        for subtitle in subtitles:
            match = re.search(r'<td><a href="(.+?)">(.+?)</a></td>', subtitle)
            if match:
                id_, filename = match.groups()
                filename = filename.replace('.srt', '').strip()
                if filename not in ['Εργαστήρι Υποτίτλων', 'subs4series']:
                    log(__name__, f"{DEBUG_PRETEXT} Found subtitle: {filename} (id = {id_})")
                    subtitles_list.append({
                        'no_files': 1,
                        'filename': filename,
                        'sync': True,
                        'id': id_,
                        'language_flag': f'flags/{lang_short}.gif',
                        'language_name': lang_long
                    })
    except Exception as e:
        log(__name__, f"{DEBUG_PRETEXT} Error parsing subtitles: {e}")
