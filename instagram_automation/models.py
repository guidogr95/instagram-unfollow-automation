from django.db import models

class InstagramUser(models.Model):
    username = models.CharField(max_length=255, unique=True, db_index=True)
    full_name = models.CharField(max_length=255, blank=True, null=True)
    instagram_pk = models.CharField(max_length=255, unique=True, db_index=True)

    def __str__(self):
        return self.username

class FollowerSnapshot(models.Model):
    profile = models.ForeignKey(InstagramUser, on_delete=models.CASCADE, related_name='snapshots')
    timestamp = models.DateTimeField(auto_now_add=True, db_index=True)
    
    followers = models.ManyToManyField(InstagramUser, related_name='following_in_snapshots')
    following = models.ManyToManyField(InstagramUser, related_name='followed_by_in_snapshots')

    class Meta:
        ordering = ['-timestamp']

    def __str__(self):
        return f"Snapshot for {self.profile.username} at {self.timestamp.strftime('%Y-%m-%d %H:%M')}"