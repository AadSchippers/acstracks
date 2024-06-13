# Generated by Django 4.1.5 on 2024-06-12 11:47

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('acstracks_app', '0051_preference_maximum_heart_rate_and_more'),
    ]

    operations = [
        migrations.AlterField(
            model_name='preference',
            name='date_end',
            field=models.CharField(blank=True, default='2024-06-12', max_length=255, null=True),
        ),
        migrations.AlterField(
            model_name='preference',
            name='maximum_heart_rate',
            field=models.IntegerField(default=175),
        ),
        migrations.AlterField(
            model_name='preference',
            name='resting_heart_rate',
            field=models.IntegerField(default=70),
        ),
    ]