# Generated by Django 3.1.7 on 2021-04-20 07:29

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('openhumans', '0002_openhumansmember_oh_deauth'),
        ('main', '0003_auto_20210404_1046'),
    ]

    operations = [
        migrations.CreateModel(
            name='RetrievedData',
            fields=[
                ('id', models.IntegerField(auto_created=True, primary_key=True, serialize=False)),
                ('data_type', models.CharField(max_length=255)),
                ('min_date', models.DateTimeField()),
                ('max_date', models.DateTimeField()),
                ('member', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='openhumans.openhumansmember')),
            ],
        ),
        migrations.AddIndex(
            model_name='retrieveddata',
            index=models.Index(fields=['member', 'data_type'], name='main_retrie_member__6b7f84_idx'),
        ),
    ]