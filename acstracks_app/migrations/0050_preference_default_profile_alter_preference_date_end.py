# Generated by Django 4.1.5 on 2024-05-15 12:03

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('acstracks_app', '0049_track_maxcadence_pointindex_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='preference',
            name='default_profile',
            field=models.CharField(blank=True, default=None, max_length=255, null=True),
        ),
        migrations.AlterField(
            model_name='preference',
            name='date_end',
            field=models.CharField(blank=True, default='2024-05-15', max_length=255, null=True),
        ),
    ]