# Generated by Django 3.1 on 2021-04-06 11:29

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('acstracks_app', '0023_auto_20210406_1312'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='preference',
            name='gpx_contains_time',
        ),
    ]