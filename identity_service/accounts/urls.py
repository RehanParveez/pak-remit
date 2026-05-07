from django.urls import path, include
from rest_framework.routers import DefaultRouter
from accounts.views import AuthViewSet, UserViewSet, CustomTokenObtainPairView
from rest_framework_simplejwt.views import TokenRefreshView

router = DefaultRouter()
router.register(r'auth', AuthViewSet, basename = 'auth')
router.register(r'user', UserViewSet, basename = 'user')

urlpatterns = [
    path('', include(router.urls)),
    path('tokenobtainpair/', CustomTokenObtainPairView.as_view(), name = 'token_obtain_pair'),
    path('tokenrefresh/', TokenRefreshView.as_view(), name = 'token_refresh'),
    path('api-auth/', include('rest_framework.urls')),
]