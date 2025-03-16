# -*- coding: utf-8 -*-

from __future__ import absolute_import
from __future__ import print_function
import difflib  # For fuzzy matching
from bs4 import BeautifulSoup
from .SubsourceUtilities import geturl, get_language_info
from six.moves import html_parser
from six.moves.urllib.request import FancyURLopener
from six.moves.urllib.parse import quote_plus, urlencode
from ..utilities import log
import html
import urllib3
import os, requests , json, re, random, string, time, warnings
from requests.packages.urllib3.exceptions import InsecureRequestWarning
warnings.simplefilter('ignore',InsecureRequestWarning)

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
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

__api = "https://api.subsource.net/api/"

__getMovie = __api + "getMovie"
__getSub = __api + "getSub"
#__search = __api + "searchMovie"
__download = __api + "downloadSub/"
root_url = "https://subsource.net/subtitles/"
main_url = "https://subsource.net"
      
s = requests.Session()      
debug_pretext = ""
ses = requests.Session()
# Seasons as strings for searching  </div>
# Seasons as strings for searching
seasons = ["Specials", "First", "Second", "Third", "Fourth", "Fifth", "Sixth", "Seventh", "Eighth", "Ninth", "Tenth"]
seasons = seasons + ["Eleventh", "Twelfth", "Thirteenth", "Fourteenth", "Fifteenth", "Sixteenth", "Seventeenth",
                     "Eighteenth", "Nineteenth", "Twentieth"]
seasons = seasons + ["Twenty-first", "Twenty-second", "Twenty-third", "Twenty-fourth", "Twenty-fifth", "Twenty-sixth",
                     "Twenty-seventh", "Twenty-eighth", "Twenty-ninth"]

# Don't remove it we need it here
subsource_languages = {
    'Chinese BG code': 'Chinese',
    'Brazillian Portuguese': 'Portuguese (Brazil)',
    'Serbian': 'SerbianLatin',
    'Ukranian': 'Ukrainian',
    'Farsi/Persian': 'Persian'
}
    
def getSearchTitle(title, year=None):
    url = __api + "searchMovie"
    params = {"query": prepare_search_string(title)}
    
    try:
        content = requests.post(url, headers=HDR, data=json.dumps(params), timeout=10).text
        response_json = json.loads(content)
    except Exception as e:
        print(f"Error fetching search results: {e}")
        return None

    if response_json.get("success"):
        found_movies = response_json.get("found", [])
        for res in found_movies:
            try:
                name = res.get('title')
                release_year = res.get('releaseYear')
                linkName = res.get('linkName')
                
                if not linkName:
                    continue  # Skip if no linkName
                
                print(f"Found: {name} ({release_year}) -> {linkName}")
                return linkName

            except KeyError as e:
                print(f"Missing key: {e}")
                continue  # Continue to the next result if one fails

    print("FAILED")
    return None  # Ensure None is returned if nothing is found

def getSearchTitle_tv(title):
    url = __api + "searchMovie"
    params = {"query": prepare_search_string(title)}
    
    print(f"Searching for: {params}")  # Debugging step

    try:
        content = requests.post(url, headers=HDR, data=json.dumps(params), timeout=10).text
        response_json = json.loads(content)
    except Exception as e:
        print(f"Error fetching search results: {e}")
        return None

    if response_json.get("success"):
        found_shows = response_json.get("found", [])

        print(f"Total API Results: {len(found_shows)}")

        # Print raw API titles before filtering
        raw_titles = [show["title"] for show in found_shows]
        print(f"Raw API Returned Titles ({len(raw_titles)}): {raw_titles}")

        # Filter only TV shows
        tv_shows = [show for show in found_shows if show.get("type") == "TVSeries"]
        all_titles = [show["title"] for show in tv_shows]

        print(f"Filtered TV Shows ({len(all_titles)}): {all_titles}")

        # Select the best match for "Prison Break"
        best_match = next((show for show in tv_shows if show["title"].strip().lower() == title.strip().lower()), None)

        if best_match:
            name = best_match["title"]
            linkName = best_match["linkName"]
            seasons = best_match.get("seasons", [])

            if not linkName or not seasons:
                print("No valid linkName or seasons found!")
                return None

            # Extract valid seasons
            seasons_list = {s["number"]: s["id"] for s in seasons if s["number"] is not None}

            print(f"Matched TV Show: {name} -> {linkName}, Seasons: {seasons_list}")
            return {"title": linkName, "seasons": seasons_list}

    print("FAILED: No matching TV show found.")
    return None                             

def getallsubs(content, allowed_languages, filename="", search_string=""):
    response_json = json.loads(content)
    success = response_json['success']
    year = response_json['movie']['year']
    all_subs = response_json['subs']
    i = 0
    subtitles = []
    if (success == True):
        for sub in all_subs:
            fullLink = sub['fullLink']
            languagefound = sub['lang']
            sub_id = sub['subId']
            language_info = get_language_info(languagefound)
            print(('language_info', language_info))
            if language_info and language_info['name'] in allowed_languages:
                link = main_url + fullLink
                print(('link', link))
                linkName = sub['linkName']
                filename = sub['releaseName']
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
                else:
                    subtitles.append({'filename': subtitle_name, 'sync': sync, 'link': link, 'language_name': language_info['name'], 'lang': language_info, 'sub_id':sub_id, 'linkName':linkName, 'year':year})
                    i = i + 1

        subtitles.sort(key=lambda x: [not x['sync']])
        return subtitles
    else:
        print("FAILED")

def prepare_search_string(s):
    s = s.replace("'", "").strip()
    s = re.sub(r'\(\d\d\d\d\)$', '', s)  # remove year from title
    s = quote_plus(s).replace("+"," ")
    return s
    
def search_movie(title, year, languages, filename):
    try:
        movie_title = prepare_search_string(title)
        if year:
            movie_title = f"{movie_title} {year}"  # Append year to improve matching
        print(("movie_title", movie_title))

        linkName = getSearchTitle(movie_title, year)  # Now includes year in the query
        print(("linkName", linkName))

        if not linkName:
            print(f"No match found for {title} ({year})")
            return []

        url = root_url + linkName
        print(("true url", url))
        params = {"movieName": linkName}

        content = requests.post(__getMovie, headers=HDR, data=json.dumps(params), timeout=10).text
        if content:
            _list = getallsubs(content, languages, filename)
            print(("_list", _list))
            return _list
        else:
            return []

    except Exception as error:
        print(("error", error))
        return []

def search_tvshow(title, season, episode, languages, filename):
    try:
        title = title.strip()
        print(("title_search_tvshow", title))
        search_result = getSearchTitle_tv(title)
        print(("search_result", search_result))

        if not search_result:
            print(f"TV Show '{title}' not found.")
            return []

        linkName = search_result["title"]
        seasons = search_result["seasons"]

        season = int(season)  # Ensure season is an integer

        if season not in seasons:
            print(f"Season {season} not found for {title}. Available seasons: {list(seasons.keys())}")
            return []

        season_id = seasons[season]
        print(f"Using Season ID: {season_id} for {title} Season {season}")

        # Fix the season format in the request payload
        params = {
            "langs": [],
            "movieName": linkName,
            "season": f"season-{season}"  # Correct API format
        }
        
        try:
            content = s.post(__getMovie, headers=HDR, data=json.dumps(params), timeout=10).text
            response_json = json.loads(content)
        except requests.exceptions.Timeout:
            print(f"Timeout occurred when fetching subtitles for {title} Season {season}. Retrying once...")
            try:
                content = s.post(__getMovie, headers=HDR, data=json.dumps(params), timeout=15).text
                response_json = json.loads(content)
            except requests.exceptions.Timeout:
                print(f"Failed again due to timeout.")
                return []

        if content and response_json.get("success"):
            return getallsubs(content, languages, filename)

        return []

    except Exception as error:
        print(f"Error in search_tvshow: {error}")
        return []

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

def download_subtitles (subtitles_list, pos, zip_subs, tmp_sub_dir, sub_folder, session_id):  # standard input
    sub_id = subtitles_list[pos][ "sub_id" ]
    language = subtitles_list[pos][ "language_name" ]
    linkName = subtitles_list[pos][ "linkName" ]
    print(("sub_id", sub_id))
    print(("language", language))
    print(("linkName", linkName))
    params = {"movie":linkName,"lang":language,"id":sub_id}
    content = requests.post(__getSub, headers=HDR , data=json.dumps(params), timeout=10).text
    response_json = json.loads(content)
    success = response_json['success']
    if (success == True):
        fileName = response_json['sub']['fileName']
        downloadToken = response_json['sub']['downloadToken']
        downloadlink = __download + downloadToken
        print(("downloadlink", downloadlink))
        local_tmp_file = fileName
        print(("local_tmp_file", local_tmp_file))
        log(__name__ , "%s Downloadlink: %s " % (debug_pretext, downloadlink))
        viewstate = 0
        previouspage = 0
        subtitleid = 0
        typeid = "zip"
        filmid = 0
        postparams = { '__EVENTTARGET': 's$lc$bcr$downloadLink', '__EVENTARGUMENT': '' , '__VIEWSTATE': viewstate, '__PREVIOUSPAGE': previouspage, 'subtitleId': subtitleid, 'typeId': typeid, 'filmId': filmid}
        log(__name__ , "%s Fetching subtitles using url '%s' with referer header '%s' and post parameters '%s'" % (debug_pretext, downloadlink, main_url, postparams))
        response = requests.get(downloadlink,data=postparams,headers=HDRDL,verify=False,allow_redirects=True) 
        local_tmp_file = zip_subs
        try:
            log(__name__ , "%s Saving subtitles to '%s'" % (debug_pretext, local_tmp_file))
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
                log(__name__ , "Discovered RAR Archive")
            else:
                myfile.seek(0)
                if (myfile.read(1).decode('utf-8') == 'P'):
                    typeid = "zip"
                    packed = True
                    log(__name__ , "Discovered ZIP Archive")
                else:
                    typeid = "srt"
                    packed = False
                    subs_file = local_tmp_file
                    log(__name__ , "Discovered a non-archive file")
            myfile.close()
            log(__name__ , "%s Saving to %s" % (debug_pretext, local_tmp_file))
        except:
            log(__name__ , "%s Failed to save subtitle to %s" % (debug_pretext, local_tmp_file))
        if packed:
            subs_file = typeid
        log(__name__ , "%s Subtitles saved to '%s'" % (debug_pretext, local_tmp_file))
        return packed, language, subs_file  # standard output

