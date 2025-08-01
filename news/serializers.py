# news/serializers.py

from rest_framework import serializers
from .models import Article, Category, UserPreference # Import UserPreference

class ArticleSerializer(serializers.ModelSerializer):
    # Note: Using 'url' and 'published_at' as per your Article model's actual field names.
    categories = serializers.StringRelatedField(many=True, read_only=True)

    class Meta:
        model = Article
        fields = ['id', 'title', 'summary', 'url', 'published_at', 'author', 'source', 'categories', 'audio_file']


# Corrected UserPreferenceSerializer
class UserPreferenceSerializer(serializers.ModelSerializer):
    # This field maps directly to the 'preferred_categories' M2M field on the UserPreference model.
    # PrimaryKeyRelatedField allows mobile apps to send/receive category IDs.
    preferred_categories = serializers.PrimaryKeyRelatedField(
        queryset=Category.objects.all(),
        many=True # Indicates it's a Many-to-Many relationship
    )

    class Meta:
        model = UserPreference
        # Ensure 'preferred_categories' is in fields, matching the declaration above.
        fields = ['id', 'user', 'preferred_categories']
        read_only_fields = ['user'] # User should be set automatically by the view