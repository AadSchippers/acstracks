# Generated by Django 3.1 on 2021-04-06 11:12

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('acstracks_app', '0022_auto_20210314_1047'),
    ]

    operations = [
        migrations.AddField(
            model_name='preference',
            name='gpx_contains_cadence',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='preference',
            name='gpx_contains_heartrate',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='preference',
            name='gpx_contains_time',
            field=models.BooleanField(default=False),
        ),
    ]
