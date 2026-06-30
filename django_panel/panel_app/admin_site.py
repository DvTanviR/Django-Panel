from django.contrib import admin
from django.urls import path
from django.shortcuts import render
from .models import Project

class PanelAdmin(admin.AdminSite):
    site_header = "DeployDjango Panel"
    site_title = "DeployDjango"
    index_title = "Dashboard"
    
    def get_urls(self):
        from django.urls import path
        urls = super().get_urls()
        custom_urls = [
            path('', self.admin_view(self.dashboard), name='dashboard'),
        ]
        return custom_urls + urls
    
    def dashboard(self, request):
        projects = Project.objects.all()
        return render(request, 'panel_app/dashboard.html', {'projects': projects})

admin_site = PanelAdmin()
admin_site.register(Project)
admin_site.register(Deployment)
admin_site.register(Domain)
admin_site.register(EnvironmentVariable)
admin_site.register(WebhookEvent)
