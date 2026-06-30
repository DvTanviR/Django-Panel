import secrets
import requests
import logging
from django.conf import settings
from django.shortcuts import redirect
from django.urls import reverse
from django.http import JsonResponse, HttpResponse
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_exempt

logger = logging.getLogger(__name__)

@login_required
def github_connect(request):
    if not settings.GITHUB_CLIENT_ID:
        return JsonResponse({'error': 'GitHub App not configured. Set GITHUB_CLIENT_ID in .env'}, status=400)
    
    state = secrets.token_urlsafe(32)
    request.session['github_oauth_state'] = state
    
    params = {
        'client_id': settings.GITHUB_CLIENT_ID,
        'redirect_uri': request.build_absolute_uri(reverse('github_callback')),
        'scope': 'read:user read:org repo',
        'state': state,
    }
    
    url = 'https://github.com/login/oauth/authorize?' + '&'.join(f'{k}={v}' for k, v in params.items())
    return redirect(url)

@login_required
def github_callback(request):
    code = request.GET.get('code')
    state = request.GET.get('state')
    expected_state = request.session.get('github_oauth_state')
    
    if not code or state != expected_state:
        return JsonResponse({'error': 'Invalid state parameter'}, status=400)
    
    if not state:
        return JsonResponse({'error': 'Missing state in session'}, status=400)
    
    token_resp = requests.post('https://github.com/login/oauth/access_token', data={
        'client_id': settings.GITHUB_CLIENT_ID,
        'client_secret': settings.GITHUB_CLIENT_SECRET,
        'code': code,
        'redirect_uri': request.build_absolute_uri(reverse('github_callback')),
    }, headers={'Accept': 'application/json'})
    
    if token_resp.status_code != 200:
        return JsonResponse({'error': 'Failed to get access token'}, status=400)
    
    access_token = token_resp.json().get('access_token')
    if not access_token:
        return JsonResponse({'error': 'No access token in response'}, status=400)
    
    request.session['github_access_token'] = access_token
    return redirect(reverse('github_repos'))

@login_required
def github_repos(request):
    access_token = request.session.get('github_access_token')
    if not access_token:
        return redirect(reverse('github_connect'))
    
    repos = []
    page = 1
    while len(repos) < 100:
        r = requests.get(
            'https://api.github.com/user/repos',
            headers={'Authorization': f'token {access_token}', 'Accept': 'application/vnd.github.v3+json'},
            params={'per_page': 100, 'page': page, 'sort': 'updated'}
        )
        if r.status_code != 200:
            break
        data = r.json()
        if not data:
            break
        repos.extend([{'name': x['full_name'], 'url': x['clone_url'], 'default_branch': x['default_branch']} for x in data])
        if len(data) < 100:
            break
        page += 1
    
    return JsonResponse({'repos': repos})

@login_required
def github_status(request):
    from panel_app.models_github import GitHubAppConfig
    try:
        config = request.user.github_app_config
        return JsonResponse({
            'connected': True,
            'installation_id': config.installation_id,
        })
    except GitHubAppConfig.DoesNotExist:
        token = request.session.get('github_access_token')
        return JsonResponse({
            'connected': bool(token),
            'installation_id': None,
        })

@login_required
def disconnect_github(request):
    request.session.pop('github_access_token', None)
    from panel_app.models_github import GitHubAppConfig
    try:
        request.user.github_app_config.delete()
    except GitHubAppConfig.DoesNotExist:
        pass
    return JsonResponse({'status': 'disconnected'})
