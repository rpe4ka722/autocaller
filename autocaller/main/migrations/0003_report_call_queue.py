# Generated by Django 3.2.23 on 2024-04-13 00:54

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('main', '0002_report_department'),
    ]

    operations = [
        migrations.AddField(
            model_name='report',
            name='call_queue',
            field=models.IntegerField(default=0),
        ),
    ]