from django.urls import path, include
from rest_framework.routers import DefaultRouter
from statements.views import StatementViewSet, DifferenceViewSet

router = DefaultRouter()
router.register(r'statement', StatementViewSet, basename = 'statement'),
router.register(r'difference', DifferenceViewSet, basename = 'difference'),

urlpatterns = [
    path('', include(router.urls)),
]