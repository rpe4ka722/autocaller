# Generated by Django 3.2.23 on 2024-05-28 13:02

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('main', '0014_call_call_timeout'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='call',
            name='call_timeout',
        ),
    ]
