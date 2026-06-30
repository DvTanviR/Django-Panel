from celery import shared_task
import time
import dns.resolver
import logging
from django.utils import timezone
from django.conf import settings
from panel_app.models import Domain, Project
from panel_app.caddy_client import update_caddy_route

logger = logging.getLogger(__name__)

def check_dns(hostname, expected_ip):
    try:
        answers = dns.resolver.resolve(hostname, 'A')
        for rdata in answers:
            if str(rdata) == expected_ip:
                return True
    except Exception:
        pass
    return False

@shared_task(bind=True)
def verify_domain_dns(self, domain_id):
    domain = Domain.objects.get(id=domain_id)
    project = domain.project
    expected_ip = settings.SERVER_IP
    
    if not expected_ip or expected_ip == '127.0.0.1':
        logger.warning(f"DNS verification skipped for {domain.hostname} - no public SERVER_IP configured")
        domain.dns_verified = False
        domain.save(update_fields=['dns_verified'])
        return False
    
    max_attempts = 60
    for i in range(max_attempts):
        if check_dns(domain.hostname, expected_ip):
            domain.dns_verified = True
            domain.verified_at = timezone.now()
            domain.save(update_fields=['dns_verified', 'verified_at'])
            
            primary_domain = project.domains.filter(is_primary=True).first()
            route_domain = primary_domain.hostname if primary_domain else domain.hostname
            update_caddy_route(project, route_domain)
            
            logger.info(f"DNS verified for {domain.hostname}")
            return True
        
        time.sleep(10)
    
    domain.dns_verified = False
    domain.save(update_fields=['dns_verified'])
    logger.warning(f"DNS verification failed for {domain.hostname}")
    return False
