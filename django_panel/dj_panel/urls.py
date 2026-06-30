from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from rest_framework.routers import DefaultRouter
from panel_app.admin_site import admin_site
from panel_app.api import ProjectViewSet, DeploymentViewSet, DomainViewSet, EnvironmentVariableViewSet, WebhookEventViewSet

router = DefaultRouter()
router.register(r'projects', ProjectViewSet, basename='project')
router.register(r'deployments', DeploymentViewSet, basename='deployment')
router.register(r'domains', DomainViewSet, basename='domain')
router.register(r'env-vars', EnvironmentVariableViewSet, basename='env-var')
router.register(r'webhook-events', WebhookEventViewSet, basename='webhook-event')

urlpatterns = [
    path('', admin_site.urls),
    path('api/', include(router.urls)),
    path('api/auth/', include('rest_framework.urls')),
    path('api/webhooks/github/', include('panel_app.github_urls')),
    path('api/github/', include('panel_app.github_app_urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
