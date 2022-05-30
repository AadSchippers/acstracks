# Generated by Django 3.1 on 2021-08-26 11:52

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('acstracks_app', '0035_auto_20210826_1351'),
    ]

    operations = [
        migrations.AddField(
            model_name='track',
            name='best30_end_pointindex',
            field=models.DecimalField(decimal_places=0, default=0, max_digits=6),
        ),
        migrations.AddField(
            model_name='track',
            name='best60_end_pointindex',
            field=models.DecimalField(decimal_places=0, default=0, max_digits=6),
        ),
    ]