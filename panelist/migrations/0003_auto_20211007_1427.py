# Generated by Django 2.2.24 on 2021-10-07 14:27

from django.db import migrations, models
import phonenumber_field.modelfields


class Migration(migrations.Migration):

    dependencies = [
        ('panelist', '0002_auto_20210927_1025'),
    ]

    operations = [
        migrations.AddField(
            model_name='profile',
            name='temp_phone',
            field=phonenumber_field.modelfields.PhoneNumberField(blank=True, max_length=128, null=True, region=None, unique=True),
        ),
        migrations.AddField(
            model_name='profile',
            name='temp_phone_expiry',
            field=models.DateTimeField(blank=True, null=True),
        ),
    ]
