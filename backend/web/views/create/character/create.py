from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from web.models.character import Character
from web.models.user import UserProfile


class CreateCharacterView(APIView):
    """POST /api/create/character/create/

    返回新建角色的 id:前端建完要直接跳去编辑页/聊天页,
    没有 id 就只能再去列表里猜哪一个是最新创建的。
    """

    permission_classes = [IsAuthenticated]

    def post(self, request):
        try:
            user_profile = UserProfile.objects.get(user=request.user)
        except UserProfile.DoesNotExist:
            return Response({'result': '用户资料不存在'}, status=status.HTTP_400_BAD_REQUEST)

        name = (request.data.get('name') or '').strip()
        profile = (request.data.get('profile') or '').strip()[:100000]
        photo = request.FILES.get('photo')
        background_image = request.FILES.get('background_image')

        if not name:
            return Response({'result': '名字不能为空'}, status=status.HTTP_400_BAD_REQUEST)
        if not profile:
            return Response({'result': '角色简介不能为空'}, status=status.HTTP_400_BAD_REQUEST)
        if not photo:
            return Response({'result': '头像不能为空'}, status=status.HTTP_400_BAD_REQUEST)
        if not background_image:
            return Response({'result': '聊天背景不能为空'}, status=status.HTTP_400_BAD_REQUEST)

        character = Character.objects.create(
            author=user_profile,
            name=name,
            profile=profile,
            photo=photo,
            background_image=background_image,
        )
        return Response({
            'result': 'success',
            'character_id': character.id,
        }, status=status.HTTP_201_CREATED)
