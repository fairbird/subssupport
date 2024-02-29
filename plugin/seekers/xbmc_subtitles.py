'''
Created on Feb 10, 2014

@author: marko
'''
from __future__ import absolute_import
import os
import time

from .seeker import BaseSeeker
from .utilities import languageTranslate, allLang

from . import _


class XBMCSubtitlesAdapter(BaseSeeker):
    module = None

    def __init__(self, tmp_path, download_path, settings=None, settings_provider=None, captcha_cb=None, delay_cb=None, message_cb=None):
        assert self.module is not None, 'you have to provide xbmc-subtitles module'
        logo = os.path.join(os.path.dirname(self.module.__file__), 'logo.png')
        BaseSeeker.__init__(self, tmp_path, download_path, settings, settings_provider, logo)
        self.module.captcha_cb = captcha_cb
        self.module.delay_cb = delay_cb
        self.module.message_cb = message_cb
        # xbmc-subtitles module can use maximum of three different languages
        # we will fill default languages from supported langs  in case no languages
        # were provided. If provider has more than 3 supported languages this just
        # gets first three languages in supported_langs list, so most of the time its
        # best to pass languages which will be used for searching
        if len(self.supported_langs) == 1:
            self.lang1 = self.lang2 = self.lang3 = languageTranslate(self.supported_langs[0], 2, 0)
        elif len(self.supported_langs) == 2:
            self.lang1 = languageTranslate(self.supported_langs[0], 2, 0)
            self.lang2 = languageTranslate(self.supported_langs[1], 2, 0)
            self.lang3 = self.lang1
        else:
            self.lang1 = languageTranslate(self.supported_langs[0], 2, 0)
            self.lang2 = languageTranslate(self.supported_langs[1], 2, 0)
            self.lang3 = languageTranslate(self.supported_langs[2], 2, 0)

    def _search(self, title, filepath, langs, season, episode, tvshow, year):
        file_original_path = filepath and filepath or ""
        title = title and title or file_original_path
        season = season if season else 0
        episode = episode if episode else 0
        tvshow = tvshow if tvshow else ""
        year = year if year else ""
        if len(langs) > 3:
            self.log.info('more then three languages provided, only first three will be selected')
        if len(langs) == 0:
            self.log.info('no languages provided will use default ones')
            lang1 = self.lang1
            lang2 = self.lang2
            lang3 = self.lang3
        elif len(langs) == 1:
            lang1 = lang2 = lang3 = languageTranslate(langs[0], 2, 0)
        elif len(langs) == 2:
            lang1 = lang3 = languageTranslate(langs[0], 2, 0)
            lang2 = languageTranslate(langs[1], 2, 0)
        elif len(langs) == 3:
            lang1 = languageTranslate(langs[0], 2, 0)
            lang2 = languageTranslate(langs[1], 2, 0)
            lang3 = languageTranslate(langs[2], 2, 0)
        self.log.info('using langs %s %s %s' % (lang1, lang2, lang3))
        self.module.settings_provider = self.settings_provider
        # Standard output -
        # subtitles list
        # session id (e.g a cookie string, passed on to download_subtitles),
        # message to print back to the user
        # return subtitlesList, "", msg
        subtitles_list, session_id, msg = self.module.search_subtitles(file_original_path, title, tvshow, year, season, episode, set_temp=False, rar=False, lang1=lang1, lang2=lang2, lang3=lang3, stack=None)
        return {'list': subtitles_list, 'session_id': session_id, 'msg': msg}

    def _download(self, subtitles, selected_subtitle, path=None):
        subtitles_list = subtitles['list']
        session_id = subtitles['session_id']
        pos = subtitles_list.index(selected_subtitle)
        zip_subs = os.path.join(self.tmp_path, selected_subtitle['filename'])
        tmp_sub_dir = self.tmp_path
        if path is not None:
            sub_folder = path
        else:
            sub_folder = self.tmp_path
        self.module.settings_provider = self.settings_provider
        # Standard output -
        # True if the file is packed as zip: addon will automatically unpack it.
        # language of subtitles,
        # Name of subtitles file if not packed (or if we unpacked it ourselves)
        # return False, language, subs_file
        compressed, language, filepath = self.module.download_subtitles(subtitles_list, pos, zip_subs, tmp_sub_dir, sub_folder, session_id)
        if compressed != False:
            if compressed == True or compressed == "":
                compressed = "zip"
            else:
                compressed = filepath
            if not os.path.isfile(filepath):
                filepath = zip_subs
        else:
            if isinstance(sub_folder, bytes):
                sub_folder = sub_folder.decode(encoding='utf-8', errors='strict')
            filepath = os.path.join(sub_folder, filepath)
        return compressed, language, filepath

    def close(self):
        try:
            del self.module.captcha_cb
            del self.module.message_cb
            del self.module.delay_cb
            del self.module.settings_provider
        except Exception:
            pass


try:
    from .Titulky import titulkycom
except ImportError as ie:
    titulkycom = ie


class TitulkyComSeeker(XBMCSubtitlesAdapter):
    module = titulkycom
    if isinstance(module, Exception):
        error, module = module, None
    id = 'titulky.com'
    provider_name = 'Titulky.com'
    supported_langs = ['sk', 'cs']
    default_settings = {'Titulkyuser': {'label': _("Username"), 'type': 'text', 'default': "", 'pos': 0},
                                       'Titulkypass': {'label': _("Password"), 'type': 'password', 'default': "", 'pos': 1}, }


try:
    from .Edna import edna
except ImportError as ie:
    edna = ie


class EdnaSeeker(XBMCSubtitlesAdapter):
    module = edna
    if isinstance(module, Exception):
        error, module = module, None
    id = 'edna.cz'
    provider_name = 'Edna.cz'
    supported_langs = ['sk', 'cs']
    default_settings = {}
    movie_search = False
    tvshow_search = True


try:
    from .SerialZone import serialzone
except ImportError as ie:
    serialzone = ie


class SerialZoneSeeker(XBMCSubtitlesAdapter):
    module = serialzone
    if isinstance(module, Exception):
        error, module = module, None
    id = 'serialzone.cz'
    provider_name = 'Serialzone.cz'
    supported_langs = ['sk', 'cs']
    default_settings = {}
    movie_search = False
    tvshow_search = True


try:
    from .Elsubtitle import elsubtitle
except ImportError as ie:
    elsubtitle = ie


class ElsubtitleSeeker(XBMCSubtitlesAdapter):
    id = 'elsubtitle'
    module = elsubtitle
    if isinstance(module, Exception):
        error, module = module, None
    provider_name = 'Elsubtitle.com'
    supported_langs = allLang()
    default_settings = {}


try:
    from .Indexsubtitle import indexsubtitle
except ImportError as ie:
    indexsubtitle = ie


class IndexsubtitleSeeker(XBMCSubtitlesAdapter):
    id = 'indexsubtitle'
    module = indexsubtitle
    if isinstance(module, Exception):
        error, module = module, None
    provider_name = 'Indexsubtitle.cc'
    supported_langs = allLang()
    default_settings = {}


try:
    from .Moviesubtitles import moviesubtitles
except ImportError as ie:
    moviesubtitles = ie


class MoviesubtitlesSeeker(XBMCSubtitlesAdapter):
    id = 'moviesubtitles'
    module = moviesubtitles
    if isinstance(module, Exception):
        error, module = module, None
    provider_name = 'Moviesubtitles.org'
    supported_langs = allLang()
    default_settings = {}


try:
    from .Moviesubtitles2 import moviesubtitles2
except ImportError as ie:
    moviesubtitles2 = ie


class Moviesubtitles2Seeker(XBMCSubtitlesAdapter):
    id = 'moviesubtitles2'
    module = moviesubtitles2
    if isinstance(module, Exception):
        error, module = module, None
    provider_name = 'Moviesubtitles.net'
    supported_langs = allLang()
    default_settings = {}


try:
    from .MySubs import mysubs
except ImportError as ie:
    mysubs = ie


class MySubsSeeker(XBMCSubtitlesAdapter):
    id = 'mysubs'
    module = mysubs
    if isinstance(module, Exception):
        error, module = module, None
    provider_name = 'Mysubs'
    supported_langs = allLang()
    default_settings = {}


try:
    from .OpenSubtitles import opensubtitles
except ImportError as ie:
    opensubtitles = ie


class OpenSubtitlesSeeker(XBMCSubtitlesAdapter):
    module = opensubtitles
    if isinstance(module, Exception):
        error, module = module, None
    id = 'opensubtitles'
    provider_name = 'OpenSubtitles'
    supported_langs = allLang()
    default_settings = {}

    def _search(self, title, filepath, lang, season, episode, tvshow, year):
        from xmlrpc.client import ProtocolError
        tries = 4
        for i in range(tries):
            try:
                return XBMCSubtitlesAdapter._search(self, title, filepath, lang, season, episode, tvshow, year)
            except ProtocolError as e:
                self.log.error(e.errcode)
                if i == (tries - 1):
                    raise
                if e.errcode == 503:
                    time.sleep(0.5)


try:
    from .OpenSubtitles2 import opensubtitles2
except ImportError as ie:
    opensubtitles2 = ie


class OpenSubtitles2Seeker(XBMCSubtitlesAdapter):
    module = opensubtitles2
    if isinstance(module, Exception):
        error, module = module, None
    id = 'opensubtitles.com'
    provider_name = 'OpenSubtitles.com'
    supported_langs = allLang()

    default_settings = {}


try:
    from .Podnapisi import podnapisi
except ImportError as ie:
    podnapisi = ie


class PodnapisiSeeker(XBMCSubtitlesAdapter):
    id = 'podnapisi'
    module = podnapisi
    if isinstance(module, Exception):
        error, module = module, None
    provider_name = 'Podnapisi'
    supported_langs = allLang()
    default_settings = {'PNuser': {'label': _("Username"), 'type': 'text', 'default': "", 'pos': 0},
                                       'PNpass': {'label': _("Password"), 'type': 'password', 'default': "", 'pos': 1},
                                       'PNmatch': {'label': _("Send and search movie hashes"), 'type': 'yesno', 'default': 'false', 'pos': 2}}


try:
    from .Subscene import subscene
except ImportError as ie:
    subscene = ie


class SubsceneSeeker(XBMCSubtitlesAdapter):
    id = 'subscene'
    module = subscene
    if isinstance(module, Exception):
        error, module = module, None
    provider_name = 'Subscene'
    supported_langs = allLang()
    default_settings = {}


try:
    from .Subdl import subdl
except ImportError as ie:
    subdl = ie


class SubdlSeeker(XBMCSubtitlesAdapter):
    module = subdl
    if isinstance(module, Exception):
        error, module = module, None
    id = 'subdl.com'
    provider_name = 'Subdl'
    supported_langs = allLang()
    default_settings = {}
    movie_search = True
    tvshow_search = True


try:
    from .Subsyts import subsyts
except ImportError as ie:
    subsyts = ie


class SubsytsSeeker(XBMCSubtitlesAdapter):
    module = subsyts
    if isinstance(module, Exception):
        error, module = module, None
    id = 'syt-subs.com'
    provider_name = 'Subsyts'
    supported_langs = allLang()
    default_settings = {}
    movie_search = True
    tvshow_search = True


try:
    from .Subtitlecat import subtitlecat
except ImportError as ie:
    subtitlecat = ie


class SubtitlecatSeeker(XBMCSubtitlesAdapter):
    module = subtitlecat
    if isinstance(module, Exception):
        error, module = module, None
    id = 'subtitlecat.com'
    provider_name = 'Subtitlecat'
    supported_langs = allLang()
    default_settings = {}
    movie_search = True
    tvshow_search = True


try:
    from .SubtitlesGR import subtitlesgr
except ImportError as ie:
    subtitlesgr = ie


class SubtitlesGRSeeker(XBMCSubtitlesAdapter):
    module = subtitlesgr
    if isinstance(module, Exception):
        error, module = module, None
    id = 'subtitles.gr'
    provider_name = 'SubtitlesGR'
    supported_langs = ['el']
    default_settings = {}
    movie_search = True
    tvshow_search = True


try:
    from .Subtitlesmora import subtitlesmora
except ImportError as ie:
    subtitlesmora = ie


class SubtitlesmoraSeeker(XBMCSubtitlesAdapter):
    module = subtitlesmora
    if isinstance(module, Exception):
        error, module = module, None
    id = 'archive.org'
    provider_name = 'Subtitlesmora'
    supported_langs = ['ar']
    default_settings = {}
    movie_search = True
    tvshow_search = True


try:
    from .Subtitlist import subtitlist
except ImportError as ie:
    subtitlist = ie


class SubtitlistSeeker(XBMCSubtitlesAdapter):
    id = 'subtitlist'
    module = subtitlist
    if isinstance(module, Exception):
        error, module = module, None
    provider_name = 'Subtitlist.com'
    supported_langs = allLang()
    default_settings = {}


try:
    from .Itasa import itasa
except ImportError as ie:
    itasa = ie


class ItasaSeeker(XBMCSubtitlesAdapter):
    module = itasa
    if isinstance(module, Exception):
        error, module = module, None
    id = 'itasa'
    provider_name = 'Itasa'
    supported_langs = ['it']
    default_settings = {'ITuser': {'label': _("Username"), 'type': 'text', 'default': "", 'pos': 0},
                                       'ITpass': {'label': _("Password"), 'type': 'password', 'default': "", 'pos': 1}, }
    movie_search = False
    tvshow_search = True


try:
    from .Titlovi import titlovi
except ImportError as ie:
    titlovi = ie


class TitloviSeeker(XBMCSubtitlesAdapter):
    module = titlovi
    if isinstance(module, Exception):
        error, module = module, None
    id = 'titlovi.com'
    provider_name = 'Titlovi'
    supported_langs = ['bs', 'hr', 'en', 'mk', 'sr', 'sl']
    default_settings = {}
    movie_search = True
    tvshow_search = True
