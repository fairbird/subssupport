# -*- coding: utf-8 -*-

from __future__ import absolute_import, print_function
import os
import re
import requests
import random
import json
import warnings
from bs4 import BeautifulSoup
from six.moves.urllib.parse import quote_plus
from requests.packages.urllib3.exceptions import InsecureRequestWarning

warnings.simplefilter('ignore', InsecureRequestWarning)
user_agents = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Linux; Android 11; SM-G991B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Mobile Safari/537.36",
    "Mozilla/5.0 (iPhone; CPU iPhone OS 15_2 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/15.2 Mobile/15E148 Safari/604.1"
]

# Function to get a random User-Agent string
def get_random_ua():
    return random.choice(user_agents)

session = requests.Session()

# Set headers for the request
session.headers.update({
    "User-Agent": get_random_ua(),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
    "Accept-Language": "en-US,en;q=0.9,ar-EG;q=0.8,ar;q=0.7",
    "Referer": "https://www.subtitlecat.com/",
})

main_url = "https://www.subtitlecat.com"

def getSearchTitle(title, year=None):
    url = f'{main_url}/index.php?search={quote_plus(title)}'
    print(("url_getSearchTitle", url))
    response = session.get(url, verify=False)
    return response.url  # Return final URL

def getallsubs(response):
    soup = BeautifulSoup(response.text, 'html.parser')
    subtitles = []
    
    for row in soup.find_all('tr'):
        link_tag = row.find('a')
        if link_tag:
            title = link_tag.text.strip()
            href = main_url + "/" + link_tag['href'].strip()
            download_count = row.find_all('td')[-2].text.strip() if len(row.find_all('td')) > 2 else "0"
            languages = row.find_all('td')[-1].text.strip() if len(row.find_all('td')) > 1 else "Unknown"
            
            subtitles.append({
                'filename': title,
                'link': href,
                'downloads': download_count,
                'language_name': languages,
                'sync': False  # Fix KeyError by always adding this key
            })
    
    return subtitles

def search_movie(title, year, languages, filename):
    url = getSearchTitle(title, year)
    print(("url_search_movie", url))
    response = session.get(url, verify=False)
    
    if response.status_code == 200:
        return getallsubs(response)
    return []

def search_tvshow(tvshow, season, episode, languages, filename):
    search_query = f"{tvshow} S{int(season):02d}E{int(episode):02d}"
    return search_movie(search_query, None, languages, filename)

def search_manual(searchstr, languages, filename):
    return search_movie(searchstr, None, languages, filename)

def search_subtitles(file_original_path, title, tvshow, year, season, episode, set_temp, rar, lang1, lang2, lang3, stack):
    if tvshow:
        return search_tvshow(tvshow, season, episode, [lang1, lang2, lang3], file_original_path), "", ""
    elif title:
        return search_movie(title, year, [lang1, lang2, lang3], file_original_path), "", ""
    else:
        return search_manual(title, [lang1, lang2, lang3], file_original_path), "", ""

def get_real_srt_links(page_url):
    """
    Extracts only ready-to-download subtitles (.srt links) from a subtitle page.
    """
    response = requests.get(page_url, verify=False)
    if response.status_code != 200:
        return []  # Return empty if fetching page fails

    soup = BeautifulSoup(response.text, 'html.parser')
    srt_links = []

    # Find all available subtitles (ignores translation-needed ones)
    for sub_single in soup.find_all('div', class_='sub-single'):
        language = sub_single.find_all('span')[1].text.strip()
        download_tag = sub_single.find('a', class_='green-link')

        if download_tag:
            download_link = "https://www.subtitlecat.com" + download_tag['href']
            srt_links.append({"language": language, "download_link": download_link})

    return srt_links  # Returns only valid SRT links


def download_subtitles(subtitles_list, pos, zip_subs, tmp_sub_dir, sub_folder, session_id):
    """
    Downloads a subtitle file. If the provided link is a page, it extracts the real SRT file link first.
    """
    page_url = subtitles_list[pos]["link"]  # This is a page, not a direct .srt file

    # Step 1: Extract the real .srt link
    srt_links = get_real_srt_links(page_url)  # Fetch all available SRT files

    if not srt_links:
        raise Exception("No downloadable SRT file found")

    # Step 2: Choose the first available SRT file (assuming the user picks the first result)
    srt_download_link = srt_links[0]["download_link"]
    language = srt_links[0]["language"]

    # Step 3: Download the subtitle file
    subtitle_response = requests.get(srt_download_link, verify=False)
    if subtitle_response.status_code != 200:
        raise Exception("Failed to download subtitle file")

    # Step 4: Define file path and save the subtitle
    file_name = srt_download_link.split("/")[-1]  # Extract filename from URL
    file_path = os.path.join(tmp_sub_dir, file_name)

    with open(file_path, 'wb') as file:
        file.write(subtitle_response.content)

    return False, language, file_path  # Standard return format for Enigma2 plugin

