# Generated by Django 3.2.23 on 2024-05-30 20:52

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('main', '0017_report_checked_abonents'),
    ]

    operations = [
        migrations.AlterField(
            model_name='report',
            name='checked_abonents',
            field=models.IntegerField(default=None, null=True),
        ),
    ]
