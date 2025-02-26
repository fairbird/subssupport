# -*- coding: utf-8 -*-

from __future__ import absolute_import
from __future__ import print_function
import difflib
import os
import re
import string
import zipfile
from ..seeker import SubtitlesDownloadError, SubtitlesErrors
from bs4 import BeautifulSoup
from .Sub_sceneUtilities import geturl, get_language_info
from six.moves import html_parser
from six.moves.urllib.request import FancyURLopener
from six.moves.urllib.parse import quote_plus, urlencode
from ..utilities import log
import html
import urllib3
import requests, re
import requests , json, re,random,string,time,warnings
from requests.packages.urllib3.exceptions import InsecureRequestWarning
from six.moves import html_parser
warnings.simplefilter('ignore',InsecureRequestWarning)


HDR= {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/133.0.0.0 Safari/537.36',
      'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
      'Accept-Language': 'fr,fr-FR;q=0.8,en-US;q=0.5,en;q=0.3',
      'Upgrade-Insecure-Requests': '1',
      'Content-Type': 'application/x-www-form-urlencoded',
      'Referer': 'https://sub-scene.com',
      'Connection': 'keep-alive',
      'Accept-Encoding':'gzip, deflate'}
      
s = requests.Session()      
main_url = "https://sub-scene.com"
debug_pretext = ""
ses = requests.Session()
# Seasons as strings for searching  </div>
# Seasons as strings for searching
seasons = ["Specials", "First", "Second", "Third", "Fourth", "Fifth", "Sixth", "Seventh", "Eighth", "Ninth", "Tenth"]
seasons = seasons + ["Eleventh", "Twelfth", "Thirteenth", "Fourteenth", "Fifteenth", "Sixteenth", "Seventeenth",
                     "Eighteenth", "Nineteenth", "Twentieth"]
seasons = seasons + ["Twenty-first", "Twenty-second", "Twenty-third", "Twenty-fourth", "Twenty-fifth", "Twenty-sixth",
                     "Twenty-seventh", "Twenty-eighth", "Twenty-ninth"]

movie_season_pattern = ("<a href=\"(?P<link>/subscene/[^\"]*)\">(?P<title>[^<]+)\((?P<year>\d{4})\)</a>\s+"
                        "<div class=\"subtle count\">\s*(?P<numsubtitles>\d+\s+subtitles)</div>\s+")

# Don't remove it we need it here
subscenebest_languages = {
    'Chinese BG code': 'Chinese',
    'Brazillian Portuguese': 'Portuguese (Brazil)',
    'Serbian': 'SerbianLatin',
    'Ukranian': 'Ukrainian',
    'Farsi/Persian': 'Persian'
}

def geturl(url):
    log(__name__, " Getting url: %s" % (url))
    try:
        response = urllib.request.urlopen(url)
        content = response.read()
        print(content)
    except:
        log(__name__, " Failed to get url:%s" % (url))
        content = None
    return(content)


def getSearchTitle(title, year=None): ## new Add
    url = 'https://sub-scene.com/search?query=%s' % quote_plus(title)
    #data = geturl(url)
    data = requests.get(url,headers=HDR,verify=False,allow_redirects=True).content
    data = data.decode('utf-8')
    div1 = data.split('<footer>')
    div1.pop(1)
    div1 = str(div1)
    div2 = div1.split('class="search-result"')
    div2.pop(0)
    middle_part = str(div2)
    blocks = middle_part.split('class="title"')
    blocks.pop(0)
    list1 = []
    for block in blocks:
        regx = '''<a href="(.*?)">(.*?)</a>'''
        try:
            matches = re.findall(regx, block)
            name = matches[0][1]
            href = matches[0][0]
            print(("hrefxxx", href))
            print(("yearxx", year))
            href = 'https://sub-scene.com' + href
            if year and year == '':
              if "/subscene/" in href:
                  return href
            if not year:
              if "/subscene/" in href:
                  return href
            if year and str(year) in name:
                if "/subscene/" in href:
                   print(("href", href))
                   return href
                   

        except:
            break                             
    return 'https://sub-scene.com/search?query=' + quote_plus(title)

def find_movie(content, title, year):
    url_found = None
    h = html_parser.HTMLParser()
    for matches in re.finditer(movie_season_pattern, content, re.IGNORECASE | re.DOTALL):
        print((tuple(matches.groups())))
        found_title = matches.group('title')
        found_title = html.unescape(found_title) 
        print(("found_title", found_title))  
        log(__name__, "Found movie on search page: %s (%s)" % (found_title, matches.group('year')))
        if found_title.lower().find(title.lower()) > -1:
            if matches.group('year') == year:
                log(__name__, "Matching movie found on search page: %s (%s)" % (found_title, matches.group('year')))
                url_found = matches.group('link')
                print(url_found)
                break
    return url_found


def find_tv_show_season(content, tvshow, season):
    url_found = None
    possible_matches = []
    all_tvshows = []

    season_pattern = "<a href=\"(?P<link>/subscene/[^\"]*)\">(?P<title>[^<]+)</a>\s*"
    for matches in re.finditer(season_pattern, content, re.IGNORECASE | re.DOTALL):
        found_title = matches.group('title')
        #found_title = html.unescape(found_title)
        print(("found_title2", found_title)) 
        log(__name__, "Found tv show season on search page: %s" % found_title)
        url_found = matches.group('link')
                                                                   
    return url_found                                                                     

def getallsubs(content, allowed_languages, filename="", search_string=""):
    soup = BeautifulSoup(content.text, 'html.parser')
    block = soup.find('tbody')
    
    # Check if block is None (no movies found)
    if block is None:
        log(__name__, "No movies found in the content.")
        return []
    
    movies = block.find_all("tr")
    i = 0
    subtitles = []
    for movie in movies:
        #numfiles = 1
        #numfiles = movie.find('td', class_="a3").get_text(strip=True)
        movielink = movie.find('td', class_="a1").a.get("href")
        languagefound = movie.find('td', class_="a1").a.div.span.get_text(strip=True)
        language_info = get_language_info(languagefound)
        print(('language_info', language_info))
        if language_info and language_info['name'] in allowed_languages:
            link = main_url + movielink
            print(('link', link))
            filename = movie.find('td', class_="a1").a.div.find('span', class_="new").get_text(strip=True)
            subtitle_name = str(filename)
            print(('subtitle_name', subtitle_name))
            print(filename)
            rating = '0'
            sync = False
            if filename != "" and filename.lower() == subtitle_name.lower():
                sync = True
            if search_string != "":
                if subtitle_name.lower().find(search_string.lower()) > -1:
                    subtitles.append({'filename': subtitle_name, 'sync': sync, 'link': link,
                                     'language_name': language_info['name'], 'lang': language_info})
                    i = i + 1
                #elif numfiles > 2:
                    #subtitle_name = subtitle_name + ' ' + ("%d files" % int(matches.group('numfiles')))
                    #subtitles.append({'rating': rating, 'filename': subtitle_name, 'sync': sync, 'link': link, 'language_name': language_info['name'], 'lang': language_info, 'comment': comment})
                #i = i + 1
            else:
                subtitles.append({'filename': subtitle_name, 'sync': sync, 'link': link, 'language_name': language_info['name'], 'lang': language_info})
                i = i + 1

    subtitles.sort(key=lambda x: [not x['sync']])
    return subtitles


def prepare_search_string(s):
    s = s.replace("'", "").strip()
    s = re.sub(r'\(\d\d\d\d\)$', '', s)  # remove year from title
    s = quote_plus(s)
    return s

def getimdbid(title):
    # Search query (movie name)
    search_string = prepare_search_string(title)
    url = f"https://www.imdb.com/find/?q={search_string}&s=tt"

    # Set headers to mimic a browser visit
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    }

    # Send request to IMDb
    response = requests.get(url, headers=headers)

    # Parse HTML with BeautifulSoup
    soup = BeautifulSoup(response.text, 'html.parser')
    #print(f"soup: {soup}")
    # Extract first search result
    result = soup.find('a', href=True, class_='ipc-metadata-list-summary-item__t')

    if result:
        movie_link = result['href']
        movie_id = movie_link.split('/')[2]  # Extract 'tt20201748' from '/title/tt20201748/'
        movie_title = result.text.strip()

        print(f"Movie ID: {movie_id}")
        print(f"Title: {movie_title}")
        print(f"IMDb Link: https://www.imdb.com/title/{movie_id}/")
    else:
        print("Movie not found.")
    return movie_id

def search_movie(title, year, languages, filename):
    try:
        movie_id = getimdbid(title)
        print(("movie_id", movie_id))
        url2 = f"https://sub-scene.com/search?query={movie_id}"
        print(("true url", url2))
        content2 = requests.get(url2,headers=HDR,allow_redirects=True)
        soup = BeautifulSoup(content2.text, 'html.parser')
        block = soup.find('div', class_='search-result').find("a")
        movie_link = block.get("href")
        url = main_url + movie_link
        print("movie_url", url)
        content = requests.get(url,headers=HDR,allow_redirects=True)
        #content = geturl(url)

        
        if content != '':
            _list = getallsubs(content, languages, filename)
            #print(("_list", _list))
            return _list
        else:
            return []
    except Exception as error:
        print(("error", error))


def search_tvshow(tvshow, season, episode, languages, filename):
    tvshow = tvshow.strip()
    print(("tvshow", tvshow))
    movie_id = getimdbid(title)
    search_string = prepare_search_string(tvshow)
    #print(("search_string", search_string))
    search_string = search_string.replace("+"," ")
    print(("search_string", search_string))
    search_string += " - " + seasons[int(season)] + " Season"
    print(("search_string", search_string))

    log(__name__, "Search tvshow = %s" % search_string)
    url = main_url + "/search?query=" + quote_plus(search_string)
    print(("url", url))
    content = requests.get(url,headers=HDR,verify=False,allow_redirects=True).text
    print("content", content)
    if content is not None:
        log(__name__, "Multiple tv show seasons found, searching for the right one ...")
        tv_show_seasonurl = find_tv_show_season(content, tvshow, seasons[int(season)])
        if tv_show_seasonurl is not None:
            log(__name__, "Tv show season found in list, getting subs ...")
            url = main_url + tv_show_seasonurl
            print(("season_url", url))
            content = requests.get(url,headers=HDR,verify=False,allow_redirects=True)
            if content is not None:
                search_string = "s%#02de%#02d" % (int(season), int(episode))
                print(("search_string", search_string))
                return getallsubs(content, languages, filename)


def search_manual(searchstr, languages, filename):
    search_string = prepare_search_string(searchstr)
    url = main_url + "/subtitles/release?q=" + search_string + '&r=true'
    content, response_url = requests.get(url,headers=HDR,verify=False,allow_redirects=True).text

    if content is not None:
        return getallsubs(content, languages, filename)


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


def download_subtitles(subtitles_list, pos, zip_subs, tmp_sub_dir, sub_folder, session_id):  # standard input
    url = subtitles_list[pos]["link"]
    language = subtitles_list[pos]["language_name"]
    content = requests.get(url, headers=HDR, verify=False, allow_redirects=True).text

    downloadlink_pattern = '<!--<span><a class="button"\s+href="(.+)">'
    match = re.compile(downloadlink_pattern).findall(content)

    if match:
        downloadlink = match[0]
        print(("downloadlink", downloadlink))
        local_tmp_file = re.split("/file/", downloadlink)[1]
        print(("local_tmp_file", local_tmp_file))
        log(__name__, "%s Downloadlink: %s " % (debug_pretext, downloadlink))

        response = requests.get(downloadlink, headers=HDR, verify=False, allow_redirects=True)
        
        # Sanitize the filename to remove slashes
        sanitized_filename = re.sub(r'[\\/]', '_', zip_subs)
        local_tmp_file = os.path.join(tmp_sub_dir, sanitized_filename)

        try:
            log(__name__, "%s Saving subtitles to '%s'" % (debug_pretext, local_tmp_file))
            if not os.path.exists(tmp_sub_dir):
                os.makedirs(tmp_sub_dir)
            with open(local_tmp_file, 'wb') as local_file_handle:
                local_file_handle.write(response.content)

            # Initialize packed to False
            packed = False
            subs_file = local_tmp_file

            # Check archive type (rar/zip/else) through the file header
            with open(local_tmp_file, "rb") as myfile:
                header = myfile.read(4)  # Read the first 4 bytes to check for ZIP header
                if header == b'PK\x03\x04':  # ZIP file header
                    packed = True
                    typeid = "zip"
                    log(__name__, "Discovered ZIP Archive")
                else:
                    typeid = "srt"
                    packed = False
                    log(__name__, "Discovered a non-archive file")

            log(__name__, "%s Saving to %s" % (debug_pretext, local_tmp_file))
        except Exception as e:
            log(__name__, "%s Failed to save subtitle to %s" % (debug_pretext, local_tmp_file))
            raise SubtitlesDownloadError(SubtitlesErrors.UNKNOWN_ERROR, str(e))

        if packed:
            # Extract the ZIP file
            try:
                with zipfile.ZipFile(local_tmp_file, 'r') as zip_ref:
                    zip_ref.extractall(tmp_sub_dir)
                    log(__name__, "%s Extracted ZIP file to %s" % (debug_pretext, tmp_sub_dir))
                    # Get the first extracted file (assuming it's the subtitle file)
                    extracted_files = zip_ref.namelist()
                    if extracted_files:
                        subs_file = os.path.join(tmp_sub_dir, extracted_files[0])
                        log(__name__, "%s Extracted subtitle file: %s" % (debug_pretext, subs_file))
            except Exception as e:
                log(__name__, "%s Failed to extract ZIP file: %s" % (debug_pretext, str(e)))
                raise SubtitlesDownloadError(SubtitlesErrors.UNKNOWN_ERROR, str(e))

        log(__name__, "%s Subtitles saved to '%s'" % (debug_pretext, local_tmp_file))
        return packed, language, subs_file  # standard output
    else:
        log(__name__, "%s No download link found" % (debug_pretext))
        raise SubtitlesDownloadError(SubtitlesErrors.UNKNOWN_ERROR, "No download link found")