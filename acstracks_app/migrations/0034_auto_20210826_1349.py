# Generated by Django 3.1 on 2021-08-26 11:49

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('acstracks_app', '0033_auto_20210826_1334'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='track',
            name='maxspeed_latitude',
        ),
        migrations.RemoveField(
            model_name='track',
            name='maxspeed_longitude',
        ),
        migrations.AddField(
            model_name='track',
            name='best20_pointindex',
            field=models.DecimalField(decimal_places=0, default=0, max_digits=6),
        ),
        migrations.AddField(
            model_name='track',
            name='best30_pointindex',
            field=models.DecimalField(decimal_places=0, default=0, max_digits=6),
        ),
        migrations.AddField(
            model_name='track',
            name='best60_pointindex',
            field=models.DecimalField(decimal_places=0, default=0, max_digits=6),
        ),
        migrations.AddField(
            model_name='track',
            name='maxspeed_pointindex',
            field=models.DecimalField(decimal_places=0, default=0, max_digits=6),
        ),
    ]