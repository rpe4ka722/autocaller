# Generated by Django 3.2.23 on 2024-04-14 19:18

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('main', '0005_call_call_error'),
    ]

    operations = [
        migrations.AddField(
            model_name='call',
            name='asterisk_no_answer',
            field=models.BooleanField(default=False),
        ),
    ]
