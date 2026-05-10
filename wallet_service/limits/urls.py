from django.urls import path, include
from rest_framework.routers import DefaultRouter
from limits.views import SpendingViewSet, FraudFlagViewSet

router = DefaultRouter()
router.register(r'spending', SpendingViewSet, basename = 'spending')
router.register(r'fraudflags', FraudFlagViewSet, basename = 'fraudflags')

urlpatterns = [
    path('', include(router.urls)),
]