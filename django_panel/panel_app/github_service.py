import requests
import logging
from django.conf import settings

logger = logging.getLogger(__name__)

class GitHubService:
    @staticmethod
    def register_webhook(repo_url, project_id, webhook_url, secret, user_access_token=None):
        parts = repo_url.rstrip('/').replace('.git', '').split('/')
        if len(parts) < 2:
            return False, "Invalid repo URL"
        owner, repo = parts[-2], parts[-1]
        
        token = user_access_token or settings.GITHUB_APP_PRIVATE_KEY
        if not token:
            return False, "No GitHub token available"
        
        try:
            headers = {
                'Authorization': f'token {token}',
                'Accept': 'application/vnd.github.v3+json',
            }
            
            payload = {
                'name': 'web',
                'active': True,
                'events': ['push'],
                'config': {
                    'url': webhook_url,
                    'content_type': 'json',
                    'secret': secret,
                }
            }
            
            r = requests.post(
                f'https://api.github.com/repos/{owner}/{repo}/hooks',
                headers=headers,
                json=payload,
                timeout=10
            )
            
            if r.status_code == 201:
                return True, r.json().get('id')
            else:
                return False, r.text
        except Exception as e:
            logger.error(f"Webhook registration error: {e}")
            return False, str(e)
    
    @staticmethod
    def remove_webhook(repo_url, webhook_id, user_access_token=None):
        try:
            parts = repo_url.rstrip('/').replace('.git', '').split('/')
            if len(parts) < 2:
                return False
            owner, repo = parts[-2], parts[-1]
            
            token = user_access_token or settings.GITHUB_APP_PRIVATE_KEY
            if not token:
                return False
            
            headers = {
                'Authorization': f'token {token}',
                'Accept': 'application/vnd.github.v3+json',
            }
            
            r = requests.delete(
                f'https://api.github.com/repos/{owner}/{repo}/hooks/{webhook_id}',
                headers=headers,
                timeout=10
            )
            return r.status_code == 204
        except Exception as e:
            logger.error(f"Webhook removal error: {e}")
            return False
