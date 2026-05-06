"""
Explore Service.

Suggests content outside the user's dominant preferences while
maintaining partial relevance — same genres but different language,
or same language but different genre, etc.

This gives users controlled diversity without polluting their
main recommendation feed.
"""

import requests
from django.conf import settings
from movies.models import WatchedItem

TMDB_BASE_URL = 'https://api.themoviedb.org/3'

# Languages considered "adjacent" to each other for exploration.
# If a user watches Korean content, Japanese and Chinese are nearby.
ADJACENT_LANGUAGES = {
    'ko': ['ja', 'zh'],
    'ja': ['ko', 'zh'],
    'zh': ['ko', 'ja'],
    'en': ['fr', 'es', 'de'],
    'hi': ['ta', 'te', 'ml'],
    'fr': ['en', 'es', 'it'],
    'es': ['en', 'fr', 'pt'],
}


def _normalize_item(item, media_type=None):
    """Normalize a TMDB discover result."""
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


def _discover(media_type, genre_ids=None, language=None, page=1):
    """Call TMDB /discover/{media_type}."""
    url = f"{TMDB_BASE_URL}/discover/{media_type}"
    params = {
        'api_key': settings.TMDB_API_KEY,
        'sort_by': 'popularity.desc',
        'page': page,
        'vote_count.gte': 50,
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


def get_explore_content(user, page=1):
    """
    Return content outside the user's dominant preferences but with
    partial relevance.

    Strategy:
      1. Same genres, adjacent language
         (K-drama romance fan → Japanese romance)
      2. Same language, different genres (expand taste within language)
      3. Opposite content type with same genres
         (TV drama fan → drama movies)

    Already-watched items are excluded from results.

    Returns:
        {
            'strategies': [...],   # which strategies produced results
            'results': [...]
        }
    """
    from movies.services.profile_analyzer import get_taste_profile

    taste = get_taste_profile(user)

    # Nothing to explore from — return popular content
    if taste['total_watched'] == 0:
        results = _discover('movie', page=page)
        results.extend(_discover('tv', page=page))
        results.sort(key=lambda x: x.get('vote_average', 0), reverse=True)
        return {
            'strategies': ['popular'],
            'results': results[:20],
        }

    dominant_lang = taste.get('dominant_language')
    dominant_type = taste.get('dominant_content_type')
    dominant_genres = taste.get('dominant_genres', [])

    # Collect already-watched + not_interested tmdb_ids for exclusion
    watched_ids = set(
        WatchedItem.objects.filter(user=user)
        .exclude(status='plan_to_watch')
        .values_list('tmdb_id', flat=True)
    )

    all_results = []
    strategies_used = []

    # --- Strategy 1: Same genres, adjacent language ---------------------------
    if dominant_lang and dominant_genres:
        adjacent_langs = ADJACENT_LANGUAGES.get(dominant_lang, [])
        for lang in adjacent_langs[:2]:  # try up to 2 adjacent languages
            mt = dominant_type or 'tv'
            items = _discover(mt, genre_ids=dominant_genres[:3], language=lang, page=page)
            if items:
                strategies_used.append(f'same_genres_lang_{lang}')
                all_results.extend(items)

    # --- Strategy 2: Same language, different genres --------------------------
    if dominant_lang:
        # Pick genres the user does NOT watch heavily
        dominant_set = set(dominant_genres)
        # Common "discovery" genres to try
        discovery_genres = [28, 878, 16, 99, 80, 14, 9648]  # Action, Sci-Fi, Animation, Documentary, Crime, Fantasy, Mystery
        new_genres = [g for g in discovery_genres if g not in dominant_set][:3]

        if new_genres:
            mt = dominant_type or 'tv'
            items = _discover(mt, genre_ids=new_genres, language=dominant_lang, page=page)
            if items:
                strategies_used.append('same_lang_new_genres')
                all_results.extend(items)

    # --- Strategy 3: Opposite content type, same genres -----------------------
    if dominant_type and dominant_genres:
        opposite_type = 'movie' if dominant_type == 'tv' else 'tv'
        items = _discover(opposite_type, genre_ids=dominant_genres[:3], page=page)
        if items:
            strategies_used.append(f'opposite_type_{opposite_type}')
            all_results.extend(items)

    # --- Deduplicate and exclude watched -------------------------------------
    seen_ids = set()
    unique_results = []
    for item in all_results:
        item_id = item.get('id')
        if item_id and item_id not in seen_ids and item_id not in watched_ids:
            seen_ids.add(item_id)
            unique_results.append(item)

    # Sort by vote_average
    unique_results.sort(key=lambda x: x.get('vote_average', 0), reverse=True)

    return {
        'strategies': strategies_used or ['popular'],
        'results': unique_results[:20],
    }
