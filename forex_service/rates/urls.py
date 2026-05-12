from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rates.views import ForexViewSet

router = DefaultRouter()
router.register(r'forex', ForexViewSet, basename = 'forex')

urlpatterns = [
    path('', include(router.urls)),
]