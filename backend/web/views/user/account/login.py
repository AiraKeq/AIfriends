import logging

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken
from django.conf import settings

from web.models.user import UserProfile
from web.views.utils.cookie import clear_legacy_refresh_cookie

logger = logging.getLogger(__name__)


class LoginViews(APIView):
    def post(self, request, *args, **kwargs):
        username = request.data.get("username")
        try:
            username = username.strip()
            password = request.data.get("password").strip()
            if not username or not password:
                return Response({
                    'result': '用户名和密码不能为空'
                })
            from django.contrib.auth import authenticate
            user = authenticate(username=username, password=password)
            if user:
                user_profile = UserProfile.objects.get(user=user)
                refresh = RefreshToken.for_user(user)
                response = Response({
                    'result': 'success',
                    'access': str(refresh.access_token),
                    'user_id': user.id,
                    'username': user.username,
                    'photo': request.build_absolute_uri(user_profile.photo.url),
                    'profile': user_profile.profile,
                })
                response.set_cookie(
                    key='refresh_token',
                    value=str(refresh),
                    httponly=True,
                    samesite='Lax',
                    secure=not settings.DEBUG,
                    max_age=86400 * 7,
                    path='/api/',
                )
                return clear_legacy_refresh_cookie(response)
            return Response({
                'result': '用户名或密码错误',
            })
        except Exception:
            # 这里以前是裸 except，会把「数据库只读」「表缺失」这类致命错误
            # 悄悄吞成一句「系统异常，请稍后重试」，排查时无从下手。
            # 现在把完整 traceback 打进日志，对外返回仍是同一句兜底文案。
            logger.exception('login failed (username=%r)', username)
            return Response({
                'result': '系统异常，请稍后重试'
            })
