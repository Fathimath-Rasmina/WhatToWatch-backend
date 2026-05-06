import requests
from django.conf import settings

TMDB_BASE_URL = 'https://api.themoviedb.org/3'

def _normalize_item(item):
    """Normalize TMDB item data to consistent format."""
    return {
        'id': item.get('id'),
        'title': item.get('title') or item.get('name'),
        'overview': item.get('overview'),
        'poster_path': item.get('poster_path'),
        'release_date': item.get('release_date') or item.get('first_air_date'),
        'media_type': item.get('media_type'),
        'vote_average': item.get('vote_average'),
        'genre_ids': item.get('genre_ids', []),
        'original_language': item.get('original_language', ''),
    }

def get_trending():
    """Fetch trending movies and TV shows from TMDB."""
    url = f"{TMDB_BASE_URL}/trending/all/day"
    params = {'api_key': settings.TMDB_API_KEY}
    
    try:
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
        return [_normalize_item(item) for item in data.get('results', [])]
    except requests.RequestException as e:
        # Log error or handle appropriately
        return []

def get_trending_filtered(media_type=None, language=None, genre_ids=None):
    """
    Fetch trending content from TMDB, then filter server-side by the
    user's dominant preferences.

    TMDB's /trending endpoint doesn't support genre or language query
    params, so we fetch up to 3 pages and filter the results ourselves.

    Parameters:
        media_type  — "movie" or "tv" or None (all)
        language    — ISO 639-1 code to filter by (e.g. "ko")
        genre_ids   — list of genre IDs; items must match at least one

    Returns:
        list of normalised, filtered trending items (up to 20).
    """
    genre_set = set(genre_ids) if genre_ids else set()
    filtered = []
    max_pages = 3  # fetch up to 3 pages to gather enough filtered results

    for page in range(1, max_pages + 1):
        # Use media-specific trending endpoint if a type is specified
        trend_type = media_type if media_type in ('movie', 'tv') else 'all'
        url = f"{TMDB_BASE_URL}/trending/{trend_type}/day"
        params = {'api_key': settings.TMDB_API_KEY, 'page': page}

        try:
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
        except requests.RequestException:
            break

        for item in data.get('results', []):
            # Filter by media_type (only needed when trend_type is 'all')
            if media_type and trend_type == 'all':
                if item.get('media_type') != media_type:
                    continue

            # Filter by language
            if language and item.get('original_language') != language:
                continue

            # Filter by genre — item must have at least one matching genre
            if genre_set:
                item_genres = set(item.get('genre_ids', []))
                if not (item_genres & genre_set):
                    continue

            filtered.append(_normalize_item(item))

            # Stop once we have enough
            if len(filtered) >= 20:
                break

        if len(filtered) >= 20:
            break

    return filtered

def search_content(query):
    """Search for movies and TV shows on TMDB."""
    if not query:
        return []
    
    url = f"{TMDB_BASE_URL}/search/multi"
    params = {'api_key': settings.TMDB_API_KEY, 'query': query}
    
    try:
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
        results = data.get('results', [])
        # Filter out person results
        filtered_results = [item for item in results if item.get('media_type') != 'person']
        return [_normalize_item(item) for item in filtered_results]
    except requests.RequestException as e:
        # Log error or handle appropriately
        return []