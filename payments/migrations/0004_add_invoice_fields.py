# Generated by Django 4.2.10 on 2025-05-16 19:13

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('payments', '0003_singlesale'),
    ]

    operations = [
        migrations.AddField(
            model_name='singlesale',
            name='cfop_code',
            field=models.CharField(
                blank=True, 
                help_text='Código Fiscal de Operações e Prestações',
                max_length=4, 
                null=True, 
                verbose_name='CFOP'
            ),
        ),
        migrations.AddField(
            model_name='singlesale',
            name='customer_phone',
            field=models.CharField(
                blank=True, 
                max_length=20, 
                null=True,
                verbose_name='Telefone'
            ),
        ),
        migrations.AddField(
            model_name='singlesale',
            name='generate_invoice',
            field=models.BooleanField(
                default=False, 
                verbose_name='Gerar Nota Fiscal'
            ),
        ),
        migrations.AddField(
            model_name='singlesale',
            name='invoice_type',
            field=models.CharField(
                blank=True, 
                choices=[
                    ('nfe', 'Nota Fiscal Eletrônica'), 
                    ('nfse', 'Nota Fiscal de Serviço')
                ],
                default='nfse', 
                max_length=10, 
                null=True, 
                verbose_name='Tipo de Nota Fiscal'
            ),
        ),
        migrations.AddField(
            model_name='singlesale',
            name='ncm_code',
            field=models.CharField(
                blank=True, 
                help_text='Código da Nomenclatura Comum do Mercosul',
                max_length=8, 
                null=True, 
                verbose_name='Código NCM'
            ),
        ),
        migrations.AddField(
            model_name='singlesale',
            name='product_code',
            field=models.CharField(
                blank=True, 
                max_length=60, 
                null=True,
                verbose_name='Código do Produto'
            ),
        ),
        migrations.AddField(
            model_name='singlesale',
            name='quantity',
            field=models.DecimalField(
                decimal_places=2, 
                default=1, 
                max_digits=10,
                verbose_name='Quantidade'
            ),
        ),
        migrations.AddField(
            model_name='singlesale',
            name='unit_value',
            field=models.DecimalField(
                blank=True, 
                decimal_places=2, 
                max_digits=10,
                null=True, 
                verbose_name='Valor Unitário'
            ),
        ),
    ]
