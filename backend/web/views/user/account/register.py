from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken

from web.models.user import UserProfile
from django.contrib.auth.models import User


class RegisterView(APIView):
    def post(self, request,):
        try:
            username = request.data['username'].strip()
            password = request.data['password'].strip()
            if not username or not password:
                return Response({
                    'result':'用户名和密码不能为空'
                })
            if User.objects.filter(username=username).exists():
                return Response({
                    'result':'用户名已存在'
                })
            user = User.objects.create_user(username=username, password=password)
            user_profile = UserProfile.objects.create(user=user)
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
                secure=True,
                max_age=86400 * 7,
            )
            return response
        except:
            return Response({
                'result':'系统异常，请稍后重试'
            })