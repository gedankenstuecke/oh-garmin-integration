# Generated by Django 3.1.7 on 2021-03-28 06:55

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('main', '0003_garminmember_has_health_export_permission'),
    ]

    operations = [
        migrations.CreateModel(
            name='SummariesToProcess',
            fields=[
                ('id', models.IntegerField(auto_created=True, primary_key=True, serialize=False)),
                ('summaries_json', models.TextField()),
                ('garmin_user_id', models.CharField(max_length=255)),
                ('year_month', models.CharField(max_length=255)),
                ('data_type', models.CharField(max_length=255)),
            ],
        ),
    ]
