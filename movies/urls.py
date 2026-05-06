from django.urls import path
from .views import (
    TrendingView,
    SearchView,
    WatchedListView,
    WatchedDetailView,
    FavoriteListView,
    FavoriteDetailView,
    RecommendationView,
    PersonalizedTrendingView,
    ExploreView,
    ChatAssistantView,
)

urlpatterns = [
    path('trending/', TrendingView.as_view(), name='trending'),
    path('trending/personal/', PersonalizedTrendingView.as_view(), name='trending-personal'),
    path('search/', SearchView.as_view(), name='search'),
    path('watched/', WatchedListView.as_view(), name='watched-list'),
    path('watched/<int:tmdb_id>/', WatchedDetailView.as_view(), name='watched-detail'),
    path('favorites/', FavoriteListView.as_view(), name='favorite-list'),
    path('favorites/<int:tmdb_id>/', FavoriteDetailView.as_view(), name='favorite-detail'),
    path('recommend/', RecommendationView.as_view(), name='recommend'),
    path('explore/', ExploreView.as_view(), name='explore'),
    path('chat/', ChatAssistantView.as_view(), name='chat-assistant'),
]