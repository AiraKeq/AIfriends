from django.db import models
from django.utils.timezone import now, localtime


class SystemPrompt(models.Model):
    """agent 的系统提示词。

    存数据库而不是写死在代码里：改一句人设不用打开编辑器、不用重启服务，
    在 admin 里改完就生效。title 用来区分用途（回复 / 记忆），
    order_number 决定拼接顺序。
    """

    title = models.CharField(max_length=100)
    order_number = models.IntegerField(default=0)
    prompt = models.TextField(max_length=10000)
    create_time = models.DateTimeField(default=now)
    update_time = models.DateTimeField(default=now)

    class Meta:
        ordering = ['order_number']

    def __str__(self):
        return f"{self.title} - {self.order_number} - {self.prompt[:50]}"
