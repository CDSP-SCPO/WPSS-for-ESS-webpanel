# Generated by Django 2.2.24 on 2021-09-27 10:25

from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='Panel',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=256)),
                ('incentive_amount', models.CharField(blank=True, help_text='Value and currency.', max_length=256)),
                ('contact_info', models.TextField(blank=True, help_text='Content that will be displayed in the "Contact us" section at the end of the panelist portal help page. If not set, the manager contact information will be displayed by default.', null=True)),
            ],
        ),
    ]
