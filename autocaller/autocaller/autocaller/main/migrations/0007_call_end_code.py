# Generated by Django 3.2.23 on 2024-05-28 08:32

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('main', '0006_call_asterisk_no_answer'),
    ]

    operations = [
        migrations.AddField(
            model_name='call',
            name='end_code',
            field=models.IntegerField(default=0),
            preserve_default=False,
        ),
    ]