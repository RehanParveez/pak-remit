from django.urls import path, include
from rest_framework.routers import DefaultRouter
from refunds.views import RefundViewSet

router = DefaultRouter()
router.register(r'refund', RefundViewSet,  basename = 'refund')

urlpatterns = [
    path('', include(router.urls)),
]