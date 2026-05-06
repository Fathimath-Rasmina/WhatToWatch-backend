"""
Recommendation service.

Combines user preferences and optional mood to build TMDB discover
API requests and return personalised results.
"""

import requests
from django.conf import settings

TMDB_BASE_URL = 'https://api.themoviedb.org/3'

# ---------------------------------------------------------------------------
# Mood → TMDB Genre ID mapping
# ---------------------------------------------------------------------------
# TMDB genre IDs reference:
#   28 = Action, 12 = Adventure, 16 = Animation, 35 = Comedy,
#   80 = Crime, 99 = Documentary, 18 = Drama, 10751 = Family,
#   14 = Fantasy, 36 = History, 27 = Horror, 10402 = Music,
#   9648 = Mystery, 10749 = Romance, 878 = Sci-Fi, 10770 = TV Movie,
#   53 = Thriller, 10752 = War, 37 = Western
#
# TV-specific genre IDs that differ:
#   10759 = Action & Adventure, 10762 = Kids, 10763 = News,
#   10764 = Reality, 10766 = Soap, 10767 = Talk, 10768 = War & Politics

MOOD_GENRE_MAP = {
    'happy': {
        'movie': [35, 10749],        # Comedy, Romance
        'tv': [35, 10749],
    },
    'sad': {
        'movie': [35, 18],           # Comedy (feel-good), Drama (light drama)
        'tv': [35, 18],
    },
    'stressed': {
        'movie': [16, 10751, 99],    # Animation (calm), Family (slice of life), Documentary
        'tv': [16, 10751, 99],
    },
    'bored': {
        'movie': [53, 9648],         # Thriller, Mystery
        'tv': [53, 9648],
    },
}

VALID_MOODS = list(MOOD_GENRE_MAP.keys())


def validate_mood(mood):
    """Return the mood string if valid, else None."""
    if mood and mood.lower() in VALID_MOODS:
        return mood.lower()
    return None


def _get_mood_genres(mood, media_type='movie'):
    """Return genre IDs for a given mood and media type."""
    if not mood:
        return []
    mapping = MOOD_GENRE_MAP.get(mood, {})
    return mapping.get(media_type, mapping.get('movie', []))


def _merge_genres(preference_genres, mood_genres):
    """Merge user-preferred genres with mood genres, removing duplicates."""
    combined = list(preference_genres or [])
    for gid in mood_genres:
        if gid not in combined:
            combined.append(gid)
    return combined


def _normalize_item(item, media_type=None):
    """Normalize a TMDB discover result to a consistent format."""
    mt = media_type or item.get('media_type')
    return {
        'id': item.get('id'),
        'title': item.get('title') or item.get('name'),
        'overview': item.get('overview'),
        'poster_path': item.get('poster_path'),
        'release_date': item.get('release_date') or item.get('first_air_date'),
        'media_type': mt,
        'vote_average': item.get('vote_average'),
        'genre_ids': item.get('genre_ids', []),
        'original_language': item.get('original_language', ''),
    }


def _discover(media_type, genre_ids, language=None, page=1):
    """
    Call TMDB /discover/{media_type} with the given genre IDs.
    Returns a list of normalised items.
    """
    url = f"{TMDB_BASE_URL}/discover/{media_type}"
    params = {
        'api_key': settings.TMDB_API_KEY,
        'sort_by': 'popularity.desc',
        'page': page,
        'vote_count.gte': 50,  # filter out obscure titles
    }
    if genre_ids:
        params['with_genres'] = ','.join(str(g) for g in genre_ids)
    if language:
        params['with_original_language'] = language

    try:
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
        return [_normalize_item(item, media_type) for item in data.get('results', [])]
    except requests.RequestException:
        return []


def get_recommendations(user, mood=None, page=1):
    """
    Build and return recommendations for the given user.

    Steps:
      1. Load user preferences (if any).
      2. Resolve mood → genre IDs.
      3. Merge preference genres + mood genres.
      4. Decide which media types to query (movie / tv / both).
      5. Call TMDB discover for each media type.
      6. Return combined results.
    """
    from accounts.models import UserPreference  # late import to avoid circular

    # --- 1. Load preferences --------------------------------------------------
    try:
        pref = UserPreference.objects.get(user=user)
        pref_genres = pref.preferred_genres or []
        pref_languages = pref.preferred_languages or []
        content_type = pref.content_type or 'both'
    except UserPreference.DoesNotExist:
        pref_genres = []
        pref_languages = []
        content_type = 'both'

    # --- 2. Determine which media types to fetch ------------------------------
    if content_type == 'both':
        media_types = ['movie', 'tv']
    else:
        media_types = [content_type]

    # --- 3. For each media type, merge genres & fetch -------------------------
    all_results = []
    for mt in media_types:
        mood_genres = _get_mood_genres(mood, mt)
        combined_genres = _merge_genres(pref_genres, mood_genres)

        # Use the first preferred language for filtering, if any
        language = pref_languages[0] if pref_languages else None

        results = _discover(mt, combined_genres, language=language, page=page)
        all_results.extend(results)

    # --- 4. Sort by popularity (vote_average descending) ----------------------
    all_results.sort(key=lambda x: x.get('vote_average', 0), reverse=True)

    return all_results


# ---------------------------------------------------------------------------
# Scored Recommendation Engine
# ---------------------------------------------------------------------------

def _score_item(item, taste_profile, pref_genres, mood_genres, excluded_genres):
    """
    Score a single TMDB result against the user's profile.

    Scoring rules:
      +5  → matches dominant language AND dominant content type
      +4  → matches a genre the user rated highly (4-5 stars)
      +3  → matches a genre from user preferences
      +2  → matches a mood-mapped genre
      -5  → matches an excluded genre

    Returns the total score (integer).
    """
    score = 0
    item_genres = set(item.get('genre_ids', []))
    item_language = item.get('original_language', '')
    item_media_type = item.get('media_type', '')

    # +5 — dominant language + content type match
    dominant_lang = taste_profile.get('dominant_language')
    dominant_type = taste_profile.get('dominant_content_type')
    if dominant_lang and dominant_type:
        if item_language == dominant_lang and item_media_type == dominant_type:
            score += 5
    elif dominant_lang and item_language == dominant_lang:
        score += 3  # language match alone is still valuable
    elif dominant_type and item_media_type == dominant_type:
        score += 2  # type match alone

    # +4 — high-rated genre match
    high_rated = set(taste_profile.get('high_rated_genres', []))
    if item_genres & high_rated:
        score += 4

    # +3 — user preference genre match
    if item_genres & set(pref_genres):
        score += 3

    # +2 — mood genre match
    if item_genres & set(mood_genres):
        score += 2

    # -5 — excluded genre penalty
    if item_genres & set(excluded_genres):
        score -= 5

    return score


def get_scored_recommendations(
    user,
    mood=None,
    excluded_genres=None,
    genre_ids=None,
    content_type=None,
    language=None,
    page=1,
):
    """
    Scored recommendation engine.

    Fetches content from TMDB and ranks it using a rule-based scoring
    system that prioritises the user's actual watch behaviour over
    generic popularity.

    Parameters:
        user             — authenticated User instance
        mood             — optional mood string (happy/sad/stressed/bored)
        excluded_genres  — list of genre IDs to penalise
        genre_ids        — explicit genre override (e.g. from chat)
        content_type     — explicit content type override ("movie"/"tv"/"both")
        language         — explicit language override (ISO 639-1 code)
        page             — TMDB pagination

    Returns:
        list of normalised items sorted by score (desc), then vote_average (desc).
    """
    from accounts.models import UserPreference
    from movies.services.profile_analyzer import get_taste_profile

    excluded_genres = excluded_genres or []

    # --- 1. Load taste profile from watch history -----------------------------
    taste_profile = get_taste_profile(user)

    # --- 2. Load explicit user preferences ------------------------------------
    try:
        pref = UserPreference.objects.get(user=user)
        pref_genres = pref.preferred_genres or []
        pref_languages = pref.preferred_languages or []
        pref_content_type = pref.content_type or 'both'
    except UserPreference.DoesNotExist:
        pref_genres = []
        pref_languages = []
        pref_content_type = 'both'

    # --- 3. Resolve effective parameters (overrides > taste > prefs) ----------
    # Content type: explicit override > dominant from history > user preference
    effective_type = content_type
    if not effective_type:
        effective_type = taste_profile.get('dominant_content_type') or pref_content_type

    # Language: explicit override > dominant from history > first user pref
    effective_language = language
    if not effective_language:
        effective_language = (
            taste_profile.get('dominant_language')
            or (pref_languages[0] if pref_languages else None)
        )

    # Genres for TMDB query: explicit override > dominant from history > user prefs
    if genre_ids:
        query_genres = list(genre_ids)
    elif taste_profile.get('dominant_genres'):
        query_genres = list(taste_profile['dominant_genres'])
    else:
        query_genres = list(pref_genres)

    # --- 4. Add mood genres ---------------------------------------------------
    mood_genres = []
    if effective_type == 'both':
        media_types = ['movie', 'tv']
    else:
        media_types = [effective_type]

    for mt in media_types:
        mg = _get_mood_genres(mood, mt)
        for g in mg:
            if g not in mood_genres:
                mood_genres.append(g)

    # Merge mood genres into query genres for TMDB fetch
    fetch_genres = _merge_genres(query_genres, mood_genres)

    # --- 5. Fetch from TMDB ---------------------------------------------------
    all_results = []
    for mt in media_types:
        results = _discover(
            media_type=mt,
            genre_ids=fetch_genres,
            language=effective_language,
            page=page,
        )
        all_results.extend(results)

    # --- 6. Score each result -------------------------------------------------
    for item in all_results:
        item['score'] = _score_item(
            item,
            taste_profile,
            pref_genres,
            mood_genres,
            excluded_genres,
        )

    # --- 7. Exclude items user marked as not_interested -----------------------
    from movies.models import WatchedItem
    not_interested_ids = set(
        WatchedItem.objects.filter(user=user, status='not_interested')
        .values_list('tmdb_id', flat=True)
    )
    if not_interested_ids:
        all_results = [r for r in all_results if r.get('id') not in not_interested_ids]

    # --- 8. Sort by score (desc), then vote_average (desc) --------------------
    all_results.sort(
        key=lambda x: (x.get('score', 0), x.get('vote_average', 0)),
        reverse=True,
    )

    return all_results

