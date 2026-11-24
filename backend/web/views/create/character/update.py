from django.db import transaction
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from web.models.character import Character
from web.views.utils.photo import remove_old_photo


class UpdateCharacterView(APIView):
    """POST /api/create/character/update/

    只允许改自己的角色。字段都可选,但 name / profile 传了就不能是空的。
    图片换了才删旧文件,且在新文件确实落盘之后才删 —— 顺序反了会丢图。
    """

    permission_classes = [IsAuthenticated]

    def post(self, request):
        character_id = request.data.get('character_id')
        name = (request.data.get('name') or '').strip()
        profile = (request.data.get('profile') or '').strip()[:100000]
        photo = request.FILES.get('photo')
        background_image = request.FILES.get('background_image')

        if not character_id:
            return Response({'result': '缺少角色 ID'}, status=status.HTTP_400_BAD_REQUEST)
        if not name:
            return Response({'result': '名字不能为空'}, status=status.HTTP_400_BAD_REQUEST)
        if not profile:
            return Response({'result': '角色简介不能为空'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            # author__user=request.user 是权限边界:别人的角色查不到
            character = Character.objects.get(id=character_id, author__user=request.user)
        except Character.DoesNotExist:
            return Response({'result': '角色不存在'}, status=status.HTTP_404_NOT_FOUND)

        old_photo = character.photo if photo else None
        old_background = character.background_image if background_image else None

        character.name = name
        character.profile = profile
        if photo:
            character.photo = photo
        if background_image:
            character.background_image = background_image

        with transaction.atomic():
            character.save()
            # 事务提交成功后再删旧文件,避免保存失败把原图删没了
            if old_photo:
                transaction.on_commit(lambda: remove_old_photo(old_photo))
            if old_background:
                transaction.on_commit(lambda: remove_old_photo(old_background))

        return Response({
            'result': 'success',
            'character': {
                'id': character.id,
                'name': character.name,
                'profile': character.profile,
                'photo': request.build_absolute_uri(character.photo.url),
                'background_image': request.build_absolute_uri(character.background_image.url),
            },
        })
