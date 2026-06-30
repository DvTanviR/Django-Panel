from django.urls import path
from panel_app import domain_views

urlpatterns = [
    path('<int:domain_id>/verify/', domain_views.verify_domain, name='verify_domain'),
]
