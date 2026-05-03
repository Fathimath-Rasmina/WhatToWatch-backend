from rest_framework import serializers
from .models import WatchedItem, FavoriteItem

class WatchedItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = WatchedItem
        fields = ('id', 'tmdb_id', 'title', 'media_type', 'poster_path', 'rating', 'watched_at')
        read_only_fields = ('id', 'watched_at')

    def validate_rating(self, value):
        if value is not None and (value < 1 or value > 5):
            raise serializers.ValidationError("Rating must be between 1 and 5.")
        return value

class FavoriteItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = FavoriteItem
        fields = ('id', 'tmdb_id', 'title', 'media_type', 'poster_path', 'added_at')
        read_only_fields = ('id', 'added_at')