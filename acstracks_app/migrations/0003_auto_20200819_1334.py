# Generated by Django 3.1 on 2020-08-19 11:34

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('acstracks_app', '0002_auto_20200818_1117'),
    ]

    operations = [
        migrations.AddField(
            model_name='track',
            name='profile',
            field=models.CharField(default='Racefiets', max_length=255),
            preserve_default=False,
        ),
        migrations.AlterField(
            model_name='track',
            name='name',
            field=models.CharField(max_length=255, unique=True),
        ),
    ]
