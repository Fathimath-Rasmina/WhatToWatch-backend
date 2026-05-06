from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    email = models.EmailField(unique=True)
    created_at = models.DateTimeField(auto_now_add=True)

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username']

    class Meta:
        ordering = ['-created_at']


class UserPreference(models.Model):
    CONTENT_TYPE_CHOICES = [
        ('movie', 'Movie'),
        ('tv', 'TV Show'),
        ('both', 'Both'),
    ]

    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='preference',
    )
    preferred_genres = models.JSONField(
        default=list,
        blank=True,
        help_text='List of TMDB genre IDs, e.g. [28, 35, 18]',
    )
    preferred_languages = models.JSONField(
        default=list,
        blank=True,
        help_text='List of ISO 639-1 language codes, e.g. ["en", "ko", "zh"]',
    )
    content_type = models.CharField(
        max_length=10,
        choices=CONTENT_TYPE_CHOICES,
        default='both',
    )
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Preferences for {self.user.username}"
