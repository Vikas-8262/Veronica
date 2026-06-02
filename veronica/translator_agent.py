"""Real-Time Language Translator agent for Veronica."""

import importlib
from .skills import AssistantContext, SkillResult

def _optional_module(module_name: str):
    try:
        return importlib.import_module(module_name)
    except ImportError:
        return None

# Common language name -> ISO 639-1 code mapping
LANGUAGE_MAP = {
    "afrikaans": "af", "albanian": "sq", "amharic": "am", "arabic": "ar",
    "armenian": "hy", "azerbaijani": "az", "basque": "eu", "belarusian": "be",
    "bengali": "bn", "bosnian": "bs", "bulgarian": "bg", "catalan": "ca",
    "cebuano": "ceb", "chinese": "zh-CN", "mandarin": "zh-CN", "corsican": "co",
    "croatian": "hr", "czech": "cs", "danish": "da", "dutch": "nl",
    "english": "en", "esperanto": "eo", "estonian": "et", "finnish": "fi",
    "french": "fr", "frisian": "fy", "galician": "gl", "georgian": "ka",
    "german": "de", "greek": "el", "gujarati": "gu", "haitian creole": "ht",
    "hausa": "ha", "hawaiian": "haw", "hebrew": "he", "hindi": "hi",
    "hmong": "hmn", "hungarian": "hu", "icelandic": "is", "igbo": "ig",
    "indonesian": "id", "irish": "ga", "italian": "it", "japanese": "ja",
    "javanese": "jv", "kannada": "kn", "kazakh": "kk", "khmer": "km",
    "korean": "ko", "kurdish": "ku", "kyrgyz": "ky", "lao": "lo",
    "latin": "la", "latvian": "lv", "lithuanian": "lt", "luxembourgish": "lb",
    "macedonian": "mk", "malagasy": "mg", "malay": "ms", "malayalam": "ml",
    "maltese": "mt", "maori": "mi", "marathi": "mr", "mongolian": "mn",
    "myanmar": "my", "burmese": "my", "nepali": "ne", "norwegian": "no",
    "nyanja": "ny", "chichewa": "ny", "pashto": "ps", "persian": "fa",
    "farsi": "fa", "polish": "pl", "portuguese": "pt", "punjabi": "pa",
    "romanian": "ro", "russian": "ru", "samoan": "sm", "scots gaelic": "gd",
    "serbian": "sr", "sesotho": "st", "shona": "sn", "sindhi": "sd",
    "sinhala": "si", "sinhalese": "si", "slovak": "sk", "slovenian": "sl",
    "somali": "so", "spanish": "es", "sundanese": "su", "swahili": "sw",
    "swedish": "sv", "tagalog": "tl", "filipino": "tl", "tajik": "tg",
    "tamil": "ta", "telugu": "te", "thai": "th", "turkish": "tr",
    "ukrainian": "uk", "urdu": "ur", "uzbek": "uz", "vietnamese": "vi",
    "welsh": "cy", "xhosa": "xh", "yiddish": "yi", "yoruba": "yo",
    "zulu": "zu",
}

def is_translator_request(message: str) -> bool:
    """Matcher for Translator requests."""
    lowered = message.lower().strip()
    return lowered.startswith("translate") or "detect language" in lowered

def handle_translator_request(message: str, context: AssistantContext) -> SkillResult:
    """Handler for translation and language detection."""
    dt = _optional_module("deep_translator")
    if dt is None:
        return SkillResult(True, "Translator Agent requires 'deep-translator'. Run: pip install deep-translator")

    lowered = message.lower().strip()

    # --- DETECT LANGUAGE ---
    if "detect language" in lowered:
        # e.g. "detect language of: こんにちは"
        text_to_detect = ""
        if "of:" in lowered:
            text_to_detect = message[message.lower().find("of:") + 3:].strip()
        elif "of " in lowered:
            text_to_detect = message[message.lower().find("of ") + 3:].strip()
        
        if not text_to_detect:
            return SkillResult(True, "Please provide text after 'detect language of: <text>'.")
        
        try:
            detected = dt.single_detection(text_to_detect, api_key=None)
            # Map code back to name if possible
            lang_name = next((k for k, v in LANGUAGE_MAP.items() if v == detected), detected)
            return SkillResult(True, f"🔍 Detected Language: **{lang_name.title()}** (code: `{detected}`)")
        except Exception as e:
            return SkillResult(True, f"Language detection failed: {e}")

    # --- TRANSLATE ---
    # Pattern 1: "translate <text> to <language>"
    # Pattern 2: "translate to <language>: <text>"
    target_lang_code = "en"
    text_to_translate = ""

    if " to " in lowered:
        # Check if format is "translate to <lang>: <text>"
        if lowered.startswith("translate to "):
            after = lowered[len("translate to "):]
            if ":" in after:
                lang_part, text_part = after.split(":", 1)
                lang_name_key = lang_part.strip()
                target_lang_code = LANGUAGE_MAP.get(lang_name_key, lang_name_key)
                # Use original message case for text
                orig_colon_idx = message.find(":", message.lower().find("translate to "))
                text_to_translate = message[orig_colon_idx + 1:].strip() if orig_colon_idx != -1 else text_part.strip()
            else:
                return SkillResult(True, "Format: 'Translate to French: Hello, how are you?'")
        else:
            # Format: "translate <text> to <language>"
            # Find "to" closest to end
            to_idx = lowered.rfind(" to ")
            lang_name_key = lowered[to_idx + 4:].strip().strip("?.!")
            target_lang_code = LANGUAGE_MAP.get(lang_name_key, lang_name_key)
            
            # Extract text between "translate" and " to "
            start = len("translate ")
            orig_to_idx = message.lower().rfind(" to ")
            text_to_translate = message[start:orig_to_idx].strip()
    else:
        return SkillResult(True, "Please specify a target language (e.g., 'Translate hello world to Spanish').")

    if not text_to_translate:
        return SkillResult(True, "Please provide the text you want to translate.")

    try:
        print(f"🌍 [Translating to {target_lang_code}...]")
        translator = dt.GoogleTranslator(source="auto", target=target_lang_code)
        result = translator.translate(text_to_translate)
        
        lang_display = next((k.title() for k, v in LANGUAGE_MAP.items() if v == target_lang_code), target_lang_code)
        
        return SkillResult(True, (
            f"🌍 Translation to {lang_display}:\n\n"
            f"  Original: \"{text_to_translate}\"\n"
            f"  → {lang_display}: \"{result}\""
        ))
    except Exception as e:
        return SkillResult(True, f"Translation failed. Check the language name is valid: {e}")
