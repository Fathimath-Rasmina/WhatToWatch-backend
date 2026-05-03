from django.db import models
from django.contrib.auth import get_user_model
from django.core.validators import MinValueValidator, MaxValueValidator

User = get_user_model()

class WatchedItem(models.Model):
    MEDIA_TYPE_CHOICES = [
        ('movie', 'Movie'),
        ('tv', 'TV Show'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='watched_items')
    tmdb_id = models.IntegerField()
    title = models.CharField(max_length=255)
    media_type = models.CharField(max_length=10, choices=MEDIA_TYPE_CHOICES)
    poster_path = models.CharField(max_length=255, null=True, blank=True)
    rating = models.IntegerField(
        null=True,
        blank=True,
        validators=[MinValueValidator(1), MaxValueValidator(5)]
    )
    watched_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-watched_at']
        unique_together = ('user', 'tmdb_id')
    
    def __str__(self):
        return f"{self.title} - {self.user.username}"

class FavoriteItem(models.Model):
    MEDIA_TYPE_CHOICES = [
        ('movie', 'Movie'),
        ('tv', 'TV Show'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='favorite_items')
    tmdb_id = models.IntegerField()
    title = models.CharField(max_length=255)
    media_type = models.CharField(max_length=10, choices=MEDIA_TYPE_CHOICES)
    poster_path = models.CharField(max_length=255, null=True, blank=True)
    added_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-added_at']
        unique_together = ('user', 'tmdb_id')
    
    def __str__(self):
        return f"{self.title} - {self.user.username}"
