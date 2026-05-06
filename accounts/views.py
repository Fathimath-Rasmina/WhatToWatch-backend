from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import authenticate
from .models import UserPreference
from .serializers import (
    UserRegistrationSerializer,
    UserLoginSerializer,
    UserProfileSerializer,
    UserPreferenceSerializer,
)


class RegisterView(APIView):
    def post(self, request):
        serializer = UserRegistrationSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save()
            refresh = RefreshToken.for_user(user)
            return Response({
                'user': UserProfileSerializer(user).data,
                'tokens': {
                    'refresh': str(refresh),
                    'access': str(refresh.access_token),
                }
            }, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class LoginView(APIView):
    def post(self, request):
        serializer = UserLoginSerializer(data=request.data)
        if serializer.is_valid():
            user = authenticate(email=serializer.validated_data['email'], password=serializer.validated_data['password'])
            if user:
                refresh = RefreshToken.for_user(user)
                return Response({
                    'user': UserProfileSerializer(user).data,
                    'tokens': {
                        'refresh': str(refresh),
                        'access': str(refresh.access_token),
                    }
                })
            return Response({'error': 'Invalid credentials'}, status=status.HTTP_401_UNAUTHORIZED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class ProfileView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        serializer = UserProfileSerializer(request.user)
        return Response(serializer.data)


class UserPreferenceView(APIView):
    """
    GET  /api/preferences/ — Retrieve the authenticated user's preferences.
    POST /api/preferences/ — Create preferences (if none exist).
    PUT  /api/preferences/ — Update existing preferences.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        try:
            preference = UserPreference.objects.get(user=request.user)
        except UserPreference.DoesNotExist:
            return Response(
                {'detail': 'Preferences not set yet.'},
                status=status.HTTP_404_NOT_FOUND,
            )
        serializer = UserPreferenceSerializer(preference)
        return Response(serializer.data)

    def post(self, request):
        # If preferences already exist, tell the user to use PUT instead.
        if UserPreference.objects.filter(user=request.user).exists():
            return Response(
                {'detail': 'Preferences already exist. Use PUT to update.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        serializer = UserPreferenceSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save(user=request.user)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def put(self, request):
        preference, created = UserPreference.objects.get_or_create(
            user=request.user,
        )
        serializer = UserPreferenceSerializer(
            preference,
            data=request.data,
            partial=True,
        )
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
