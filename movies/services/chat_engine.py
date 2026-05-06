"""
Chat Engine Service.

Orchestrates the chat flow:
  1. Parses user message → structured intent
  2. Loads user's taste profile
  3. Combines intent with taste profile
  4. Calls the scored recommendation engine
  5. Builds a conversational response

This is the single entry point called by the ChatAssistantView.
"""

from movies.services.chat_parser import parse_message
from movies.services.profile_analyzer import get_taste_profile
from movies.services.recommendation import get_scored_recommendations


# ---------------------------------------------------------------------------
# Response message templates
# ---------------------------------------------------------------------------

def _build_response_message(intent, taste_profile):
    """
    Build a friendly, conversational response message based on what
    the parser understood from the user's input.
    """
    # Greeting
    if intent.get('is_greeting'):
        return (
            "Hey! 👋 Tell me what you're in the mood for, "
            "or I'll suggest something based on your taste. "
            "Try something like: \"I want a romantic K-drama\" "
            "or \"feeling bored, suggest a thriller\""
        )

    parts = []

    # Mood acknowledgment — only for explicitly stated moods
    mood = intent.get('mood')
    mood_source = intent.get('mood_source')
    if mood and mood_source == 'explicit':
        if mood == 'sad':
            parts.append("Feeling down? Let me find something to cheer you up 💛")
        elif mood == 'happy':
            parts.append("Love the good vibes! Here's something fun for you 😄")
        elif mood == 'stressed':
            parts.append("Time to relax! Here are some calm picks for you 🍃")
        elif mood == 'bored':
            parts.append("Let's fix that boredom! Check these out 🔥")

    # Exclusion acknowledgment
    excluded = intent.get('excluded_genres', [])
    if excluded:
        genre_names = _genre_ids_to_names(excluded)
        parts.append(f"Got it — skipping {', '.join(genre_names)}.")

    # Tone acknowledgment — when mood was inferred from tone keywords
    tone = intent.get('tone')
    if tone and mood_source == 'tone':
        parts.append(f"Looking for something {tone}?")

    # Content description
    descriptors = []

    # Genre names
    genres = intent.get('genres', [])
    if genres:
        genre_names = _genre_ids_to_names(genres)
        descriptors.extend(genre_names)

    # Language / content type
    language = intent.get('language')
    content_type = intent.get('content_type')
    lang_name = _language_code_to_name(language)

    if lang_name and content_type:
        ct_label = 'movies' if content_type == 'movie' else 'shows'
        descriptors.append(f"{lang_name} {ct_label}")
    elif lang_name:
        descriptors.append(f"{lang_name} content")
    elif content_type:
        ct_label = 'movies' if content_type == 'movie' else 'TV shows'
        descriptors.append(ct_label)

    if descriptors:
        parts.append(f"Here are some {', '.join(descriptors)} for you! 🎬")
    elif not parts:
        # Nothing specific extracted — use taste profile for context
        if taste_profile and taste_profile.get('total_watched', 0) > 0:
            parts.append("Here are some picks based on your taste! 🍿")
        else:
            parts.append("Here are some popular picks you might enjoy! 🍿")

    return " ".join(parts)


# ---------------------------------------------------------------------------
# Helper maps for human-readable names
# ---------------------------------------------------------------------------

GENRE_ID_TO_NAME = {
    28: 'action', 12: 'adventure', 16: 'animation', 35: 'comedy',
    80: 'crime', 99: 'documentary', 18: 'drama', 10751: 'family',
    14: 'fantasy', 36: 'history', 27: 'horror', 10402: 'music',
    9648: 'mystery', 10749: 'romance', 878: 'sci-fi', 10770: 'TV movie',
    53: 'thriller', 10752: 'war', 37: 'western',
}

LANGUAGE_CODE_TO_NAME = {
    'ko': 'Korean', 'ja': 'Japanese', 'zh': 'Chinese',
    'en': 'English', 'hi': 'Hindi', 'fr': 'French',
    'es': 'Spanish', 'de': 'German', 'th': 'Thai',
    'tr': 'Turkish', 'ta': 'Tamil', 'te': 'Telugu',
    'it': 'Italian', 'pt': 'Portuguese',
}


def _genre_ids_to_names(genre_ids):
    """Convert a list of genre IDs to human-readable names."""
    return [GENRE_ID_TO_NAME.get(gid, f'genre {gid}') for gid in genre_ids]


def _language_code_to_name(code):
    """Convert a language code to a human-readable name."""
    if not code:
        return None
    return LANGUAGE_CODE_TO_NAME.get(code)


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

def process_chat_message(user, message):
    """
    Process a user's chat message and return a response with
    recommendations.

    Returns:
        {
            "message": "Friendly response text...",
            "intent": { parsed intent dict },
            "count": int,
            "results": [ list of TMDB items ],
        }
    """
    # --- 1. Parse the message -------------------------------------------------
    intent = parse_message(message)

    # --- 2. Load taste profile ------------------------------------------------
    taste_profile = get_taste_profile(user)

    # --- 3. Build response message --------------------------------------------
    response_message = _build_response_message(intent, taste_profile)

    # --- 4. If it's just a greeting, return early (no results) ----------------
    if intent.get('is_greeting'):
        return {
            'message': response_message,
            'intent': intent,
            'count': 0,
            'results': [],
        }

    # --- 5. Build recommendation params from intent ---------------------------
    rec_params = _build_recommendation_params(intent, taste_profile)

    # --- 6. Fetch scored recommendations --------------------------------------
    results = get_scored_recommendations(user=user, **rec_params)

    return {
        'message': response_message,
        'intent': intent,
        'count': len(results),
        'results': results,
    }


def _build_recommendation_params(intent, taste_profile):
    """
    Translate parsed intent + taste profile into keyword arguments
    for get_scored_recommendations().

    Priority: chat intent > taste profile > defaults.
    Mood ADJUSTS within the user's taste — it does not override it.
    """
    params = {}

    # Mood
    if intent.get('mood'):
        params['mood'] = intent['mood']

    # Excluded genres
    if intent.get('excluded_genres'):
        params['excluded_genres'] = intent['excluded_genres']

    # Explicit genres from chat override preference genres
    if intent.get('genres'):
        params['genre_ids'] = intent['genres']

    # Content type from chat overrides preference
    if intent.get('content_type'):
        params['content_type'] = intent['content_type']

    # Language from chat overrides preference
    if intent.get('language'):
        params['language'] = intent['language']

    return params
