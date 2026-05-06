from django.db import models
from django.contrib.auth import get_user_model
from django.core.validators import MinValueValidator, MaxValueValidator

User = get_user_model()

class WatchedItem(models.Model):
    MEDIA_TYPE_CHOICES = [
        ('movie', 'Movie'),
        ('tv', 'TV Show'),
    ]

    STATUS_CHOICES = [
        ('watching', 'Currently Watching'),
        ('completed', 'Completed'),
        ('plan_to_watch', 'Plan to Watch'),
        ('on_hold', 'On Hold'),
        ('dropped', 'Dropped'),
        ('not_interested', 'Not Interested'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='watched_items')
    tmdb_id = models.IntegerField()
    title = models.CharField(max_length=255)
    media_type = models.CharField(max_length=10, choices=MEDIA_TYPE_CHOICES)
    poster_path = models.CharField(max_length=255, null=True, blank=True)
    genre_ids = models.JSONField(
        default=list,
        blank=True,
        help_text='List of TMDB genre IDs, e.g. [18, 10749]',
    )
    original_language = models.CharField(
        max_length=10,
        blank=True,
        default='',
        help_text='ISO 639-1 language code, e.g. "en", "ko"',
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='completed',
        help_text='Current watch status',
    )
    rating = models.IntegerField(
        null=True,
        blank=True,
        validators=[MinValueValidator(1), MaxValueValidator(5)]
    )
    watched_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-updated_at']
        unique_together = ('user', 'tmdb_id')
    
    def __str__(self):
        return f"{self.title} ({self.status}) - {self.user.username}"

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
