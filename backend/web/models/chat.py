from django.conf import settings
from django.db import models


class Conversation(models.Model):
    """一个会话。标题只是给侧边栏显示用的,不参与逻辑。"""

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='conversations',
    )
    title = models.CharField(max_length=100, default='新对话')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-updated_at']          # 最近聊过的排在最前

    def __str__(self):
        return f'{self.user.username} / {self.title}'


class Message(models.Model):
    """一条消息。role 用两种取值,和各家大模型的对话格式一致。"""

    ROLE_USER = 'user'
    ROLE_ASSISTANT = 'assistant'
    ROLE_CHOICES = [
        (ROLE_USER, '用户'),
        (ROLE_ASSISTANT, 'AI'),
    ]

    conversation = models.ForeignKey(
        Conversation,
        on_delete=models.CASCADE,
        related_name='messages',
    )
    role = models.CharField(max_length=16, choices=ROLE_CHOICES)
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at']           # 按时间正序,就是聊天记录的显示顺序

    def __str__(self):
        return f'{self.role}: {self.content[:20]}'
