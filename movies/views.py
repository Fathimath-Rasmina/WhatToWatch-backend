from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import get_object_or_404
from django.db import IntegrityError
from .services.tmdb import get_trending, get_trending_filtered, search_content
from .services.profile_analyzer import get_taste_profile
from .services.explore import get_explore_content
from .services.chat_engine import process_chat_message
from .services.recommendation import (
    get_recommendations,
    get_scored_recommendations,
    validate_mood,
    VALID_MOODS,
)
from .models import WatchedItem, FavoriteItem
from .serializers import WatchedItemSerializer, FavoriteItemSerializer

class TrendingView(APIView):
    def get(self, request):
        data = get_trending()
        return Response(data)

class SearchView(APIView):
    def get(self, request):
        query = request.GET.get('query', '').strip()
        if not query:
            return Response({'error': 'Query parameter is required'}, status=status.HTTP_400_BAD_REQUEST)
        data = search_content(query)
        return Response(data)

class WatchedListView(APIView):
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        watched_items = WatchedItem.objects.filter(user=request.user)

        # Filter by status if provided
        status_filter = request.query_params.get('status')
        if status_filter:
            valid_statuses = [s[0] for s in WatchedItem.STATUS_CHOICES]
            if status_filter in valid_statuses:
                watched_items = watched_items.filter(status=status_filter)

        serializer = WatchedItemSerializer(watched_items, many=True)
        return Response(serializer.data)
    
    def post(self, request):
        serializer = WatchedItemSerializer(data=request.data)
        if serializer.is_valid():
            try:
                serializer.save(user=request.user)
                return Response(serializer.data, status=status.HTTP_201_CREATED)
            except IntegrityError:
                return Response(
                    {'error': 'This item has already been added to your watched list.'},
                    status=status.HTTP_400_BAD_REQUEST
                )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class WatchedDetailView(APIView):
    permission_classes = [IsAuthenticated]
    
    def get_object(self, user, tmdb_id):
        return get_object_or_404(WatchedItem, user=user, tmdb_id=tmdb_id)
    
    def put(self, request, tmdb_id):
        watched_item = self.get_object(request.user, tmdb_id)
        serializer = WatchedItemSerializer(watched_item, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    def delete(self, request, tmdb_id):
        watched_item = self.get_object(request.user, tmdb_id)
        watched_item.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

class FavoriteListView(APIView):
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        favorite_items = FavoriteItem.objects.filter(user=request.user)
        serializer = FavoriteItemSerializer(favorite_items, many=True)
        return Response(serializer.data)
    
    def post(self, request):
        serializer = FavoriteItemSerializer(data=request.data)
        if serializer.is_valid():
            try:
                serializer.save(user=request.user)
                return Response(serializer.data, status=status.HTTP_201_CREATED)
            except IntegrityError:
                return Response(
                    {'error': 'This item is already in your favorites.'},
                    status=status.HTTP_400_BAD_REQUEST
                )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class FavoriteDetailView(APIView):
    permission_classes = [IsAuthenticated]
    
    def get_object(self, user, tmdb_id):
        return get_object_or_404(FavoriteItem, user=user, tmdb_id=tmdb_id)
    
    def delete(self, request, tmdb_id):
        favorite_item = self.get_object(request.user, tmdb_id)
        favorite_item.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class RecommendationView(APIView):
    """
    GET /api/movies/recommend/?mood=happy&page=1

    Returns personalised, scored recommendations based on:
      - User's watch history (dominant taste profile)
      - User preferences (genres, languages, content type)
      - Optional mood query parameter

    Results are ranked by a scoring system that prioritises what
    the user actually watches, not just generic popularity.

    Supported moods: happy, sad, stressed, bored
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        # --- Validate mood (optional) -----------------------------------------
        mood_param = request.query_params.get('mood')
        mood = None
        if mood_param:
            mood = validate_mood(mood_param)
            if mood is None:
                return Response(
                    {
                        'error': f'Invalid mood "{mood_param}". '
                                 f'Supported moods: {", ".join(VALID_MOODS)}',
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

        # --- Page parameter ---------------------------------------------------
        try:
            page = int(request.query_params.get('page', 1))
            if page < 1:
                page = 1
        except (ValueError, TypeError):
            page = 1

        # --- Fetch scored recommendations -------------------------------------
        results = get_scored_recommendations(
            user=request.user,
            mood=mood,
            page=page,
        )

        return Response({
            'mood': mood,
            'page': page,
            'count': len(results),
            'results': results,
        })


class PersonalizedTrendingView(APIView):
    """
    GET /api/movies/trending/personal/

    Returns trending content filtered by the user's dominant taste.
    If the user has no watch history, falls back to global trending.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        taste = get_taste_profile(request.user)

        # If no watch history, return global trending
        if taste['total_watched'] == 0:
            fallback_results = get_trending()
            return Response({
                'personalized': False,
                'count': len(fallback_results),
                'results': fallback_results,
            })

        results = get_trending_filtered(
            media_type=taste['dominant_content_type'],
            language=taste['dominant_language'],
            genre_ids=taste['dominant_genres'] or None,
        )

        return Response({
            'personalized': True,
            'dominant_content_type': taste['dominant_content_type'],
            'dominant_language': taste['dominant_language'],
            'count': len(results),
            'results': results,
        })


class ExploreView(APIView):
    """
    GET /api/movies/explore/

    Returns content outside the user's dominant preferences with
    partial relevance — helping users discover new content without
    affecting their main recommendations.

    Strategies used:
      - Same genres, adjacent language (e.g. K-drama fan → J-drama)
      - Same language, new genres (e.g. Korean romance fan → Korean thriller)
      - Opposite content type, same genres (e.g. TV fan → movies)
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        # --- Page parameter ---------------------------------------------------
        try:
            page = int(request.query_params.get('page', 1))
            if page < 1:
                page = 1
        except (ValueError, TypeError):
            page = 1

        data = get_explore_content(user=request.user, page=page)

        return Response({
            'strategies': data['strategies'],
            'count': len(data['results']),
            'results': data['results'],
        })


class ChatAssistantView(APIView):
    """
    POST /api/movies/chat/

    Chat-based recommendation assistant. Accepts a natural language
    message, extracts intent (mood, genre, content type, language,
    exclusions), combines it with the user's taste profile, and
    returns personalised recommendations in a conversational format.

    Request body:
        { "message": "I want a romantic K-drama" }

    Response:
        {
            "message": "Here are some romance, Korean shows for you! 🎬",
            "intent": { ... },
            "count": 20,
            "results": [ ... ]
        }
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        message = request.data.get('message', '').strip()

        if not message:
            return Response(
                {'error': 'Message is required.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        response_data = process_chat_message(
            user=request.user,
            message=message,
        )

        return Response(response_data)
