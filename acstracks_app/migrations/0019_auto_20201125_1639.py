# Generated by Django 3.1 on 2020-11-25 15:39

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('acstracks_app', '0018_auto_20201125_1124'),
    ]

    operations = [
        migrations.AlterField(
            model_name='track',
            name='avgspeed',
            field=models.DecimalField(decimal_places=2, default=0, max_digits=6),
        ),
        migrations.AlterField(
            model_name='track',
            name='maxspeed',
            field=models.DecimalField(decimal_places=2, default=0, max_digits=6),
        ),
    ]
