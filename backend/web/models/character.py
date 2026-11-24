import uuid

from django.db import models
from django.utils.timezone import now, localtime

from web.models.user import UserProfile


def photo_upload_to(instance, filename):
    ext = filename.split('.')[-1]
    filename = f'{uuid.uuid4().hex[:10]}.{ext}'
    return f'character/photos/{instance.author.user_id}_{filename}'


def background_image_upload_to(instance, filename):
    ext = filename.split('.')[-1]
    filename = f'{uuid.uuid4().hex[:10]}.{ext}'
    return f'character/background_image/{instance.author.user_id}_{filename}'


class Character(models.Model):
    """一个可聊天的角色。

    注意:这里存的是「人设文本」,不是模型。聊天时由 llm.py 把 profile
    拼进 system prompt —— 角色不是微调出来的,是提示词塑造的。
    """

    author = models.ForeignKey(UserProfile, on_delete=models.CASCADE)
    name = models.CharField(max_length=50)
    photo = models.ImageField(upload_to=photo_upload_to)
    profile = models.TextField(max_length=100000)
    # 之前这里错写成 photo_upload_to,导致背景图被存进 photos 目录
    background_image = models.ImageField(upload_to=background_image_upload_to)
    create_time = models.DateTimeField(default=now)

    def __str__(self):
        return f"{self.author.user.username} - {self.name} - {localtime(self.create_time).strftime('%Y-%m-%d %H:%M:%S')}"
