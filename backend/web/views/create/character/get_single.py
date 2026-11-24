from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from web.models.character import Character


class GetSingleCharacterView(APIView):
    """GET /api/create/character/get_single/?character_id=1

    返回绝对 URL:前端 <img :src> 要能直接加载,
    相对路径在别的域名下会指向错误的主机。
    """

    permission_classes = [IsAuthenticated]

    def get(self, request):
        character_id = request.query_params.get('character_id')
        if not character_id:
            return Response({'result': '缺少角色 ID'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            character = Character.objects.get(id=character_id, author__user=request.user)
        except Character.DoesNotExist:
            return Response({'result': '角色不存在'}, status=status.HTTP_404_NOT_FOUND)

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
