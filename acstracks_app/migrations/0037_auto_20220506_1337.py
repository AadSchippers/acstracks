# Generated by Django 3.1.14 on 2022-05-06 11:37

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('acstracks_app', '0036_auto_20210826_1352'),
    ]

    operations = [
        migrations.AlterField(
            model_name='preference',
            name='date_end',
            field=models.CharField(blank=True, default='2022-05-06', max_length=255, null=True),
        ),
    ]
