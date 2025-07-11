# Generated by Django 4.2.10 on 2025-06-23 22:40

import django.core.validators
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('clients', '0005_alter_client_address_alter_client_address_number_and_more'),
    ]

    operations = [
        migrations.AlterField(
            model_name='individualclient',
            name='cpf',
            field=models.CharField(blank=True, max_length=14, null=True, validators=[django.core.validators.RegexValidator(message='Digite um CPF válido no formato XXX.XXX.XXX-XX', regex='^\\d{3}\\.\\d{3}\\.\\d{3}-\\d{2}$')], verbose_name='CPF'),
        ),
        migrations.AddConstraint(
            model_name='individualclient',
            constraint=models.UniqueConstraint(condition=models.Q(('cpf__isnull', False)), fields=('cpf',), name='unique_non_null_cpf'),
        ),
    ]
