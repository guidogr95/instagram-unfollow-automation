import os
from django.conf import settings
from django.http import HttpRequest, HttpResponse, HttpResponsePermanentRedirect, HttpResponseRedirect, JsonResponse
from django.shortcuts import redirect, render
import redis

from instagram_automation.models import FollowerSnapshot, InstagramUser
from .tasks import perform_instagram_login, scrape_followers_and_following

def dashboard(request: HttpRequest) -> HttpResponse:
    main_username = settings.INSTA_USER
    
    if not main_username:
        return render(
            request,
            "instagram_automation/dashboard.html",
            {"error": "INSTA_USER not set." }
        )
        
    profile, _ = InstagramUser.objects.get_or_create(
        username=main_username,
        defaults={"instagram_pk": f"pk_{main_username}"}
    )
    
    redis_client = redis.from_url(settings.CELERY_BROKER_URL)
    is_scanning = redis_client.exists(f"scan_lock_for_{main_username}")
    
    snapshots = FollowerSnapshot.objects.filter(
        profile=profile
    ).order_by("-timestamp")[:2]
    
    unfollowers = []
    not_following_back = []
    
    if len(snapshots) >= 2:
        latest_snapshot = snapshots[0]
        previous_snapshot = snapshots[1]
        latest_followers = set(latest_snapshot.followers.all())
        previous_followers = set(previous_snapshot.followers.all())
        unfollower_users = previous_followers - latest_followers
        unfollowers = [user.username for user in unfollower_users]
        
    if len(snapshots) >= 1:
        latest_snapshot = snapshots[0]
        followers = set(latest_snapshot.followers.all())
        following = set(latest_snapshot.following.all())
        not_following_back_users = following - followers
        not_following_back = [user.username for user in not_following_back_users]
        
    context = {
        "profile": profile,
        "unfollowers": unfollowers,
        "not_following_back": not_following_back,
        "latest_snapshot_time": snapshots[0].timestamp if snapshots else "N/A",
        "is_scanning": is_scanning
    }
    
    return render(
        request,
        "instagram_automation/dashboard.html",
        context
    )
    
    
from typing import Union

def trigger_scan(request: HttpRequest) -> Union[HttpResponseRedirect, HttpResponsePermanentRedirect]:
    username = settings.INSTA_USER
    password = settings.INSTA_PASSWORD
    
    if username and password:
        scrape_followers_and_following.delay(username, password)

    return redirect("dashboard")

def cancel_scan(request):
    
    username = settings.INSTA_USER
    redis_client = redis.from_url(settings.CELERY_BROKER_URL)
    lock_key = f"scan_lock_for_{username}"
    
    is_scanning = redis_client.exists(f"scan_lock_for_{username}")
    
    if is_scanning:
        redis_client.delete(lock_key)
        
    return redirect("dashboard")
    
def trigger_login(request):
    """
    This view triggers the background task.
    It returns immediately.
    """
    
    username = settings.INSTA_USER
    password = settings.INSTA_PASSWORD
    
    if not username or not password:
        return JsonResponse({
            "error": "Instagram credentials are not set in the environment."
        }, status=500)
        
    # .delay() is the magic that sends the job to Celery
    task = perform_instagram_login.delay(username, password)
    
    # Return a response to the user right away
    return JsonResponse({
        "message": "Instagram login process has been started in the background.",
        "task_id": task.id  # You can use this ID to check the task's status later
    })