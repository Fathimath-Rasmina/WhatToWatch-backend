"""
Chat Parser Service.

Rule-based keyword extraction from natural language messages.
Parses user input into a structured intent dict that the chat
engine can use to build personalised recommendations.

No AI/ML — purely dictionary-based keyword matching.
"""

import re


# ---------------------------------------------------------------------------
# Keyword dictionaries
# ---------------------------------------------------------------------------

# Mood keywords → mood label
MOOD_KEYWORDS = {
    # happy
    'happy': 'happy',
    'cheerful': 'happy',
    'upbeat': 'happy',
    'joyful': 'happy',
    'excited': 'happy',
    'great': 'happy',
    'wonderful': 'happy',
    'amazing': 'happy',
    # sad
    'sad': 'sad',
    'cry': 'sad',
    'crying': 'sad',
    'emotional': 'sad',
    'down': 'sad',
    'depressed': 'sad',
    'low': 'sad',
    'heartbroken': 'sad',
    'upset': 'sad',
    'lonely': 'sad',
    # stressed
    'stressed': 'stressed',
    'anxious': 'stressed',
    'tense': 'stressed',
    'overwhelmed': 'stressed',
    'tired': 'stressed',
    'exhausted': 'stressed',
    'burnout': 'stressed',
    # bored
    'bored': 'bored',
    'boring': 'bored',
    'nothing to do': 'bored',
    'nothing to watch': 'bored',
}

# Genre keywords → TMDB genre ID
GENRE_KEYWORDS = {
    # Multi-word first (matched before single-word)
    'science fiction': 878,
    'sci-fi': 878,
    'sci fi': 878,
    'romantic comedy': 35,     # treat as comedy
    'rom-com': 35,
    'rom com': 35,
    'martial arts': 28,
    'true crime': 80,
    'true story': 36,
    'slice of life': 10751,
    # Single-word
    'comedy': 35,
    'funny': 35,
    'laugh': 35,
    'hilarious': 35,
    'humor': 35,
    'humour': 35,
    'romance': 10749,
    'romantic': 10749,
    'love': 10749,
    'love story': 10749,
    'thriller': 53,
    'suspense': 53,
    'suspenseful': 53,
    'horror': 27,
    'scary': 27,
    'creepy': 27,
    'spooky': 27,
    'action': 28,
    'adventure': 12,
    'drama': 18,
    'dramatic': 18,
    'mystery': 9648,
    'mysterious': 9648,
    'detective': 9648,
    'animation': 16,
    'animated': 16,
    'anime': 16,
    'cartoon': 16,
    'documentary': 99,
    'fantasy': 14,
    'magical': 14,
    'crime': 80,
    'criminal': 80,
    'war': 10752,
    'history': 36,
    'historical': 36,
    'family': 10751,
    'music': 10402,
    'musical': 10402,
    'western': 37,
}

# Content type keywords → content_type + optional language
# Stored as (content_type, language_or_None)
CONTENT_TYPE_KEYWORDS = {
    # Multi-word first
    'k-drama': ('tv', 'ko'),
    'kdrama': ('tv', 'ko'),
    'k drama': ('tv', 'ko'),
    'korean drama': ('tv', 'ko'),
    'korean show': ('tv', 'ko'),
    'c-drama': ('tv', 'zh'),
    'cdrama': ('tv', 'zh'),
    'c drama': ('tv', 'zh'),
    'chinese drama': ('tv', 'zh'),
    'chinese show': ('tv', 'zh'),
    'j-drama': ('tv', 'ja'),
    'jdrama': ('tv', 'ja'),
    'j drama': ('tv', 'ja'),
    'japanese drama': ('tv', 'ja'),
    'japanese show': ('tv', 'ja'),
    'bollywood': ('movie', 'hi'),
    'bollywood movie': ('movie', 'hi'),
    'hollywood': ('movie', 'en'),
    'hollywood movie': ('movie', 'en'),
    'tv show': ('tv', None),
    'tv series': ('tv', None),
    'web series': ('tv', None),
    # Single-word
    'movie': ('movie', None),
    'film': ('movie', None),
    'movies': ('movie', None),
    'films': ('movie', None),
    'show': ('tv', None),
    'shows': ('tv', None),
    'series': ('tv', None),
}

# Language keywords → ISO 639-1 code
LANGUAGE_KEYWORDS = {
    'korean': 'ko',
    'korea': 'ko',
    'chinese': 'zh',
    'mandarin': 'zh',
    'china': 'zh',
    'japanese': 'ja',
    'japan': 'ja',
    'hindi': 'hi',
    'indian': 'hi',
    'english': 'en',
    'french': 'fr',
    'spanish': 'es',
    'german': 'de',
    'thai': 'th',
    'turkish': 'tr',
    'tamil': 'ta',
    'telugu': 'te',
    'italian': 'it',
    'portuguese': 'pt',
}

# Tone keywords → mood override
# These map descriptive words to the mood system
TONE_KEYWORDS = {
    # Light / feel-good → maps to happy mood
    'feel-good': 'happy',
    'feel good': 'happy',
    'light': 'happy',
    'lighthearted': 'happy',
    'fun': 'happy',
    'uplifting': 'happy',
    'wholesome': 'happy',
    'heartwarming': 'happy',
    'warm': 'happy',
    'sweet': 'happy',
    'cute': 'happy',
    'cozy': 'happy',
    'positive': 'happy',
    # Intense / gripping → maps to bored mood (thriller/mystery path)
    'intense': 'bored',
    'gripping': 'bored',
    'edge of seat': 'bored',
    'mind-blowing': 'bored',
    'mind blowing': 'bored',
    'dark': 'bored',
    'twisted': 'bored',
    # Calm / relaxing → maps to stressed mood (calm path)
    'calm': 'stressed',
    'relaxing': 'stressed',
    'chill': 'stressed',
    'soothing': 'stressed',
    'peaceful': 'stressed',
    'gentle': 'stressed',
    'slow': 'stressed',
}

# Negation patterns — "no X", "not X", "don't want X", etc.
NEGATION_PATTERNS = [
    r"(?:no|not|don'?t want|without|skip|avoid|hate|exclude|nothing)\s+",
]

# Greeting patterns
GREETING_PATTERNS = [
    r'^(?:hi|hello|hey|howdy|hola|yo|sup|what\'?s up|greetings)[\s!.,?]*$',
]


def parse_message(message):
    """
    Parse a natural language message and extract structured intent.

    Returns:
        {
            "mood": str or None,
            "genres": list[int],          # TMDB genre IDs to include
            "excluded_genres": list[int], # TMDB genre IDs to exclude
            "content_type": "movie" | "tv" | None,
            "language": str or None,      # ISO 639-1 code
            "tone": str or None,          # original tone keyword
            "mood_source": "explicit" | "tone" | None,
            "is_greeting": bool,
            "original_message": str,
        }
    """
    original = message
    text = message.lower().strip()

    intent = {
        'mood': None,
        'genres': [],
        'excluded_genres': [],
        'content_type': None,
        'language': None,
        'tone': None,
        'mood_source': None,
        'is_greeting': False,
        'original_message': original,
    }

    # --- Check for greetings -------------------------------------------------
    for pattern in GREETING_PATTERNS:
        if re.match(pattern, text, re.IGNORECASE):
            intent['is_greeting'] = True
            return intent

    # --- Extract negations / exclusions first --------------------------------
    _extract_exclusions(text, intent)

    # --- Extract content type + language (multi-word first) ------------------
    _extract_content_type(text, intent)

    # --- Extract language (standalone keywords) ------------------------------
    _extract_language(text, intent)

    # --- Extract genres (multi-word first) -----------------------------------
    _extract_genres(text, intent)

    # --- Extract mood --------------------------------------------------------
    _extract_mood(text, intent)

    # --- Extract tone (can override mood) ------------------------------------
    _extract_tone(text, intent)

    return intent


def _extract_exclusions(text, intent):
    """Find negated genres: 'no thriller', 'skip horror', etc."""
    for neg_pattern in NEGATION_PATTERNS:
        # Look for negation + genre keyword
        for keyword, genre_id in _sorted_keywords(GENRE_KEYWORDS):
            pattern = neg_pattern + re.escape(keyword)
            if re.search(pattern, text):
                if genre_id not in intent['excluded_genres']:
                    intent['excluded_genres'].append(genre_id)


def _extract_content_type(text, intent):
    """Extract content type and optionally language from compound keywords."""
    for keyword, (ct, lang) in _sorted_keywords(CONTENT_TYPE_KEYWORDS):
        if keyword in text:
            intent['content_type'] = ct
            if lang and not intent['language']:
                intent['language'] = lang
            break  # first match wins


def _extract_language(text, intent):
    """Extract standalone language keywords (if not already set by content type)."""
    if intent['language']:
        return
    for keyword, lang_code in _sorted_keywords(LANGUAGE_KEYWORDS):
        if keyword in text:
            intent['language'] = lang_code
            break


def _extract_genres(text, intent):
    """Extract genre keywords, skipping any that were negated."""
    excluded = set(intent['excluded_genres'])
    for keyword, genre_id in _sorted_keywords(GENRE_KEYWORDS):
        if keyword in text and genre_id not in excluded:
            # Make sure this keyword isn't part of a negation
            is_negated = False
            for neg_pattern in NEGATION_PATTERNS:
                if re.search(neg_pattern + re.escape(keyword), text):
                    is_negated = True
                    break
            if not is_negated and genre_id not in intent['genres']:
                intent['genres'].append(genre_id)


def _extract_mood(text, intent):
    """Extract mood keywords."""
    for keyword, mood in _sorted_keywords(MOOD_KEYWORDS):
        if keyword in text:
            # Check it's not negated
            is_negated = False
            for neg_pattern in NEGATION_PATTERNS:
                if re.search(neg_pattern + re.escape(keyword), text):
                    is_negated = True
                    break
            if not is_negated:
                intent['mood'] = mood
                intent['mood_source'] = 'explicit'
                break


def _extract_tone(text, intent):
    """Extract tone keywords. Tone can override mood if mood wasn't explicitly set."""
    for keyword, mood_mapping in _sorted_keywords(TONE_KEYWORDS):
        if keyword in text:
            intent['tone'] = keyword
            # Tone sets mood only if no explicit mood was found
            if not intent['mood']:
                intent['mood'] = mood_mapping
                intent['mood_source'] = 'tone'
            break


def _sorted_keywords(keyword_dict):
    """
    Sort keywords by length (longest first) so that multi-word
    keywords are matched before their single-word substrings.
    e.g. "science fiction" before "fiction", "k-drama" before "drama".
    """
    return sorted(keyword_dict.items(), key=lambda x: len(x[0]), reverse=True)
