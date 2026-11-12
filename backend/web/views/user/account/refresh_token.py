from django.conf import settings
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.serializers import TokenRefreshSerializer
from web.views.utils.cookie import clear_legacy_refresh_cookie


class RefreshTokenViews(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]

    def post(self, request):
        refresh_token = request.COOKIES.get('refresh_token')
        if not refresh_token:
            return Response({
                'result': 'refresh token不存在'
            }, status=status.HTTP_401_UNAUTHORIZED)

        # 沿用 SimpleJWT 的轮换和黑名单设置，不仅手动修改 jti。
        serializer = TokenRefreshSerializer(data={'refresh': refresh_token})
        try:
            serializer.is_valid(raise_exception=True)
        except TokenError:
            return Response({
                'result': 'refresh token无效或已过期'
            }, status=status.HTTP_401_UNAUTHORIZED)

        data = serializer.validated_data
        response = Response({
            'result': 'success',
            'access': data['access'],
        })
        response.set_cookie(
            key='refresh_token',
            value=data.get('refresh', refresh_token),
            httponly=True,
            samesite='Lax',
            secure=not settings.DEBUG,
            max_age=int(settings.SIMPLE_JWT['REFRESH_TOKEN_LIFETIME'].total_seconds()),
            path='/api/',
        )
        return clear_legacy_refresh_cookie(response)
