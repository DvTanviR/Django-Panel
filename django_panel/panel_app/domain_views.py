from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.decorators import login_required
from panel_app.models import Domain, Project
from panel_app.domain_tasks import verify_domain_dns
import logging

logger = logging.getLogger(__name__)

@login_required
@require_POST
def verify_domain(request, domain_id):
    try:
        domain = Domain.objects.get(id=domain_id)
        project = domain.project
        
        is_primary = not project.domains.filter(is_primary=True).exists()
        if is_primary:
            domain.is_primary = True
            domain.save(update_fields=['is_primary'])
        
        verify_domain_dns.delay(domain_id)
        
        return JsonResponse({
            'status': 'verifying',
            'domain': domain.hostname,
            'message': 'DNS verification started. This may take a few minutes.'
        })
    except Domain.DoesNotExist:
        return JsonResponse({'error': 'Domain not found'}, status=404)
    except Exception as e:
        logger.error(f"Domain verification error: {e}")
        return JsonResponse({'error': str(e)}, status=500)
