import web.models.user
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('web', '0002_userprofile'),
    ]

    operations = [
        migrations.AlterField(
            model_name='userprofile',
            name='photo',
            field=models.ImageField(
                default='user/photos/default.png',
                upload_to=web.models.user.photo_path,
            ),
        ),
    ]
