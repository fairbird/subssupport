# -*- coding: UTF-8 -*-
from __future__ import absolute_import

import os
import re
import requests
from .OpenSubtitles2Utilities import get_language_info
import os.path
import http.client
import json
import sys
from bs4 import BeautifulSoup
from urllib.request import HTTPCookieProcessor, build_opener, install_opener, Request, urlopen
from urllib.parse import urlencode
from ..utilities import languageTranslate, getFileSize, log
from ..seeker import SubtitlesDownloadError, SubtitlesErrors


HDR = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 6.1; rv:109.0) Gecko/20100101 Firefox/115.0',
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
    print(f"API Key: {API_KEY}, Username: {USERNAME}, Password: {PASSWORD}")
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
    print(languagefound)
    language_info = get_language_info(languagefound)
    language_info1 = language_info['name']
    language_info2 = language_info['2et']
    language_info3 = language_info['3et']

    subtitles_list = []
    msg = ""

    if len(tvshow) == 0 and year:  # Movie
        searchstring = "%s (%s)" % (title, year)
    elif len(tvshow) > 0 and title == tvshow:  # Movie not in Library
        searchstring = "%s (%#02d%#02d)" % (tvshow, int(season), int(episode))
    elif len(tvshow) > 0:  # TVShow
        searchstring = "%s S%#02dE%#02d" % (tvshow, int(season), int(episode))
    else:
        searchstring = title
    log(__name__, "%s Search string = %s" % (debug_pretext, searchstring))
    get_subtitles_list(searchstring, language_info2, language_info1, subtitles_list)
    return subtitles_list, "", msg  # standard output


def download_subtitles(subtitles_list, pos, zip_subs, tmp_sub_dir, sub_folder, session_id, session=None):
    """Download subtitles and show remaining downloads as a message."""
    token = get_opensubtitles_token()
    global settings_provider
    API_KEY = settings_provider.getSetting("OpenSubtitles_API_KEY")
    
    language = subtitles_list[pos]["language_name"]
    file_id = subtitles_list[pos]["id"]
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
        download_url = data.get("link")
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
        #postparams = { '__EVENTTARGET': 's$lc$bcr$downloadLink', '__EVENTARGUMENT': '' , '__VIEWSTATE': viewstate, '__PREVIOUSPAGE': previouspage, 'subtitleId': subtitleid, 'typeId': typeid, 'filmId': filmid}
        postparams = urlencode({'__EVENTTARGET': 's$lc$bcr$downloadLink', '__EVENTARGUMENT': '', '__VIEWSTATE': viewstate, '__PREVIOUSPAGE': previouspage, 'subtitleId': subtitleid, 'typeId': typeid, 'filmId': filmid})
        #class MyOpener(urllib.FancyURLopener):
            #version = 'User-Agent=Mozilla/5.0 (Windows NT 6.1; rv:109.0) Gecko/20100101 Firefox/115.0'
        #my_urlopener = MyOpener()
        #my_urlopener.addheader('Referer', url)
        log(__name__, "%s Fetching subtitles using url with referer header '%s' and post parameters '%s'" % (debug_pretext, downloadlink, postparams))
        #response = my_urlopener.open(downloadlink, postparams)
        response = s.get(downloadlink, data=postparams, headers=HDR, verify=False, allow_redirects=True)
        #print(response.content)
        local_tmp_file = zip_subs
        try:
            log(__name__, "%s Saving subtitles to '%s'" % (debug_pretext, local_tmp_file))
            if not os.path.exists(tmp_sub_dir):
                os.makedirs(tmp_sub_dir)
            local_file_handle = open(local_tmp_file, 'wb')
            local_file_handle.write(response.content)
            local_file_handle.close()
            # Check archive type (rar/zip/else) through the file header (rar=Rar!, zip=PK) urllib3.request.urlencode
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


def get_subtitles_list(searchstring, languageshort, languagelong, subtitles_list):
    print('searchstring_original:', searchstring)
    search_string = searchstring.lower().replace(" ", "+").replace(".", "_dot_")
    #search_string = searchstring.lower().replace(":", "-").replace(" ", "-").replace(".", "_dot_")
    print('search_string:', search_string)
    lang = languageshort
    
    url = '%s/fr/%s/search-all/q-%s/hearing_impaired-include/machine_translated-/trusted_sources-' % (main_url, lang, search_string)
    print('url', url)

    try:
        log(__name__, "%s Getting url: %s" % (debug_pretext, url))
        print(url)
        content = requests.get(url, timeout=10)
        soup = BeautifulSoup(content.text, "html.parser").tbody
        rows = soup.find_all("tr")

        # Initialize a list to store the scraped data
        scraped_data = []

        # Loop through each row
        for row in rows:
            # Extract subtitle name (use only the desktop view text)
            subtitle_name_tag = row.find('span', {'class': 'hidden md:block'})
            if subtitle_name_tag:
                subtitle_name = subtitle_name_tag.text.strip()
            else:
                subtitle_name = None
            
            # Extract number of downloads
            downloads_tag = row.find('a', {'title': 'téléchargé'})
            if downloads_tag:
                downloads = downloads_tag.text.strip()
            else:
                downloads = None
            
            # Extract file_id from the download link
            download_link = row.find('a', {'class': 'ddl_trigger_no'})
            if download_link:
                file_id = download_link['href'].split('/nocache/download/')[1].split('/')[0]
            else:
                file_id = None
            
            # Append the data to the list
            scraped_data.append({
                'subtitle_name': subtitle_name,
                'downloads': downloads,
                'file_id': file_id
            })
            
            id = file_id
            filename = subtitle_name
            downloads = downloads
            print(id)
            print(filename)
            print(downloads)
            
            try:
                rating = get_rating(downloads)
                #print(rating)
            except:
                rating = 0
                pass
            if not downloads == 0:
                log(__name__, "%s Subtitles found: %s (id = %s)" % (debug_pretext, filename, id))
                subtitles_list.append({'rating': str(rating), 'no_files': 1, 'filename': filename, 'sync': False, 'id': id, 'language_flag': 'flags/' + languageshort + '.gif', 'language_name': languagelong})

        # Print the scraped data
        #for data in scraped_data:
            #print(f"Subtitle Title: {data['Subtitle Title']}")
            #print(f"Download Link: {data['Download Link']}")
            #print("-" * 40)
    except:
        pass

