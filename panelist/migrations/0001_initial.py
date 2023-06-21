# Generated by Django 2.2.24 on 2021-09-27 10:25

import django.core.validators
from django.db import migrations, models
import django.db.models.deletion
import panelist.models
import phonenumber_field.modelfields
import uuid


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('hq', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='BlankSlot',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=50, unique=True, validators=[django.core.validators.RegexValidator('^[A-Za-z0-9]*$', 'Only numbers and letters are accepted.')])),
                ('description', models.TextField(max_length=500)),
            ],
        ),
        migrations.CreateModel(
            name='BlankSlotValue',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('value', models.CharField(blank=True, default='', max_length=100)),
            ],
        ),
        migrations.CreateModel(
            name='Profile',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('uid', models.UUIDField(default=uuid.uuid4, editable=False, unique=True)),
                ('first_name', models.CharField(blank=True, max_length=256, verbose_name='first name')),
                ('last_name', models.CharField(blank=True, max_length=256, verbose_name='last name')),
                ('email', models.EmailField(blank=True, error_messages={'unique': 'A user with that email address already exists.'}, max_length=254, null=True, unique=True, verbose_name='email address')),
                ('temp_email', models.EmailField(blank=True, max_length=254, null=True, unique=True)),
                ('temp_email_expiry', models.DateTimeField(blank=True, null=True)),
                ('phone', phonenumber_field.modelfields.PhoneNumberField(blank=True, error_messages={'unique': 'A user with that phone number already exists.'}, max_length=128, null=True, region=None, unique=True, verbose_name='phone number')),
                ('is_opt_out', models.BooleanField(default=False)),
                ('language', models.CharField(default='', max_length=10, verbose_name='language')),
                ('address_property_name', models.CharField(blank=True, max_length=50, null=True, verbose_name='name of property')),
                ('address_number', models.CharField(blank=True, max_length=50, null=True, verbose_name='number')),
                ('address', models.CharField(blank=True, max_length=50, null=True, verbose_name='address line 1')),
                ('address2', models.CharField(blank=True, max_length=50, null=True, verbose_name='address line 2')),
                ('city', models.CharField(blank=True, max_length=50, null=True, verbose_name='city')),
                ('county', models.CharField(blank=True, max_length=50, null=True, verbose_name='county')),
                ('postcode', models.CharField(blank=True, max_length=50, null=True, verbose_name='postcode')),
                ('country', models.CharField(choices=[('AT', 'Austria'), ('BE', 'Belgium'), ('BG', 'Bulgaria'), ('CZ', 'Czechia'), ('HR', 'Croatia'), ('CY', 'Cyprus'), ('EE', 'Estonia'), ('FI', 'Finland'), ('FR', 'France'), ('DE', 'Germany'), ('HU', 'Hungary'), ('IS', 'Iceland'), ('IE', 'Ireland'), ('IT', 'Italy'), ('LV', 'Latvia'), ('LT', 'Lithuania'), ('NL', 'The Netherlands'), ('NO', 'Norway'), ('PL', 'Poland'), ('PT', 'Portugal'), ('SK', 'Slovakia'), ('SI', 'Slovenia'), ('SE', 'Sweden'), ('GB', 'United Kingdom'), ('CH', 'Switzerland'), ('AL', 'Albania'), ('DK', 'Denmark'), ('IL', 'Israel'), ('ME', 'Montenegro'), ('RS', 'Serbia'), ('ES', 'Spain'), ('GR', 'Greece'), ('XK', 'Kosovo'), ('LU', 'Luxembourg'), ('RO', 'Romania'), ('RU', 'Russia'), ('TK', 'Turkey'), ('UA', 'Ukraine')], max_length=2, verbose_name='country')),
                ('day_of_birth', models.PositiveIntegerField(validators=[panelist.models.validate_dob_range], verbose_name='day of birth')),
                ('month_of_birth', models.PositiveIntegerField(validators=[panelist.models.validate_mob_range], verbose_name='month of birth')),
                ('year_of_birth', models.PositiveIntegerField(validators=[panelist.models.validate_yob_range], verbose_name='year of birth')),
                ('sex', models.PositiveIntegerField(choices=[(1, 'Male'), (2, 'Female'), (3, 'Other'), (7, 'Refusal'), (8, "Don't know"), (9, 'No answer')], verbose_name='sex')),
                ('internet_use', models.PositiveIntegerField(choices=[(1, 'Never'), (2, 'Only occasionally'), (3, 'A few times a week'), (4, 'Most days'), (5, 'Every day'), (7, 'Refusal'), (8, "Don't know"), (9, 'No answer')], verbose_name='internet use')),
                ('education_years', models.PositiveIntegerField(validators=[panelist.models.validate_eduyrs_range], verbose_name='years of education')),
                ('ess_id', models.PositiveIntegerField(validators=[django.core.validators.MinValueValidator(0), django.core.validators.MaxValueValidator(999999999999)])),
                ('opt_out_date', models.DateTimeField(blank=True, null=True)),
                ('opt_out_reason', models.TextField(blank=True, max_length=1000)),
                ('delete_data', models.BooleanField(default=False)),
                ('out_of_country', models.BooleanField(default=False)),
                ('no_incentive', models.BooleanField(default=False)),
                ('no_letter', models.BooleanField(default=False)),
                ('no_text', models.BooleanField(default=False)),
                ('no_email', models.BooleanField(default=False)),
                ('panel', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='hq.Panel')),
            ],
        ),
    ]