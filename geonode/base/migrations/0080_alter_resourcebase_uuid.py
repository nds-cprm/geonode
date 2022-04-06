# Generated by Django 3.2.12 on 2022-03-28 10:17

from django.db import migrations, models
import uuid


class Migration(migrations.Migration):

    dependencies = [
        ('base', '0079_alter_resourcebase_alternate'),
    ]

    operations = [
        migrations.AlterField(
            model_name='resourcebase',
            name='uuid',
            field=models.CharField(max_length=36, unique=True, default=uuid.uuid4),
        ),
    ]
