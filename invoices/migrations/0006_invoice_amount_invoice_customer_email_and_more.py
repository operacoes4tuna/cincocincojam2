# Generated by Django 4.2.10 on 2025-04-05 04:03

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('payments', '0003_singlesale'),
        ('invoices', '0005_merge_0003_add_rps_fields_0004_invoice_external_id'),
    ]

    operations = [
        migrations.AddField(
            model_name='invoice',
            name='amount',
            field=models.DecimalField(blank=True, decimal_places=2, max_digits=10, null=True, verbose_name='valor'),
        ),
        migrations.AddField(
            model_name='invoice',
            name='customer_email',
            field=models.EmailField(blank=True, max_length=255, null=True, verbose_name='email do cliente'),
        ),
        migrations.AddField(
            model_name='invoice',
            name='customer_name',
            field=models.CharField(blank=True, max_length=255, null=True, verbose_name='nome do cliente'),
        ),
        migrations.AddField(
            model_name='invoice',
            name='customer_tax_id',
            field=models.CharField(blank=True, max_length=20, null=True, verbose_name='CPF/CNPJ do cliente'),
        ),
        migrations.AddField(
            model_name='invoice',
            name='description',
            field=models.CharField(blank=True, max_length=255, null=True, verbose_name='descrição'),
        ),
        migrations.AddField(
            model_name='invoice',
            name='singlesale',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='invoices', to='payments.singlesale', verbose_name='venda avulsa'),
        ),
        migrations.AddField(
            model_name='invoice',
            name='type',
            field=models.CharField(choices=[('nfse', 'NFSe'), ('nfe', 'NFe'), ('rps', 'RPS')], default='rps', max_length=10, verbose_name='tipo'),
        ),
        migrations.AlterField(
            model_name='invoice',
            name='transaction',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='invoices', to='payments.paymenttransaction', verbose_name='transação'),
        ),
    ]
