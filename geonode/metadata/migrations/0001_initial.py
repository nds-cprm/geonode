# Generated by Django 4.2.9 on 2024-11-25 10:55

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ("base", "0092_migrate and_remove_resourcebase_files"),
    ]

    operations = [
        migrations.CreateModel(
            name="SparseField",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("name", models.CharField(max_length=64)),
                ("value", models.CharField(blank=True, max_length=1024, null=True)),
                ("resource", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to="base.resourcebase")),
            ],
            options={
                "ordering": ("resource", "name"),
                "unique_together": {("resource", "name")},
            },
        ),
    ]