# Generated by Django 3.2.23 on 2024-05-31 18:42

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('main', '0025_call_confirmed'),
    ]

    operations = [
        migrations.AlterField(
            model_name='calllist',
            name='sound',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, to='main.soundfile'),
        ),
    ]
