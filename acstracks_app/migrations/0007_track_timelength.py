# Generated by Django 3.1 on 2020-08-24 08:54

import datetime
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('acstracks_app', '0006_auto_20200819_1340'),
    ]

    operations = [
        migrations.AddField(
            model_name='track',
            name='timelength',
            field=models.TimeField(default=datetime.datetime(2020, 8, 24, 10, 54, 36, 691620)),
            preserve_default=False,
        ),
    ]
