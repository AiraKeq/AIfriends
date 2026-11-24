"""序列化器。

放在一个文件里而不是拆包：现在只有五个，拆开反而要来回跳。
等超过十个再按 auth / chat 分目录不迟。
"""

from django.contrib.auth import get_user_model
from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

from .models import Character, Conversation, Message

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


class CharacterBriefSerializer(serializers.ModelSerializer):
    """角色在会话列表里的「名片」——只要够画一行头像和名字就行。"""

    class Meta:
        model = Character
        fields = ['id', 'name', 'photo', 'background_image']


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
    character = CharacterBriefSerializer(read_only=True)
    # 写入时只收 character 的 id；读的时候用上面那个嵌套对象
    character_id = serializers.PrimaryKeyRelatedField(
        queryset=Character.objects.all(),
        source='character',
        write_only=True,
        required=False,
        allow_null=True,
    )

    class Meta:
        model = Conversation
        fields = [
            'id', 'title', 'character', 'character_id',
            'created_at', 'updated_at', 'message_count', 'last_message',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']

    def get_last_message(self, obj):
        last = obj.messages.last()          # Meta.ordering 是正序，last() 才是最新那条
        if last is None:
            return None
        return {'role': last.role, 'content': last.content[:60]}

    def validate_character_id(self, character):
        """只能绑自己的角色 —— 否则能挂到别人的角色上。"""
        request = self.context.get('request')
        if character is not None and request is not None:
            if character.author.user_id != request.user.id:
                raise serializers.ValidationError('这个角色不属于你')
        return character


class ConversationDetailSerializer(ConversationSerializer):
    """单个会话：把消息一起带上，前端一次请求就能画出整个聊天记录。"""

    messages = MessageSerializer(many=True, read_only=True)

    class Meta(ConversationSerializer.Meta):
        fields = ConversationSerializer.Meta.fields + ['messages']
