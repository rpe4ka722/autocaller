# Generated by Django 3.2.23 on 2024-05-30 22:02

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('main', '0021_alter_report_checked_abonents'),
    ]

    operations = [
        migrations.AddField(
            model_name='call',
            name='abonent',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, to='main.abonent'),
        ),
    ]
