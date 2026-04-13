from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response

class CustomPagination(PageNumberPagination):
    page_size=5
    page_query_param='page'
    page_size_query_param='size'
    max_page_size=10

    def get_paginated_response(self, data):
        return Response({
            'total_items':self.page.paginator.count,
            'total_pages':self.page.paginator.num_pages,
            'current_page':self.page.number,
            'results':data
        })