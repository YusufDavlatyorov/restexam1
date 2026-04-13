from django.db.models import Q


def filter_videos(request, queryset):
    search_query = request.GET.get('search')
    if search_query:
        queryset = queryset.filter(
            Q(title__icontains=search_query) |
            Q(description__icontains=search_query)
        )

    chanel_id = request.GET.get('chanel')
    if chanel_id:
        queryset = queryset.filter(chanel_id=chanel_id)

    ordering = request.GET.get('ordering')
    if ordering:
        queryset = queryset.order_by(ordering)
    else:
        queryset = queryset.order_by('-created_at')

    return queryset