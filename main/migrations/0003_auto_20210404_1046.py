# Generated by Django 3.1.7 on 2021-04-04 10:46

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('main', '0002_remove_garminmember_earliest_available_data'),
    ]

    operations = [
        migrations.CreateModel(
            name='SummariesToProcess',
            fields=[
                ('id', models.IntegerField(auto_created=True, primary_key=True, serialize=False)),
                ('summaries_json', models.TextField()),
                ('garmin_user_id', models.CharField(max_length=255)),
                ('file_name', models.CharField(max_length=255)),
            ],
        ),
        migrations.AddField(
            model_name='garminmember',
            name='has_health_export_permission',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='garminmember',
            name='was_backfilled',
            field=models.BooleanField(default=False),
        ),
    ]
