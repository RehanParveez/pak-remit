from django.urls import path, include
from rest_framework.routers import DefaultRouter
from kyc.views import KYCViewSet

router = DefaultRouter()
router.register(r'kycview', KYCViewSet, basename = 'kycview')

urlpatterns = [
    path('', include(router.urls)),
]