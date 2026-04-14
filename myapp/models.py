from django.db import models
from django.contrib.auth.models import AbstractUser

class Users(AbstractUser):
    pass


class Chanels(models.Model):
    user = models.ForeignKey(Users, on_delete=models.CASCADE, related_name='chanels')
    title = models.CharField(max_length=350)
    description = models.TextField()
    avatar = models.ImageField(upload_to='photoes/')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title


class Videos(models.Model):
    chanel = models.ForeignKey(Chanels, on_delete=models.CASCADE, related_name='videos')
    title = models.CharField(max_length=250)
    description = models.TextField()
    video_file = models.FileField(upload_to='videos/')
    views = models.BigIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)


class Comments(models.Model):
    user = models.ForeignKey(Users, on_delete=models.CASCADE, related_name='comments')
    video = models.ForeignKey(Videos, on_delete=models.CASCADE, related_name='comments')
    text = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)


class Likes(models.Model):
    user = models.ForeignKey(Users, on_delete=models.CASCADE, related_name='likes')
    video = models.ForeignKey(Videos, on_delete=models.CASCADE, related_name='likes')
    created_at = models.DateTimeField(auto_now_add=True)


class Subscription(models.Model):
    chanel = models.ForeignKey(Chanels, on_delete=models.CASCADE, related_name='subscription')
    user = models.ForeignKey(Users, on_delete=models.CASCADE, related_name='subscriptions')
    created_at = models.DateTimeField(auto_now_add=True)