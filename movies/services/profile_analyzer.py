"""
Profile Analyzer Service.

Analyzes a user's watch history (WatchedItem data) to detect
dominant content patterns — content type, language, genres, and
rating-based genre preferences.
"""

from collections import Counter
from movies.models import WatchedItem


def get_taste_profile(user):
    """
    Analyze the user's watched items and return a taste profile dict.

    Returns:
        {
            "dominant_content_type": "tv" | "movie" | None,
            "dominant_language": "ko" | "en" | ... | None,
            "dominant_genres": [18, 10749, ...],
            "high_rated_genres": [10749, 35, ...],
            "low_rated_genres": [27, 53, ...],
            "total_watched": 42,
            "content_type_distribution": {"tv": 34, "movie": 8},
            "language_distribution": {"ko": 30, "en": 10, ...},
            "genre_distribution": {18: 25, 10749: 20, ...},
        }
    """
    # Only analyze items the user actually watched/is watching.
    # Dropped, not_interested, plan_to_watch, on_hold don't reflect taste.
    TASTE_STATUSES = ['completed', 'watching']
    watched_items = WatchedItem.objects.filter(
        user=user,
        status__in=TASTE_STATUSES,
    )

    if not watched_items.exists():
        return _empty_profile()

    total = watched_items.count()

    # --- Content type distribution -------------------------------------------
    content_type_counts = Counter()
    for item in watched_items.values_list('media_type', flat=True):
        if item:
            content_type_counts[item] += 1

    dominant_content_type = (
        content_type_counts.most_common(1)[0][0]
        if content_type_counts else None
    )

    # --- Language distribution ------------------------------------------------
    language_counts = Counter()
    for item in watched_items.values_list('original_language', flat=True):
        if item:  # skip empty strings
            language_counts[item] += 1

    dominant_language = (
        language_counts.most_common(1)[0][0]
        if language_counts else None
    )

    # --- Genre distribution ---------------------------------------------------
    genre_counts = Counter()
    for genre_list in watched_items.values_list('genre_ids', flat=True):
        if genre_list:
            for gid in genre_list:
                genre_counts[gid] += 1

    # Top genres (up to 5)
    dominant_genres = [gid for gid, _ in genre_counts.most_common(5)]

    # --- Rating-based genre analysis -----------------------------------------
    high_rated_genres = _genres_by_rating_range(watched_items, min_rating=4, max_rating=5)
    low_rated_genres = _genres_by_rating_range(watched_items, min_rating=1, max_rating=2)

    return {
        'dominant_content_type': dominant_content_type,
        'dominant_language': dominant_language,
        'dominant_genres': dominant_genres,
        'high_rated_genres': high_rated_genres,
        'low_rated_genres': low_rated_genres,
        'total_watched': total,
        'content_type_distribution': dict(content_type_counts),
        'language_distribution': dict(language_counts),
        'genre_distribution': dict(genre_counts),
    }


def _genres_by_rating_range(watched_qs, min_rating, max_rating):
    """
    Collect genre IDs from items whose rating falls within
    [min_rating, max_rating]. Returns a deduplicated list sorted
    by frequency (most common first), up to 5 genres.
    """
    rated_items = watched_qs.filter(
        rating__gte=min_rating,
        rating__lte=max_rating,
    )
    genre_counts = Counter()
    for genre_list in rated_items.values_list('genre_ids', flat=True):
        if genre_list:
            for gid in genre_list:
                genre_counts[gid] += 1

    return [gid for gid, _ in genre_counts.most_common(5)]


def _empty_profile():
    """Return a blank taste profile for users with no watch history."""
    return {
        'dominant_content_type': None,
        'dominant_language': None,
        'dominant_genres': [],
        'high_rated_genres': [],
        'low_rated_genres': [],
        'total_watched': 0,
        'content_type_distribution': {},
        'language_distribution': {},
        'genre_distribution': {},
    }
