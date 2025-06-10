# Generated manually for adding BoletoBancario model

from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone


class Migration(migrations.Migration):

    dependencies = [
        ('invoices', '0010_alter_companyconfig_city_service_code'),
    ]

    operations = [
        migrations.CreateModel(
            name='BoletoBancario',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('numero_documento', models.CharField(blank=True, max_length=50, null=True, verbose_name='número do documento')),
                ('nosso_numero', models.CharField(blank=True, max_length=50, null=True, verbose_name='nosso número')),
                ('codigo_barras', models.CharField(blank=True, max_length=44, null=True, verbose_name='código de barras')),
                ('linha_digitavel', models.CharField(blank=True, max_length=47, null=True, verbose_name='linha digitável')),
                ('valor_documento', models.DecimalField(decimal_places=2, max_digits=10, verbose_name='valor do documento')),
                ('valor_juros', models.DecimalField(decimal_places=2, default=0.0, max_digits=10, verbose_name='valor de juros')),
                ('valor_multa', models.DecimalField(decimal_places=2, default=0.0, max_digits=10, verbose_name='valor de multa')),
                ('data_emissao', models.DateField(default=django.utils.timezone.now, verbose_name='data de emissão')),
                ('data_vencimento', models.DateField(verbose_name='data de vencimento')),
                ('data_pagamento', models.DateField(blank=True, null=True, verbose_name='data de pagamento')),
                ('status', models.CharField(choices=[('draft', 'Rascunho'), ('generated', 'Gerado'), ('sent', 'Enviado'), ('paid', 'Pago'), ('expired', 'Vencido'), ('cancelled', 'Cancelado'), ('error', 'Erro')], default='draft', max_length=20, verbose_name='status')),
                ('url_pdf', models.URLField(blank=True, null=True, verbose_name='URL do PDF')),
                ('arquivo_pdf', models.FileField(blank=True, null=True, upload_to='boletos/%Y/%m/', verbose_name='arquivo PDF')),
                ('external_id', models.CharField(blank=True, max_length=100, null=True, verbose_name='ID externo')),
                ('external_data', models.JSONField(blank=True, null=True, verbose_name='dados externos')),
                ('banco_codigo', models.CharField(blank=True, help_text='Código FEBRABAN do banco', max_length=3, null=True, verbose_name='código do banco')),
                ('agencia', models.CharField(blank=True, max_length=10, null=True, verbose_name='agência')),
                ('conta', models.CharField(blank=True, max_length=20, null=True, verbose_name='conta')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='criado em')),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='atualizado em')),
                ('metadata', models.JSONField(blank=True, default=dict, verbose_name='metadados')),
                ('invoice', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='boleto', to='invoices.invoice', verbose_name='nota fiscal')),
            ],
            options={
                'verbose_name': 'boleto bancário',
                'verbose_name_plural': 'boletos bancários',
                'ordering': ['-created_at'],
            },
        ),
    ] 