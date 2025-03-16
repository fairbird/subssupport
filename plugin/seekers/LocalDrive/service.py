import os
import re
import shutil



LANGUAGE_MAP = {
    "sq": ("Albanian", "flags/sq.gif"),
    "ar": ("Arabic", "flags/ar.gif"),
    "hy": ("Belarusian", "flags/hy.gif"),
    "bs": ("Bosnian", "flags/bs.gif"),
    "bg": ("Bulgarian", "flags/bg.gif"),
    "ca": ("Catalan", "flags/ca.gif"),
    "zh": ("Chinese", "flags/zh.gif"),
    "hr": ("Croatian", "flags/hr.gif"),
    "cs": ("Czech", "flags/cs.gif"),
    "da": ("Danish", "flags/da.gif"),
    "nl": ("Dutch", "flags/nl.gif"),
    "en": ("English", "flags/en.gif"),
    "et": ("Estonian", "flags/et.gif"),
    "fa": ("Persian", "flags/fa.gif"),
    "fi": ("Finnish", "flags/fi.gif"),
    "fr": ("French", "flags/fr.gif"),
    "de": ("German", "flags/de.gif"),
    "el": ("Greek", "flags/el.gif"),
    "he": ("Hebrew", "flags/he.gif"),
    "hi": ("Hindi", "flags/hi.gif"),
    "hu": ("Hungarian", "flags/hu.gif"),
    "is": ("Icelandic", "flags/is.gif"),
    "id": ("Indonesian", "flags/id.gif"),
    "it": ("Italian", "flags/it.gif"),
    "ja": ("Japanese", "flags/ja.gif"),
    "ko": ("Korean", "flags/ko.gif"),
    "lv": ("Latvian", "flags/lv.gif"),
    "lt": ("Lithuanian", "flags/lt.gif"),
    "mk": ("Macedonian", "flags/mk.gif"),
    "ms": ("Malay", "flags/ms.gif"),
    "no": ("Norwegian", "flags/no.gif"),
    "pl": ("Polish", "flags/pl.gif"),
    "pt": ("Portuguese", "flags/pt.gif"),
    "pt-br": ("Portuguese (Brazil)", "flags/pt-br.gif"),
    "pb": ("Portuguese (Brazil)", "flags/pt-br.gif"),
    "ro": ("Romanian", "flags/ro.gif"),
    "ru": ("Russian", "flags/ru.gif"),
    "sr": ("Serbian", "flags/sr.gif"),
    "sk": ("Slovak", "flags/sk.gif"),
    "sl": ("Slovenian", "flags/sl.gif"),
    "es": ("Spanish", "flags/es.gif"),
    "sv": ("Swedish", "flags/sv.gif"),
    "th": ("Thai", "flags/th.gif"),
    "tr": ("Turkish", "flags/tr.gif"),
    "uk": ("Ukrainian", "flags/uk.gif"),
    "vi": ("Vietnamese", "flags/vi.gif"),
    "ur": ("Urdu", "flags/ur.gif"),
    "ta": ("Tamil", "flags/ta.gif"),
    "te": ("Telugu", "flags/te.gif"),
    "ml": ("Malayalam", "flags/ml.gif"),
    "kn": ("Kannada", "flags/kn.gif"),
    "mr": ("Marathi", "flags/mr.gif"),
    "bn": ("Bengali", "flags/bn.gif"),
    "pa": ("Punjabi", "flags/pa.gif"),
    "es-la": ("Spanish (Latin America)", "flags/es-la.gif"),
    "es-es": ("Spanish (Spain)", "flags/es-es.gif"),
    "zh-cn": ("Chinese (Simplified)", "flags/zh-cn.gif"),
    "zh-tw": ("Chinese (Traditional)", "flags/zh-tw.gif"),
}



def get_first_word(title):
    """Extracts the first word before a space or any special symbol."""
    match = re.match(r'^([\w]+)', title)  # Match only the first word
    return match.group(1) if match else title  # Return first word or full title

def extract_language(filename):
    """Extracts the last two letters before '.srt' as the language code and converts it to a full name."""
    match = re.search(r'([a-zA-Z-]{2,5})\.srt$', filename)  # Match language code (supports 2-5 characters)
    lang_code = match.group(1).lower() if match else "unknown"
    
    # Get full language name from LANGUAGE_MAP
    language_name = LANGUAGE_MAP.get(lang_code, ("Unknown", "flags/unknown.gif"))[0]  # Extract only name
    
    return language_name  # Return as a string, not a list or tuple

def search_subtitles(file_path, title, tvshow, year, season, episode, set_temp, rar, lang1, lang2, lang3, stack):
    global settings_provider  # Ensure we're using the existing instance
    DOWNLOAD_PATH = settings_provider.getSetting("LocalSearchPath")
    print(DOWNLOAD_PATH)
    search_paths = [DOWNLOAD_PATH, "/tmp/"]
    subtitles_list = []
    msg = ""

    title_key = get_first_word(title)
    filename_pattern = rf"{title_key}.*\.srt$"

    for path in search_paths:
        if os.path.exists(path):
            for root, _, files in os.walk(path):  # Recursively walk through directories
                for file in files:
                    if re.match(filename_pattern, file, re.IGNORECASE):
                        language_name = extract_language(file)
                        subtitles_list.append({
                            "filename": file,
                            "path": os.path.join(root, file),
                            "language_name": language_name,
                            "language_flag": LANGUAGE_MAP.get(language_name, ("Unknown", "flags/unknown.gif"))[1],
                            "sync": True
                        })

    return subtitles_list, "", msg

def remove_language_code(filename):
    """Removes repeated or single language codes before '.srt'."""
    return re.sub(r'([._-][a-zA-Z]{2,5})+\.srt$', ".srt", filename)  # Remove repeated codes

def download_subtitles(subtitles_list, pos, zip_subs, tmp_sub_dir, sub_folder, session_id):
    """
    Copies the selected subtitle from its original location to /tmp/,
    and removes any language code from the filename.
    """
    if pos < 0 or pos >= len(subtitles_list):
        print(f"[LocalDriveSeeker][error] Invalid subtitle selection index: {pos}")
        return False, "Unknown", None  # Return failure

    subtitle_info = subtitles_list[pos]
    subtitle_path = subtitle_info.get("path")  # Original location
    subtitle_filename = subtitle_info.get("filename")  # Original filename
    print(subtitle_filename)
    language = subtitle_info.get("language_name", "Unknown")

    if not subtitle_path or not os.path.exists(subtitle_path):
        print(f"[LocalDriveSeeker][error] Subtitle file not found: {subtitle_path}")
        return False, language, None  # Return failure

    # Ensure /tmp/ directory exists
    os.makedirs(tmp_sub_dir, exist_ok=True)

    # Remove language code(s) from filename
    new_filename = remove_language_code(subtitle_filename)
    print(new_filename)
    copied_path = os.path.join(tmp_sub_dir, new_filename)

    try:
        shutil.copy(subtitle_path, copied_path)
        print(f"[LocalDriveSeeker][info] Subtitle copied to: {copied_path}")
    except Exception as e:
        print(f"[LocalDriveSeeker][error] Error copying subtitle: {e}")
        return False, language, None  # Return failure

    packed = False  # SRT files are not packed
    return packed, language, copied_path  # Return correct file path