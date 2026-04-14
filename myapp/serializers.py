from django.db.models import Sum
from rest_framework import serializers
from .models import Users, Chanels, Comments, Likes, Videos


class RegisterSerializer(serializers.ModelSerializer):
    class Meta:
        model = Users
        fields = ['username', 'password']

    def create(self, validated_data):
        user = Users.objects.create_user(
            username=validated_data['username'],
            password=validated_data['password']
        )
        return user


class UsersSerializers(serializers.ModelSerializer):
    date_joined = serializers.DateTimeField(read_only=True)
    channels_count = serializers.IntegerField(read_only=True, default=0)

    class Meta:
        model = Users
        fields = ['id', 'username', 'email', 'date_joined', 'channels_count']


class ChanelSerializers(serializers.ModelSerializer):
    created_at = serializers.DateTimeField(read_only=True)
    user = UsersSerializers(read_only=True)
    videos_count = serializers.IntegerField(read_only=True, default=0)
    subscribers_count = serializers.IntegerField(read_only=True, default=0)
    user_id = serializers.PrimaryKeyRelatedField(
        queryset=Users.objects.all(),
        write_only=True,
        source='user'
    )

    class Meta:
        model = Chanels
        fields = ['id', 'user', 'user_id', 'title', 'avatar', 'description', 'created_at', 'videos_count', 'subscribers_count']


class VideoSerializers(serializers.ModelSerializer):
    created_at = serializers.DateTimeField(read_only=True)
    chanel = ChanelSerializers(read_only=True)
    comments_count = serializers.IntegerField(read_only=True, default=0)
    likes_count = serializers.IntegerField(read_only=True, default=0)
    chanel_id = serializers.PrimaryKeyRelatedField(
        queryset=Chanels.objects.all(),
        write_only=True,
        source='chanel'
    )

    class Meta:
        model = Videos
        fields = ['id', 'chanel', 'chanel_id', 'title', 'description', 'video_file', 'views', 'created_at', 'comments_count', 'likes_count']


class CommentSerializers(serializers.ModelSerializer):
    created_at = serializers.DateTimeField(read_only=True)
    user = UsersSerializers(read_only=True)
    video_id = serializers.IntegerField(read_only=True, source='video.id')
    user_id = serializers.PrimaryKeyRelatedField(
        queryset=Users.objects.all(),
        write_only=True,
        source='user'
    )

    class Meta:
        model = Comments
        fields = ['id', 'user', 'user_id', 'video_id', 'text', 'created_at']


class CommentDetailSerializers(serializers.ModelSerializer):
    created_at = serializers.DateTimeField(read_only=True)
    user = UsersSerializers(read_only=True)
    video = VideoSerializers(read_only=True)

    class Meta:
        model = Comments
        fields = ['id', 'user', 'video', 'text', 'created_at']


class LikeSerializers(serializers.ModelSerializer):
    created_at = serializers.DateTimeField(read_only=True)
    user = UsersSerializers(read_only=True)
    video = VideoSerializers(read_only=True)
    user_id = serializers.PrimaryKeyRelatedField(
        queryset=Users.objects.all(),
        write_only=True,
        source='user'
    )
    video_id = serializers.PrimaryKeyRelatedField(
        queryset=Videos.objects.all(),
        write_only=True,
        source='video'
    )

    class Meta:
        model = Likes
        fields = ['id', 'user', 'video', 'user_id', 'video_id', 'created_at']


class VideoLikesListSerializer(serializers.ModelSerializer):
    user = UsersSerializers(read_only=True)
    is_liked_by_current_user = serializers.SerializerMethodField()

    class Meta:
        model = Likes
        fields = ['user', 'is_liked_by_current_user']

    def get_is_liked_by_current_user(self, obj):
        fake_user_id = 1
        return obj.user.id == fake_user_id


class LikeToggleSerializer(serializers.ModelSerializer):
    user = UsersSerializers(read_only=True)
    video = VideoSerializers(read_only=True)
    user_id = serializers.PrimaryKeyRelatedField(
        queryset=Users.objects.all(),
        write_only=True,
        source='user'
    )
    video_id = serializers.PrimaryKeyRelatedField(
        queryset=Videos.objects.all(),
        write_only=True,
        source='video'
    )
    liked = serializers.BooleanField(read_only=True)
    total_likes = serializers.IntegerField(read_only=True)

    class Meta:
        model = Likes
        fields = ['user', 'video', 'user_id', 'video_id', 'liked', 'total_likes']

    def create(self, validated_data):
        user = validated_data['user']
        video = validated_data['video']
        like_qs = Likes.objects.filter(user=user, video=video)
        if like_qs.exists():
            like_qs.delete()
            liked = False
        else:
            Likes.objects.create(user=user, video=video)
            liked = True
        return {
            'user': user,
            'video': video,
            'liked': liked,
            'total_likes': Likes.objects.filter(video=video).count()
        }


class UserDetailSerializers(serializers.ModelSerializer):
    date_joined = serializers.DateTimeField(read_only=True)
    chanels = ChanelSerializers(many=True, read_only=True)
    total_video = serializers.SerializerMethodField()

    class Meta:
        model = Users
        fields = ['id', 'username', 'email', 'date_joined', 'chanels', 'total_video']

    def get_total_video(self, obj):
        return Videos.objects.filter(chanel__user=obj).count()


class ChanelDetailSerializer(serializers.ModelSerializer):
    user = UsersSerializers(read_only=True)
    last_videos = serializers.SerializerMethodField()
    total_views = serializers.SerializerMethodField()

    class Meta:
        model = Chanels
        fields = ['id', 'user', 'title', 'description', 'avatar', 'created_at', 'last_videos', 'total_views']

    def get_last_videos(self, obj):
        videos = Videos.objects.filter(chanel=obj).order_by('-created_at')[:5]
        return VideoSerializers(videos, many=True).data

    def get_total_views(self, obj):
        return Videos.objects.filter(chanel=obj).aggregate(Sum('views'))['views__sum'] or 0