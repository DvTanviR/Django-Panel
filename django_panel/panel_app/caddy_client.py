import requests
import json
import logging
from django.conf import settings

logger = logging.getLogger(__name__)

def get_caddy_config():
    try:
        r = requests.get(f"{settings.CADDY_ADMIN_API}/config/", timeout=5)
        if r.status_code == 200:
            return r.json()
    except Exception as e:
        logger.error(f"Caddy config fetch error: {e}")
    return None

def _build_server_config(project, domain):
    upstream = f"localhost:{project.internal_port}"
    return {
        "handler": "reverse_proxy",
        "transport": {"protocol": "http"},
        "upstreams": [{"dial": upstream}]
    }

def update_caddy_route(project, domain):
    try:
        config = get_caddy_config()
        if not config:
            logger.error("Could not fetch Caddy config")
            return False
        
        apps = config.get('apps', {})
        http = apps.get('http', {})
        servers = http.get('servers', {})
        
        server_name = settings.BASE_DOMAIN
        if server_name not in servers:
            https_port = getattr(settings, 'CADDY_HTTPS_PORT', '8443')
            http_port = getattr(settings, 'CADDY_HTTP_PORT', '8080')
            servers[server_name] = {
                'listen': [f':{https_port}', f':{http_port}'],
                'routes': []
            }
        
        server = servers[server_name]
        routes = server.get('routes', [])
        
        new_route = {
            'match': [{'host': [domain]}],
            'handle': [_build_server_config(project, domain)]
        }
        
        existing_hosts = set()
        for route in routes:
            for match in route.get('match', []):
                if 'host' in match:
                    existing_hosts.update(match['host'])
                    for h in match['host']:
                        if h == domain:
                            match['host'] = [domain]
                            route['handle'] = [_build_server_config(project, domain)]
        
        if domain not in existing_hosts:
            routes.append(new_route)
        
        payload = {
            'config': config
        }
        
        r = requests.post(f"{settings.CADDY_ADMIN_API}/load", json=payload, timeout=10)
        if r.status_code == 200:
            logger.info(f"Caddy route updated: {domain} -> localhost:{project.internal_port}")
            return True
        else:
            logger.error(f"Caddy load failed: {r.status_code} {r.text}")
            return False
    except Exception as e:
        logger.error(f"Caddy route update error: {e}")
        return False

def remove_caddy_domain(project, hostname):
    try:
        config = get_caddy_config()
        if not config:
            return False
        
        apps = config.get('apps', {})
        http = apps.get('http', {})
        servers = http.get('servers', {})
        server_name = settings.BASE_DOMAIN
        
        if server_name not in servers:
            return False
        
        routes = servers[server_name].get('routes', [])
        new_routes = []
        for route in routes:
            should_remove = False
            for match in route.get('match', []):
                if 'host' in match and hostname in match['host']:
                    should_remove = True
            if not should_remove:
                new_routes.append(route)
        
        servers[server_name]['routes'] = new_routes
        
        payload = {'config': config}
        r = requests.post(f"{settings.CADDY_ADMIN_API}/load", json=payload, timeout=10)
        return r.status_code == 200
    except Exception as e:
        logger.error(f"Caddy domain removal error: {e}")
        return False
