from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('invoices', '0002_alter_companyconfig_regime_tributario_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='companyconfig',
            name='rps_serie',
            field=models.CharField(default='1', help_text='Série do Recibo Provisório de Serviço', max_length=5, verbose_name='série do RPS'),
        ),
        migrations.AddField(
            model_name='companyconfig',
            name='rps_numero_atual',
            field=models.PositiveIntegerField(default=1, help_text='Número sequencial do último RPS emitido', verbose_name='número atual do RPS'),
        ),
        migrations.AddField(
            model_name='companyconfig',
            name='rps_lote',
            field=models.PositiveIntegerField(default=1, help_text='Número do lote de RPS para envio em lote', verbose_name='lote de RPS'),
        ),
        migrations.AddField(
            model_name='invoice',
            name='rps_serie',
            field=models.CharField(blank=True, max_length=5, null=True, verbose_name='série RPS'),
        ),
        migrations.AddField(
            model_name='invoice',
            name='rps_numero',
            field=models.PositiveIntegerField(blank=True, null=True, verbose_name='número RPS'),
        ),
        migrations.AddField(
            model_name='invoice',
            name='rps_lote',
            field=models.PositiveIntegerField(blank=True, null=True, verbose_name='lote RPS'),
        ),
    ]
