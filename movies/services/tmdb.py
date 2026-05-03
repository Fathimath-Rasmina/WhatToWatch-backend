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