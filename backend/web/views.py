"""视图：认证 + 聊天 API。

认证部分用 simplejwt 的内置视图,各自覆写一两个方法:
- TokenObtainPairView  -> 登录(走 web.serializers.LoginSerializer,响应多带 user)
- TokenRefreshView     -> 无感刷新的服务端一半(旋转 + 拉黑由 SIMPLE_JWT 配置决定)
- APIView              -> 登出(把 refresh 拉黑,服务端真正失效)
"""

from pathlib import Path

from django.conf import settings
from django.db.models import Count
from django.http import HttpResponse
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import AuthenticationFailed
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

from . import llm
from .models import Conversation, Message
from .serializers import (
    ConversationDetailSerializer,
    ConversationSerializer,
    LoginSerializer,
    MessageSerializer,
    UserSerializer,
)

TOKEN_COOKIE = 'refresh_token'

# refresh token 过期时间,和 SIMPLE_JWT['REFRESH_TOKEN_LIFETIME'] 保持一致
REFRESH_MAX_AGE = 7 * 24 * 3600


def _set_refresh_cookie(response, refresh_token):
    """把 refresh token 放进 httpOnly cookie。

    为什么不全放 localStorage:
      access 放 localStorage 是常见做法(它只活 30 分钟);
      refresh 一旦被 JS 读走,就等于把「7 天的登录态」交出去了。
      httpOnly 的 cookie JS 读不到,XSS 也偷不走。
    """
    cookie_kwargs = {
        'httponly': True,
        'samesite': 'Lax',
        'secure': False,          # 上线(HTTPS)时改成 True
        'path': '/api/auth/',
    }
    if refresh_token is None:
        response.delete_cookie(TOKEN_COOKIE)
    else:
        response.set_cookie(TOKEN_COOKIE, refresh_token, max_age=REFRESH_MAX_AGE, **cookie_kwargs)
    return response


class LoginView(TokenObtainPairView):
    """POST /api/auth/login/   {username, password} -> {access, refresh, user}"""

    def post(self, request, *args, **kwargs):
        # ⚠ 传 data=request.data 是必须的:不写的话 serializer 收到 None,
        #   直接报 "may not be null"。
        serializer = LoginSerializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        response = Response(data, status=status.HTTP_200_OK)
        return _set_refresh_cookie(response, data.get('refresh'))


class RefreshView(TokenRefreshView):
    """POST /api/auth/refresh/   {refresh} -> 新的一对 token

    这就是「无感刷新」的服务端那一半,客户端那半在
    frontend/src/api/http.js 的响应拦截器里。

    ★ TokenError 必须自己转成 401 ★
      refresh 过期、被拉黑、格式不对时,simplejwt 抛的是 TokenError。
      父类 TokenRefreshView 内部会把它转成 401,但这里覆写了 post()、
      走的是自己的流程,所以必须自己 catch ——
      漏了就会炸成 500 并吐一整页 HTML 堆栈
      (2026-10-09 实测:状态 500、响应体 121742 字节)。
    """

    def post(self, request, *args, **kwargs):
        # refresh 可能来自 body,也可能来自 httpOnly cookie
        data = request.data.copy() if hasattr(request.data, 'copy') else dict(request.data)
        if not data.get('refresh'):
            cookie_token = request.COOKIES.get(TOKEN_COOKIE)
            if cookie_token:
                data['refresh'] = cookie_token

        serializer = self.get_serializer(data=data)
        try:
            serializer.is_valid(raise_exception=True)
        except TokenError:
            # 前端的响应拦截器看到 401 才会去走"重新登录"的分支,
            # 给 500 它只会当成服务器故障。
            raise AuthenticationFailed('刷新令牌无效或已过期，请重新登录')

        payload = dict(serializer.validated_data)
        if not payload.get('refresh'):
            payload['refresh'] = data['refresh']

        response = Response(payload, status=status.HTTP_200_OK)
        return _set_refresh_cookie(response, payload.get('refresh'))


class LogoutView(APIView):
    """POST /api/auth/logout/   {refresh} -> 204

    登出不只是前端删掉 token:blacklist() 才是让那串 refresh
    在服务端真正失效的动作(依赖 token_blacklist 应用)。
    """

    permission_classes = [IsAuthenticated]

    def post(self, request):
        raw = request.data.get('refresh') or request.COOKIES.get(TOKEN_COOKIE)
        if raw:
            try:
                RefreshToken(raw).blacklist()
            except TokenError:
                # 已过期/已拉黑/格式不对都不该让登出失败 —— 前端无论如何都会清空本地状态
                pass

        response = Response(status=status.HTTP_204_NO_CONTENT)
        return _set_refresh_cookie(response, None)


class MeView(APIView):
    """GET /api/auth/me/  -> 当前登录用户。"""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response(UserSerializer(request.user).data)


class ChatViewSet(viewsets.ModelViewSet):
    """会话 CRUD + 发消息。

    路由(DefaultRouter 生成):
        GET    /api/conversations/                列表
        POST   /api/conversations/                新建
        GET    /api/conversations/{id}/           详情(含全部消息)
        PATCH  /api/conversations/{id}/           改标题
        DELETE /api/conversations/{id}/           删除
        POST   /api/conversations/{id}/messages/  发一条消息,拿回 AI 回复
    """

    permission_classes = [IsAuthenticated]
    serializer_class = ConversationSerializer

    def get_queryset(self):
        # ★ 数据隔离的关键一行:只返回当前用户的会话。
        #   少了它,任何登录用户都能读到别人的聊天记录(水平越权)。
        return (
            Conversation.objects
            .filter(user=self.request.user)
            .annotate(message_count=Count('messages'))
        )

    def get_serializer_class(self):
        # 列表和详情用不同的序列化器:列表不带消息正文,省流量
        if self.action in ('retrieve', 'create'):
            return ConversationDetailSerializer
        return ConversationSerializer

    def perform_create(self, serializer):
        # user 由服务端填,不接受客户端传 —— 否则能伪造别人的会话
        serializer.save(user=self.request.user)

    @action(detail=True, methods=['post'], url_path='messages')
    def messages(self, request, pk=None):
        """POST /api/conversations/{id}/messages/  {content: "..."}"""
        conversation = self.get_object()          # get_queryset 已保证是自己的
        content = (request.data.get('content') or '').strip()
        if not content:
            return Response({'detail': 'content 不能为空'}, status=status.HTTP_400_BAD_REQUEST)

        user_message = Message.objects.create(
            conversation=conversation,
            role=Message.ROLE_USER,
            content=content,
        )

        # 首条消息顺便当标题,省得列表里全是「新对话」
        if conversation.title == '新对话':
            conversation.title = content[:20]
            conversation.save(update_fields=['title'])

        reply_text = generate_reply(conversation)
        assistant_message = Message.objects.create(
            conversation=conversation,
            role=Message.ROLE_ASSISTANT,
            content=reply_text,
        )

        conversation.save(update_fields=['updated_at'])   # 让会话排到列表最前

        return Response(
            {
                'user_message': MessageSerializer(user_message).data,
                'assistant_message': MessageSerializer(assistant_message).data,
            },
            status=status.HTTP_201_CREATED,
        )


def generate_reply(conversation):
    """调 DeepSeek 拿回复。

    真正的调用逻辑在 web/llm.py，这里只负责「把模型侧的异常转成一句人话」。

    为什么要 try：模型会超时、会欠费、会限流。这些都不是 bug，
    是网络那头的常态。让它们炸成 500 的话，前端只会看到「服务器错误」，
    而且用户刚打的那句话在界面上会显得像没发出去。
    现在改成：把这句话作为 assistant 消息存下来，前端照常显示，
    用户一眼就知道发生了什么。
    """
    try:
        return llm.chat(conversation)
    except llm.LLMUnavailable as exc:
        return f'（模型暂时不可用：{exc}）'
    except Exception as exc:                      # 兜底，绝不把 500 丢给用户
        return f'（调用模型时出错：{exc}）'


# ─────────────────────────────────────────────────────────────────────────────
# 页面入口（不是 API）
#
# 返回 Vite 打包出来的那份 HTML，而不是走 Django 模板：
# 每次 build 都会产生新的哈希文件名（assets/index-<hash>.js），
# 模板里手写就钉死了一个哈希，下次 build 立刻 404。
# ─────────────────────────────────────────────────────────────────────────────

def index(request):
    built = Path(settings.BASE_DIR) / 'static' / 'frontend' / 'index.html'
    if not built.exists():
        return HttpResponse(
            'Frontend not built yet -- run "npm run build" in F:\\AIFriends\\frontend.',
            status=503,
        )
    return HttpResponse(built.read_text(encoding='utf-8'))
