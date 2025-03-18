# -*- coding: utf-8 -*-
from __future__ import absolute_import
from __future__ import print_function
import requests , random
import json
import re, os
from bs4 import BeautifulSoup
from six.moves.urllib.parse import quote_plus
from .YtssubsUtilities import geturl, get_language_info
from ..utilities import log
import base64


USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Linux; Android 11; SM-G991B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Mobile Safari/537.36",
    "Mozilla/5.0 (iPhone; CPU iPhone OS 15_2 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/15.2 Mobile/15E148 Safari/604.1"
]

def get_random_ua():
    return random.choice(USER_AGENTS)
HDR = {
    "accept": "application/json, text/plain, */*",
    "accept-language": "en-US,en;q=0.9",
    "content-type": "application/json",
    "priority": "u=1, i",
    "User-Agent": get_random_ua()
    }
HDRDL = {
    "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
    "accept-language": "en-US,en;q=0.9",
    "content-type": "application/x-www-form-urlencoded",
    "priority": "u=1, i",
    "User-Agent": get_random_ua()
    }
session = requests.Session()

session.headers.update({
    "accept": "application/json, text/plain, */*",
    "accept-language": "en-US,en;q=0.9",
    "Referer": "https://yifysubtitles.ch",
    "User-Agent": get_random_ua()
})

BASE_URL = "https://yifysubtitles.ch"
debug_pretext = ""
def prepare_search_string(s):
    s = s.replace("'", "").strip()
    s = re.sub(r'\(\d\d\d\d\)$', '', s)  # remove year from title
    s = s.replace(" :",":")
    print(("s_title", s))
    return s

def getallsubs(html_content, allowed_languages, filename=""):
    """ Extract subtitle links from YIFYSubtitles.ch subtitle page with multiple filenames """
    subtitles = []
    
    soup = BeautifulSoup(html_content, "html.parser")
    subtitle_rows = soup.select("tr[data-id]")  # Select subtitle rows
    
    for row in subtitle_rows:
        try:
            # Extract language
            language = row.select_one("td.flag-cell span.sub-lang").text.strip()

            # Extract download page link
            subtitle_link_tag = row.select_one("td a[href^='/subtitles/']")
            if not subtitle_link_tag:
                continue  # Skip if no valid link

            subtitle_page_link = subtitle_link_tag["href"]
            
            # Ensure correct `<br>` splitting, even if first two names are joined
            subtitle_names = re.split(r"<br\s*/?>", subtitle_link_tag.decode_contents(), flags=re.IGNORECASE)

            # Match language to the correct format
            language_info = get_language_info(language)
            if not language_info or language_info["name"] not in allowed_languages:
                continue

            # Add each subtitle variant separately
            for subtitle_name in subtitle_names:
                subtitle_name = BeautifulSoup(subtitle_name, "html.parser").text.strip()  # Clean HTML tags
                subtitle_name = re.sub(r"^subtitle\s*", "", subtitle_name, flags=re.IGNORECASE)  # Remove "subtitle" only at the start
                subtitle_name = re.sub(r"^\.+", "", subtitle_name)  # Remove leading dots (e.g., ".Moana" -> "Moana")

                if subtitle_name:
                    subtitles.append({
                        "filename": subtitle_name,
                        "sync": False,  # No sync info available
                        "link": BASE_URL + subtitle_page_link,
                        "language_name": language_info["name"],
                        "lang": language_info
                    })

        except Exception as e:
            print(f"Skipping subtitle due to error: {e}")
            continue

    return subtitles

def split_movie_title(movie_entry):
    """Extracts movie name and year from the API response."""
    movie_title = movie_entry.get("movie", "").strip()
    match = re.search(r"^(.*)\s+(\d{4})$", movie_title)  # Match "Title YYYY"

    if match:
        return match.group(1).strip(), match.group(2)  # (Movie Name, Year)
    return movie_title, None  # Return title as-is if no year found

def search_movie(title, year, languages, filename):
    """ Search for a movie on YIFYSubtitles.ch and retrieve subtitles """
    movie_title = prepare_search_string(title)
    try:
        # Prepare search URL
        search_url = f"https://yifysubtitles.ch/ajax/search/?mov={movie_title}"
        response = requests.get(search_url, headers=HDR, timeout=10)

        if response.status_code != 200:
            print(f"Error: Failed to fetch search results for '{movie_title}'")
            return []

        movies = response.json()
        if not movies:
            print(f"No results found for '{movie_title}'")
            return []

        # Try to find an exact year match
        best_match = None
        for movie in movies:
            movie_name, movie_year = split_movie_title(movie)
            if movie_year and movie_year == str(year):  # Exact match
                best_match = movie
                break  # Stop at first perfect match

        if not best_match:
            print(f"No exact year match found, selecting first result.")
            best_match = movies[0]  # Fallback to the first result if no exact match

        imdb_code = best_match.get("imdb")
        if not imdb_code:
            print(f"No IMDb code found for '{movie_title}'")
            return []

        # Fetch subtitles for the selected movie
        movie_url = f"https://yifysubtitles.ch/movie-imdb/{imdb_code}"
        movie_page = requests.get(movie_url, headers=HDR, timeout=10)

        if movie_page.status_code != 200:
            print(f"Error: Failed to fetch subtitle page for '{movie_title}'")
            return []

        return getallsubs(movie_page.text, languages, filename)

    except Exception as error:
        print(f"Error in search_movie: {error}")
        return []




def search_tvshow(title, season, episode, languages, filename):
    """ Search for a movie on YTS-Subs and retrieve subtitles """
    tv_title = prepare_search_string(title)
    try:
        # Search for the movie
        search_url = f"{BASE_URL}/search/ajax/{tv_title}"
        response = requests.get(search_url, headers=HDR, timeout=10)

        if response.status_code != 200:
            print(f"Error: Failed to fetch search results for '{tv_title}'")
            return []

        movies = response.json()
        if not movies:
            print(f"No results found for '{tv_title}'")
            return []

        # Select the best-matching movie (first result)
        selected_movie = movies[0]
        imdb_code = selected_movie.get("mov_imdb_code")
        if not imdb_code:
            print(f"No IMDb code found for '{tv_title}'")
            return []

        # Fetch subtitles for the selected movie
        movie_url = f"{BASE_URL}/movie-imdb/{imdb_code}"
        movie_page = requests.get(movie_url, timeout=10)

        if movie_page.status_code != 200:
            print(f"Error: Failed to fetch subtitle page for '{tv_title}'")
            return []

        return getallsubs(movie_page.text, languages, filename)

    except Exception as error:
        print(f"Error in search_movie: {error}")
        return []

def search_subtitles(file_original_path, title, tvshow, year, season, episode, set_temp, rar, lang1, lang2, lang3, stack):  # standard input
    log(__name__, "%s Search_subtitles = '%s', '%s', '%s', '%s', '%s', '%s', '%s', '%s', '%s', '%s', '%s', '%s'" %
         (debug_pretext, file_original_path, title, tvshow, year, season, episode, set_temp, rar, lang1, lang2, lang3, stack))
    if lang1 == 'Farsi':
        lang1 = 'Persian'
    if lang2 == 'Farsi':
        lang2 = 'Persian'
    if lang3 == 'Farsi':
        lang3 = 'Persian'
    if tvshow:
        sublist = search_tvshow(tvshow, season, episode, [lang1, lang2, lang3], file_original_path)
    elif title:
        sublist = search_movie(title, year, [lang1, lang2, lang3], file_original_path)
    else:
        try:
          sublist = search_manual(title, [lang1, lang2, lang3], file_original_path)
        except:
            print("error")
    return sublist, "", ""



import os
import requests
from bs4 import BeautifulSoup

def download_subtitles(subtitles_list, pos, zip_subs, tmp_sub_dir, sub_folder, session_id):
    """ Download selected subtitle (ZIP/RAR) from scraped link """
    try:
        subtitle = subtitles_list[pos]
        subtitle_page_url = subtitle["link"]  # Page containing the download link
        language = subtitle["language_name"]

        print(("subtitle_page_url", subtitle_page_url))

        # Fetch the subtitle details page
        response = requests.get(subtitle_page_url, headers=HDR, timeout=10)
        if response.status_code != 200:
            print(f"Error: Failed to fetch subtitle page {subtitle_page_url}")
            return False, "", ""

        # Parse HTML to extract direct download link
        soup = BeautifulSoup(response.text, "html.parser")
        download_button = soup.select_one("a.btn-icon.download-subtitle")

        if not download_button:
            print("Error: Could not find the download button.")
            return False, "", ""

        download_link = download_button.get("href")
        if not download_link:
            print("Error: No download link found.")
            return False, "", ""

        # Convert relative link to absolute URL
        if not download_link.startswith("http"):
            download_link = BASE_URL + download_link

        print(("download_link", download_link))

        # Download the subtitle file
        subtitle_response = requests.get(download_link, timeout=10, stream=True)
        if subtitle_response.status_code != 200:
            print(f"Error: Failed to download subtitle from {download_link}")
            return False, "", ""

        # Save subtitle file as ZIP/RAR
        os.makedirs(tmp_sub_dir, exist_ok=True)
        local_tmp_file = zip_subs

        with open(local_tmp_file, "wb") as f:
            for chunk in subtitle_response.iter_content(chunk_size=1024):
                if chunk:
                    f.write(chunk)

        # Detect file format (RAR/ZIP/SRT)
        packed = False
        subs_file = ""

        with open(local_tmp_file, "rb") as f:
            header = f.read(2)
            if header.startswith(b'R'):
                packed = True
                subs_file = "rar"
            elif header.startswith(b'P'):
                packed = True
                subs_file = "zip"
            else:
                subs_file = local_tmp_file  # Assume SRT if neither ZIP nor RAR

        return packed, language, subs_file

    except Exception as e:
        print(f"Error downloading subtitle: {e}")
        return False, "", ""
