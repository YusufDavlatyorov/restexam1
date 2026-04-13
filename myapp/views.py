from datetime import timedelta

from django.db.models import Avg, Case, Count, IntegerField, Q, Sum, When
from django.utils import timezone
from rest_framework.generics import (
    CreateAPIView,
    ListAPIView,
    ListCreateAPIView,
    RetrieveDestroyAPIView,
    RetrieveUpdateDestroyAPIView,
)
from rest_framework.response import Response
from rest_framework.views import APIView

from .filters import filter_videos
from .models import Chanels, Comments, Likes, Users, Videos
from .pagination import CustomPagination
from .serializers import (
    ChanelDetailSerializer,
    ChanelSerializers,
    CommentDetailSerializers,
    CommentSerializers,
    LikeToggleSerializer,
    UserDetailSerializers,
    UsersSerializers,
    VideoLikesListSerializer,
    VideoSerializers,
)


class UsersListCreateAPIView(ListCreateAPIView):
    serializer_class = UsersSerializers
    pagination_class = CustomPagination

    def get_queryset(self):
        return Users.objects.annotate(channels_count=Count('chanels'))


class UserDetailAPIView(RetrieveUpdateDestroyAPIView):
    serializer_class = UserDetailSerializers
    queryset = Users.objects.all()


class UserChannelsListAPIView(ListAPIView):
    serializer_class = ChanelSerializers
    pagination_class = CustomPagination

    def get_queryset(self):
        return Chanels.objects.filter(user_id=self.kwargs.get('pk')).annotate(
            videos_count=Count('videos', distinct=True),
            subscribers_count=Count('subscription', distinct=True)
        )


class ChanelListCreateAPIView(ListCreateAPIView):
    serializer_class = ChanelSerializers
    pagination_class = CustomPagination

    def get_queryset(self):
        return Chanels.objects.annotate(
            subscribers_count=Count('subscription', distinct=True),
            videos_count=Count('videos', distinct=True)
        ).select_related('user')

    def create(self, request, *args, **kwargs):
        response = super().create(request, *args, **kwargs)
        response.data['stats'] = {'videos_count': 0, 'subscribers_count': 0}
        return response


class ChanelDetailAPIView(RetrieveUpdateDestroyAPIView):
    queryset = Chanels.objects.all()
    serializer_class = ChanelDetailSerializer

    def update(self, request, *args, **kwargs):
        response = super().update(request, *args, **kwargs)
        response.data['updated'] = True
        return response

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        channel_id = instance.id
        self.perform_destroy(instance)
        return Response({'status': 'deleted', 'deleted_channel_id': channel_id})


class ChanelVideosListView(ListAPIView):
    serializer_class = VideoSerializers
    pagination_class = CustomPagination

    def get_queryset(self):
        queryset = Videos.objects.filter(chanel_id=self.kwargs.get('pk'))
        sort = self.request.query_params.get('sort')
        queryset = queryset.order_by('-views') if sort == 'popular' else queryset.order_by('-created_at')
        start_date = self.request.query_params.get('start_date')
        end_date = self.request.query_params.get('end_date')
        if start_date and end_date:
            queryset = queryset.filter(created_at__range=[start_date, end_date])
        return queryset


class ChanelStatsView(APIView):
    def get(self, request, pk):
        videos = Videos.objects.filter(chanel_id=pk)
        stats = videos.aggregate(total_videos=Count('id'), total_views=Sum('views'), avg_views=Avg('views'))
        top_video = videos.order_by('-views').first()
        return Response({
            'total_videos': stats['total_videos'] or 0,
            'total_views': stats['total_views'] or 0,
            'avg_views_per_video': stats['avg_views'] or 0,
            'top_video': VideoSerializers(top_video).data if top_video else None
        })


class VideoListCreateAPIView(ListCreateAPIView):
    serializer_class = VideoSerializers
    pagination_class = CustomPagination

    def get_queryset(self):
        return filter_videos(self.request, Videos.objects.all().select_related('chanel'))


class VideoDetailAPIView(RetrieveUpdateDestroyAPIView):
    serializer_class = VideoSerializers

    def get_queryset(self):
        return Videos.objects.annotate(
            comments_count=Count('comments', distinct=True),
            likes_count=Count('likes', distinct=True)
        ).select_related('chanel')

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        instance.views += 1
        instance.save(update_fields=['views'])
        return Response(self.get_serializer(instance).data)

    def update(self, request, *args, **kwargs):
        instance = self.get_object()
        old_title, old_description = instance.title, instance.description
        serializer = self.get_serializer(instance, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response({
            'updated_object': serializer.data,
            'diff': {
                'before': {'title': old_title, 'description': old_description},
                'after': {'title': instance.title, 'description': instance.description}
            }
        })

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        info = {
            'status': 'deleted',
            'cascade_delete_info': {
                'comments': instance.comments.count(),
                'likes': instance.likes.count()
            }
        }
        instance.delete()
        return Response(info)


class VideoCommentsListAPIView(ListAPIView):
    serializer_class = CommentSerializers
    pagination_class = CustomPagination

    def get_queryset(self):
        queryset = Comments.objects.filter(video_id=self.kwargs.get('pk')).select_related('user')
        sort = self.request.query_params.get('sort')
        return queryset.order_by('created_at') if sort == 'old' else queryset.order_by('-created_at')


class VideoCommentCreateAPIView(CreateAPIView):
    serializer_class = CommentSerializers

    def perform_create(self, serializer):
        serializer.save(video_id=self.kwargs.get('pk'))


class CommentDetailAPIView(RetrieveDestroyAPIView):
    queryset = Comments.objects.all().select_related('user', 'video')
    serializer_class = CommentDetailSerializers

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        comment_id = instance.id
        instance.delete()
        return Response({'status': 'deleted', 'deleted_comment_id': comment_id})


class VideoLikeAPIView(APIView):
    def post(self, request, pk):
        data = request.data.copy()
        data['video_id'] = pk
        serializer = LikeToggleSerializer(data=data)
        serializer.is_valid(raise_exception=True)
        result = serializer.save()
        return Response({'liked': result['liked'], 'total_likes': result['total_likes']})

    def delete(self, request, pk):
        Likes.objects.filter(video_id=pk, user_id=request.data.get('user_id')).delete()
        return Response({'liked': False, 'total_likes': Likes.objects.filter(video_id=pk).count()})


class VideoLikesListAPIView(ListAPIView):
    serializer_class = VideoLikesListSerializer

    def get_queryset(self):
        return Likes.objects.filter(video_id=self.kwargs.get('pk')).select_related('user')

    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        return Response({
            'users': self.get_serializer(queryset, many=True).data,
            'total_count': queryset.count(),
            'is_liked_by_current_user': True
        })


class VideoSearchAPIView(ListAPIView):
    serializer_class = VideoSerializers

    def get_queryset(self):
        query = self.request.GET.get('query', '')
        queryset = Videos.objects.all().select_related('chanel')
        if query:
            queryset = queryset.filter(
                Q(title__icontains=query) | Q(description__icontains=query)
            ).annotate(
                relevance=Case(
                    When(title__icontains=query, then=2),
                    When(description__icontains=query, then=1),
                    default=0,
                    output_field=IntegerField()
                )
            ).order_by('-relevance')
        return queryset


class VideoTopAPIView(ListAPIView):
    serializer_class = VideoSerializers

    def get_queryset(self):
        queryset = Videos.objects.all().select_related('chanel')
        period = self.request.query_params.get('period')
        if period == 'day':
            queryset = queryset.filter(created_at__date=timezone.now().date())
        elif period == 'week':
            queryset = queryset.filter(created_at__gte=timezone.now() - timedelta(days=7))
        elif period == 'month':
            queryset = queryset.filter(created_at__gte=timezone.now() - timedelta(days=30))
        return queryset.order_by('-views')[:10]


class VideoRelatedAPIView(ListAPIView):
    serializer_class = VideoSerializers

    def get_queryset(self):
        current = Videos.objects.get(id=self.kwargs.get('pk'))
        return Videos.objects.filter(chanel=current.chanel).exclude(id=current.id).order_by('-views')[:10]


class StatsVideosAPIView(APIView):
    def get(self, request):
        stats = Videos.objects.aggregate(total_videos=Count('id'), total_views=Sum('views'), avg_views=Avg('views'))
        return Response({
            'total_videos': stats['total_videos'] or 0,
            'total_views': stats['total_views'] or 0,
            'avg_views': stats['avg_views'] or 0
        })


class StatsUsersAPIView(APIView):
    def get(self, request):
        total_users = Users.objects.count()
        users_with_channels = Users.objects.annotate(c_count=Count('chanels')).filter(c_count__gt=0).count()
        return Response({
            'total_users': total_users,
            'users_with_channels': users_with_channels,
            'active_users': total_users
        })


class StatsChannelsAPIView(APIView):
    def get(self, request):
        top_channel = Chanels.objects.annotate(all_views=Sum('videos__views')).order_by('-all_views').first()
        avg_videos = Chanels.objects.annotate(v_count=Count('videos')).aggregate(Avg('v_count'))
        return Response({
            'total_channels': Chanels.objects.count(),
            'top_channel_by_views': top_channel.title if top_channel else None,
            'average_videos_per_channel': avg_videos['v_count__avg'] or 0
        })