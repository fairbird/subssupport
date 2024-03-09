# -*- coding: utf-8 -*-
'''
Created 2021

@author: Franc
'''
from __future__ import absolute_import
from ..utilities import languageTranslate, log
import json, requests, re

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
	("SerbianLatin" , "36",	 "sr",	 "scc",	  "100",  30237, "SrpskiLatinica")) #?

def languageTranslate(lang, lang_from, lang_to):
	for x in LANGUAGES:
		if lang == x[lang_from]:
			return x[lang_to]

class OSDBServer:
	#KEY = "UGE4Qk0tYXNSMWEtYTJlaWZfUE9US1NFRC1WRUQtWA=="
	def search_subtitles(self, name, tvshow, season, episode, lang, year):

		subtitles_list = []
		if len(tvshow) > 1:		#SAMO SERIJE DOLAZE U OBZIR
			name = tvshow
		else:
			return

		#FORMATIRAJ U STRING KOJI CE PRIJEVODI-ONLINE RAZUMJETI
		season = "%01d" % (int(season))
		episode = "%01d" % (int(episode))

		search_string = name
		search_string = search_string.lower()
		first_char = search_string[0]
		#-----------------------------------------------------------------------------------
		#-----------------------------------------------------------------------------------
		#BASIC PARAMS
		api_url = "https://www.prijevodi-online.org"
		#-----------------------------------------------------------------------------------
		#-----------------------------------------------------------------------------------
		#START
		try:
			#IDI NA ABECEDU, TJ. PRVO SLOVO TRAZENOG STRINGA
			response = requests.post('{0}/serije/index/{1}'.format(api_url, first_char))
			if response.status_code == requests.codes.ok:
				data = response.content
				if type(data) is bytes:
					data = data.decode("utf-8", "ignore")
					data = data.lower()
				raw = re.findall('<td class="naziv"><a href="(.*?)" title="{0}">{0}</a></td>'.format(search_string), data)
				url = ''.join(raw)
				url = '{0}{1}'.format(api_url, url)
				
				if url != "":
					#IZVADI TOKEN
					response = requests.get(url)
					data = response.content
					if type(data) is bytes:
						data = data.decode("utf-8", "ignore")
					data = ' '.join(data.split())
					raw = re.findall("epizode.key = '(.*?)';", data)
					token = ''.join(raw)
				
					#BROJI SVE SEZONE 
					broj_sezona = re.findall('<h3 id="sezona-.*?">.*?</h3>', data)
					duzina = str(len(broj_sezona))
					#IZVADI TRAZENU SEZONU U BLOCK. ALI AKO JE ZADNJA SEZONA ONDA MORAS POSTAVITI REGEX DRUGACIJE
					if season == duzina:	#ZADNJA SEZONA NA STRANICI
						block = re.findall('<h3 id="sezona-.*?">Sezona ' + season + '</h3>(.*?)<script type="text/javascript">', data)
					else:
						block = re.findall('<h3 id="sezona-.*?">Sezona ' + season + '</h3>(.*?)<h3', data)
					block = ' '.join(block)
					if block == "": return subtitles_list

					#IZVADI SVE LINKOVE 
					raw = re.findall('<li class="broj">' + episode + '.</li> <li class="naziv"> <a class="open" rel="(.*?)"', block)
					url = ''.join(raw)
					if url == '':
						return
					url = '{0}{1}'.format(api_url, url)

					#KRENI PO PRAVE DOWNLOAD LINKOVE
					param = {'key': token}
					response = requests.post(url, data=param)
					data = response.content
					if type(data) is bytes:
						data = data.decode("utf-8", "ignore")
						
					if response.status_code == requests.codes.ok:
						raw = re.findall('<a href="(.*?)"', data)
						for (url) in raw:
							release = url.rsplit('/', 1)[-1]
							lang_id = release.rsplit('-', 1)[-1]
							link = '{0}{1}'.format(api_url, url)

							if lang_id != "razno":
								lang_name = languageTranslate((lang_id),2,0)		#Hrvatski --> Croatian, itd..
								flag_image = lang_id
							else:
								lang_name = ""
								flag_image = ""
								
							format = "srt"

							subtitles_list.append({'filename': release,
															'link': link,
															'language_name': lang_name,
															'language_id': lang_id,
															'language_flag': flag_image,
															'movie': release,
															'ID': "who cares",
															'rating': "i dont care",
															'format': format,
															'sync': False,
															'hearing_imp': False
															})

		except:
			return subtitles_list
		return subtitles_list
