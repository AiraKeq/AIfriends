from django.contrib.auth.models import User
from django.utils.timezone import now
from django.db import transaction
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

from web.views.utils.photo import remove_old_photo
from web.models.user import UserProfile

class UpdateProfileView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        try:
            user = request.user
            user_profile = UserProfile.objects.get(user=user)
            username = (request.data.get('username') or '').strip()
            profile = (request.data.get('profile') or '').strip()[:500]
            photo = request.FILES.get('photo')

            if not username:
                return Response({'result': '用户名不能为空'})
            if not profile:
                return Response({'result': '简介不能为空'})
            if username != user.username and User.objects.filter(username=username).exists():
                return Response({'result': '用户名已存在'})

            old_photo = user_profile.photo if photo else None
            with transaction.atomic():
                if photo:
                    user_profile.photo = photo
                user_profile.profile = profile
                user_profile.update_time = now()
                user_profile.save()
                user.username = username
                user.save()

                # 新文件及资料保存成功后，才删除旧上传文件。
                if old_photo:
                    transaction.on_commit(lambda: remove_old_photo(old_photo))

            return Response({
                'result': 'success',
                'user_id': user.id,
                'username': user.username,
                'profile': user_profile.profile,
                'photo': request.build_absolute_uri(user_profile.photo.url),
            })
        except Exception:
            return Response({'result': '系统异常，请稍后重试'})