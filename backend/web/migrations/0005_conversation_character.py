from django.db import migrations, models
import django.db.models.deletion

import web.models.character


class Migration(migrations.Migration):
    """把 Character 接进 Conversation,并修正背景图的上传路径。

    两件事一起做:
      1. Conversation 加 character 外键(可为空:老的通用会话没有角色)
      2. Character.background_image 的 upload_to 从 photo_upload_to 改成
         background_image_upload_to(之前背景图被存进了 character/photos/)
    """

    dependencies = [
        ('web', '0004_character'),
    ]

    operations = [
        migrations.AddField(
            model_name='conversation',
            name='character',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name='conversations',
                to='web.character',
            ),
        ),
        migrations.AlterField(
            model_name='character',
            name='background_image',
            field=models.ImageField(upload_to=web.models.character.background_image_upload_to),
        ),
    ]
