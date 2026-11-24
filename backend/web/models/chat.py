from django.conf import settings
from django.db import models

from .character import Character


class Conversation(models.Model):
    """一个会话。标题只是给侧边栏显示用的,不参与逻辑。

    ★ character 是可以为空的 ★
      老数据(以及「通用对话」场景)没有角色,所以 null=True。
      聊天时 llm.build_messages 会判断:有角色就注入人设,没有就用默认 system prompt。
    """

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='conversations',
    )
    character = models.ForeignKey(
        Character,
        on_delete=models.CASCADE,
        related_name='conversations',
        null=True,
        blank=True,
    )
    title = models.CharField(max_length=100, default='新对话')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-updated_at']          # 最近聊过的排在最前

    def __str__(self):
        target = self.character.name if self.character else '通用'
        return f'{self.user.username} / {target} / {self.title}'


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
