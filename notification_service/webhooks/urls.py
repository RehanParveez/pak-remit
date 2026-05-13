from django.urls import path, include
from rest_framework.routers import DefaultRouter
from webhooks.views import WebhookEndpointViewSet, WebhookDeliveryViewSet

router = DefaultRouter()
router.register(r'webhook', WebhookEndpointViewSet, basename = 'webhook'),
router.register(r'webhookdelivery', WebhookDeliveryViewSet, basename = 'webhookdelivery'),

urlpatterns = [
    path('', include(router.urls)),
]