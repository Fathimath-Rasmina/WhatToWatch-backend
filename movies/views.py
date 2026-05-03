from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import get_object_or_404
from django.db import IntegrityError
from .services.tmdb import get_trending, search_content
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
