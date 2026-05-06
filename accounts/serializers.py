from rest_framework import serializers
from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from .models import UserPreference

User = get_user_model()

class UserRegistrationSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, required=True, validators=[validate_password])
    password_confirm = serializers.CharField(write_only=True, required=True)

    class Meta:
        model = User
        fields = ('username', 'email', 'password', 'password_confirm')

    def validate(self, attrs):
        if attrs['password'] != attrs['password_confirm']:
            raise serializers.ValidationError({"password": "Password fields didn't match."})
        return attrs

    def create(self, validated_data):
        validated_data.pop('password_confirm')
        user = User.objects.create_user(**validated_data)
        return user

class UserLoginSerializer(serializers.Serializer):
    email = serializers.EmailField(required=True)
    password = serializers.CharField(required=True, write_only=True)

class UserProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ('id', 'username', 'email', 'created_at')
        read_only_fields = ('id', 'created_at')


class UserPreferenceSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserPreference
        fields = (
            'preferred_genres',
            'preferred_languages',
            'content_type',
            'updated_at',
        )
        read_only_fields = ('updated_at',)

    def validate_preferred_genres(self, value):
        """Ensure preferred_genres is a list of integers (TMDB genre IDs)."""
        if not isinstance(value, list):
            raise serializers.ValidationError('Must be a list of genre IDs.')
        if not all(isinstance(g, int) for g in value):
            raise serializers.ValidationError('Each genre ID must be an integer.')
        return value

    def validate_preferred_languages(self, value):
        """Ensure preferred_languages is a list of language code strings."""
        if not isinstance(value, list):
            raise serializers.ValidationError('Must be a list of language codes.')
        if not all(isinstance(lang, str) and len(lang) == 2 for lang in value):
            raise serializers.ValidationError(
                'Each language must be a 2-letter ISO 639-1 code (e.g. "en", "ko").'
            )
        return value