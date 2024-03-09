# -*- coding: utf-8 -*-
'''
Created 2021

@author: Franc
'''
from __future__ import absolute_import
from ..utilities import languageTranslate, log
import json, requests

LANGUAGES = (
	# Full Language name[0]
	# podnapisi[1]
	# ISO 639-1[2]
	# ISO 639-1 Code[3]
	# Script Setting Language[4]
	# localized name id number[5]
	# Localized Full Language name[6]
	("Bosnian"		, "10",	 "bs",	 "bos",	  "3",	  30204, "Bosanski"),
	("Croatian"		, "38",	 "hr",	 "hrv",	  "7",	  30208, "Hrvatski"),
	("English"		, "2",	 "en",	 "eng",	  "11",	  30212, "Engleski"),
	("Macedonian"	, "35",	 "mk",	 "mac",	  "28",	  30229, "Makedosnki"),
	("Serbian"		, "36",	 "sr",	 "scc",	  "36",	  30237, "Srpski"),
	("Slovenian"	, "1",	 "sl",	 "slv",	  "38",	  30239, "Slovenski"),
	("SerbianLatin" , "36",	 "sr",	 "scc",	  "100",  30237, "Srpski"), #?
	("BosnianLatin" , "10",	 "bs",	 "bos",	  "3",	  30204, "Bosanski")) #?



def get_user_pass():
	try:
		#OVO NE BUM RADILO! ZASTO? NEMAM IDEJU ZA SADA. No module named _enigma?
		#TODO: POGLEDATI SWIG!?
		# from Components.config import config
		# user = config.plugins.streamlordfnc.opensubtitlesusername.value
		# passw = config.plugins.streamlordfnc.opensubtitlesusername.value
		
		#ZATO, CITAJ KONFIGURACIJU KAO PLAIN TEXT/FILE, PA FILTRIRAJ QUERY. LUDO? DA, ALI...
		with open("/etc/enigma2/settings") as file:
			for line in file:
				parts = line.split("=") # split line into parts
				if len(parts) > 1:	 # if at least 2 parts/columns
					if line.startswith("config.plugins.subtitlesSupport.search.titlovi.password"):
						_PASSW = parts[1].replace("\n", "").strip()
					if line.startswith("config.plugins.subtitlesSupport.search.titlovi.username"):
						_USER = parts[1].replace("\n", "").strip()
	except:
		_PASSW = ""
		_USER = ""
	return _USER, _PASSW

def languageTranslate(lang, lang_from, lang_to):
	for x in LANGUAGES:
		if lang == x[lang_from]:
			return x[lang_to]

class OSDBServer:
	#KEY = "UGE4Qk0tYXNSMWEtYTJlaWZfUE9US1NFRC1WRUQtWA=="
	def search_subtitles(self, name, tvshow, season, episode, lang, year):
		subtitles_list = []
		search_params = {}
		if len(tvshow) > 1:
			name = tvshow
			
			#SEARCH PARAMS - DICTIONARY
			#OVA DVA SU ZA SERIJE:
			season = "%02d" % (int(season,))
			episode = "%02d" % (int(episode,))
			search_params['season'] = season
			search_params['episode'] = episode
			
		search_string = name
		#-----------------------------------------------------------------------------------
		#-----------------------------------------------------------------------------------
		#BASIC PARAMS
		username = ""
		password = ""
		api_url = "https://kodi.titlovi.com/api/subtitles"
		username, password = get_user_pass()
		login_params = {'username': username, 'password': password}
		#-----------------------------------------------------------------------------------
		#-----------------------------------------------------------------------------------
		#VIDI KOJE JEZIKE TREBA TRAZITI I ODMAH IH KONVERTIRAJ U NASKI DA TITLOVI.COM ZNA
		language_query = ""
		for i in range(len(lang)):
			language_query = language_query + "|" + languageTranslate((lang[i]),2,6)

		if language_query.startswith("|"):
			language_query = language_query[1:]	#IZBACI PRVI "|"
		#-----------------------------------------------------------------------------------
		#-----------------------------------------------------------------------------------
		#START LOGIN
		try:
			response = requests.post('{0}/gettoken'.format(api_url), params=login_params)
			if response.status_code == requests.codes.ok:
				resp_json = response.json()
				#U VARIJABLE PODATKE ZA SLIJEDECI REQUEST
				token = str(resp_json['Token'])
				user_name = str(resp_json['UserName'])
				user_id = str(resp_json['UserId'])
				expiration_date = str(resp_json['ExpirationDate'])
				#-----------------------------------------------------------------------------------
				search_language = language_query #"Hrvatski|Srpski|Bosanski|Makedonski|Slovenski|Engleski"
				search_params['lang'] = search_language
				search_params['query'] = search_string
				search_params['token'] = token
				search_params['userid'] = user_id
				search_params['json'] = True
				
				#KRENI U PRETRAGU. BEZ USER AGENTA, ZA SADA
				response = requests.get('{0}/search'.format(api_url), params=search_params)
				if response.status_code == requests.codes.ok:
					resp_json = response.json()
					subtitles = []
					if resp_json['SubtitleResults']:
						subtitles.extend(resp_json['SubtitleResults'])
						log(__name__, "Found titlovi.com subs: %s" % len(subtitles))

						try:
							type = result_item['Type']
						except:
							type = ""

						url_base = "https://titlovi.com/download/?type=1&mediaid=%s"

						for result_item in subtitles:
							movie = result_item['Title']

							try:
								link = str(result_item['Link'])
							except Exception as e:
								link = ""

							try:
								for i in range(len(subtitles)):
									lang_name = str(result_item['Lang'])
									lang_name = languageTranslate((lang_name),6,0)		#Hrvatski --> Croatian, etc..
									flag_image = languageTranslate((lang_name),0,2)			#Croatian ---> hr, etc...
							except Exception as e:
								flag_image = ""
								lang_name = ""

							try:
								year = str(result_item['Year'])
							except Exception as e:
								year = ""

							filename = str(result_item['Release'])
							filename = filename.split("/")
							
							if len(tvshow) < 1:			#Movies?
								if len(filename) > 1:
									filename = movie.replace(" ", ".") + "." + year + "." + str(filename[0]).replace(" ", ".")
								else:
									filename = movie.replace(" ", ".") + "." + year + "." + str(filename).replace(" ", ".").replace("['", "").replace("']", "")
							else:
								if len(filename) > 1:	#TV?
									filename = movie.replace(" ", ".") + ".s" + season + "e" + episode + "." + str(filename[0]).replace(" ", ".")
								else:
									filename = movie.replace(" ", ".") + ".s" + season + "e" + episode + "." + str(filename).replace(" ", ".").replace("['", "").replace("']", "")

							if filename.endswith("."): filename = filename[:-1]
								
							try:
								rating = str(result_item['Rating'])
							except Exception as e:
								rating = ""

							try:
								subtitle_id = str(result_item['Id'])
							except Exception as e:
								subtitle_id = ""

							lang_id = ''
							format = "srt"

							subtitles_list.append({'filename': filename,
															'link': link,
															'language_name': lang_name,
															'language_id': lang_id,
															'language_flag': flag_image,
															'movie': movie,
															'ID': subtitle_id,
															'rating': rating,
															'format': format,
															'sync': False,
															'hearing_imp': False
															})

		except:
			return subtitles_list
		return subtitles_list
