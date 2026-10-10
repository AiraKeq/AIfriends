"""序列化器。

放在一个文件里而不是拆包：现在只有四个，拆开反而要来回跳。
等超过十个再按 auth / chat 分目录不迟。
"""

from django.contrib.auth import get_user_model
from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

from .models import Conversation, Message

User = get_user_model()


class UserSerializer(serializers.ModelSerializer):
    """只暴露前端需要的字段。绝不 include 整个模型 —— password 会被带出去。"""

    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'is_staff']
        read_only_fields = fields


class LoginSerializer(TokenObtainPairSerializer):
    """登录 + 刷新共用的序列化器。

    父类返回 {'access': ..., 'refresh': ...}。这里再加上 user，
    前端登录一次就能拿到「我是谁」，不用再发一次 /auth/me/。
    """

    def validate(self, attrs):
        data = super().validate(attrs)
        data['user'] = UserSerializer(self.user).data
        return data


class MessageSerializer(serializers.ModelSerializer):
    class Meta:
        model = Message
        # role 不在可写字段里：客户端不该自称 assistant。
        fields = ['id', 'role', 'content', 'created_at']
        read_only_fields = ['id', 'role', 'created_at']


class ConversationSerializer(serializers.ModelSerializer):
    """会话列表用的轻量版：不带消息正文，只带条数和最后一句预览。"""

    message_count = serializers.IntegerField(read_only=True)
    last_message = serializers.SerializerMethodField()

    class Meta:
        model = Conversation
        fields = ['id', 'title', 'created_at', 'updated_at', 'message_count', 'last_message']
        read_only_fields = ['id', 'created_at', 'updated_at']

    def get_last_message(self, obj):
        last = obj.messages.last()          # Meta.ordering 是正序，last() 才是最新那条
        if last is None:
            return None
        return {'role': last.role, 'content': last.content[:60]}


class ConversationDetailSerializer(ConversationSerializer):
    """单个会话：把消息一起带上，前端一次请求就能画出整个聊天记录。"""

    messages = MessageSerializer(many=True, read_only=True)

    class Meta(ConversationSerializer.Meta):
        fields = ConversationSerializer.Meta.fields + ['messages']
