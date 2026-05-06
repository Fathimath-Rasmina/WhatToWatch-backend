from rest_framework import serializers
from .models import WatchedItem, FavoriteItem

class WatchedItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = WatchedItem
        fields = ('id', 'tmdb_id', 'title', 'media_type', 'poster_path',
                  'genre_ids', 'original_language', 'status', 'rating',
                  'watched_at', 'updated_at')
        read_only_fields = ('id', 'watched_at', 'updated_at')

    def validate_rating(self, value):
        if value is not None and (value < 1 or value > 5):
            raise serializers.ValidationError("Rating must be between 1 and 5.")
        return value

    def validate_status(self, value):
        valid_statuses = [s[0] for s in WatchedItem.STATUS_CHOICES]
        if value not in valid_statuses:
            raise serializers.ValidationError(
                f"Invalid status. Must be one of: {', '.join(valid_statuses)}"
            )
        return value

class FavoriteItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = FavoriteItem
        fields = ('id', 'tmdb_id', 'title', 'media_type', 'poster_path', 'added_at')
        read_only_fields = ('id', 'added_at')