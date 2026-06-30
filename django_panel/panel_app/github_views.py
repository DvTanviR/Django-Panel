import hmac
import hashlib
import json
from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from panel_app.models import Project, WebhookEvent

@csrf_exempt
@require_POST
def github_webhook(request):
    signature = request.headers.get('X-Hub-Signature-256', '')
    payload = request.body
    
    import os
    webhook_secret = os.getenv('GITHUB_WEBHOOK_SECRET', '')
    
    if webhook_secret:
        expected = 'sha256=' + hmac.new(webhook_secret.encode(), payload, hashlib.sha256).hexdigest()
        if not hmac.compare_digest(expected, signature):
            return HttpResponse('Invalid signature', status=403)
    
    event = request.headers.get('X-GitHub-Event', '')
    
    try:
        data = json.loads(payload)
    except json.JSONDecodeError:
        return HttpResponse('Invalid JSON', status=400)
    
    WebhookEvent.objects.create(
        raw_payload=data,
        result=f'Received {event} event',
    )
    
    if event == 'push':
        repo_url = data.get('repository', {}).get('clone_url', '')
        branch = data.get('ref', '').replace('refs/heads/', '')
        commit_sha = data.get('after', '')
        commit_message = data.get('head_commit', {}).get('message', '') if data.get('head_commit') else ''
        
        try:
            project = Project.objects.get(git_repo_url=repo_url, git_branch=branch)
            from panel_app.tasks import deploy_project
            deploy = project.deployments.create(
                git_commit_sha=commit_sha,
                git_commit_message=commit_message,
                triggered_by='webhook',
                status='queued',
            )
            project.status = 'building'
            project.save()
            deploy_project.delay(project.id, deploy.id)
            we = WebhookEvent.objects.filter(project=project).order_by('-created_at').first()
            if we:
                we.result = f'Triggered deploy for {project.name}'
                we.processed_at = we.created_at
                we.save()
        except Project.DoesNotExist:
            pass
    
    return HttpResponse('OK')
