from django.contrib import admin
from web.models.user import UserProfile
from web.models.character import Character
from web.models.friend import Friend, FriendMessage
from web.models.prompt import SystemPrompt


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    raw_id_fields = ('user',)    # 逗号千万别删


@admin.register(Character)
class CharacterAdmin(admin.ModelAdmin):
    raw_id_fields = ('author',)


@admin.register(Friend)
class FriendAdmin(admin.ModelAdmin):
    raw_id_fields = ('me', 'character',)


@admin.register(FriendMessage)
class FriendMessageAdmin(admin.ModelAdmin):
    raw_id_fields = ('friend',)


@admin.register(SystemPrompt)
class SystemPromptAdmin(admin.ModelAdmin):
    list_display = ('title', 'order_number', 'prompt')
    list_filter = ('title',)
    ordering = ('order_number',)
