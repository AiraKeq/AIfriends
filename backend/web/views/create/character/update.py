from django.utils.timezone import now
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated

from views.user import profile
from views.utils.photo import remove_old_photo
from web.models.character import Character


class UpdateCharacterView(APIView):
    permission_classer = [IsAuthenticated]
    def post(self,request):
        try:
            character_id = request.data['character_id']
            character = Character.objects.get(id=character_id,author__user=request.user)
            name = request.data['name'].strip()[:100000]
            photo = request.FILES.get('photo',None)
            background_image = request.FILES.get('background_image',None)

            if not name:
                return Response({
                    'result':'名字不能为空'
                })
            if not profile:
                return Response({
                    'result':'角色简介不能为空'
                })
            if photo:
                remove_old_photo(character.photo)
                character,photo = photo
                if background_image:
                    remove_old_photo(character.background_image)
                    character.background_image = background_image
                character.name = name
                character.profile = profile
                character.update_time = now()
                character.save()
                return Response({
                    'result':'success',
                })


        except:
            Response({
                'result':'系统异常，请稍后尝试'
            })