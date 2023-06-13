# Generated by Django 4.1.5 on 2023-06-09 14:42

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('acstracks_app', '0048_preference_show_backgroundimage_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='track',
            name='maxcadence_pointindex',
            field=models.DecimalField(decimal_places=0, default=0, max_digits=6),
        ),
        migrations.AddField(
            model_name='track',
            name='maxheartrate_pointindex',
            field=models.DecimalField(decimal_places=0, default=0, max_digits=6),
        ),
        migrations.AlterField(
            model_name='preference',
            name='date_end',
            field=models.CharField(blank=True, default='2023-06-09', max_length=255, null=True),
        ),
    ]