# Generated by Django 3.1 on 2021-07-21 09:41

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('acstracks_app', '0031_auto_20210720_1655'),
    ]

    operations = [
        migrations.AddField(
            model_name='preference',
            name='link_to_detail_page',
            field=models.BooleanField(default=False),
        ),
        migrations.AlterField(
            model_name='preference',
            name='date_end',
            field=models.CharField(blank=True, default='2021-07-21', max_length=255, null=True),
        ),
    ]
