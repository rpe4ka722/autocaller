# Generated by Django 3.2.23 on 2024-04-08 21:07

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('main', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='report',
            name='department',
            field=models.CharField(max_length=4, null=True),
        ),
    ]
