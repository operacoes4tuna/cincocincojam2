# Generated manually on 2025-05-16

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('payments', '0004_add_invoice_fields'),
    ]

    operations = [
        migrations.AddField(
            model_name='singlesale',
            name='customer_address',
            field=models.CharField(
                blank=True, 
                max_length=255, 
                null=True,
                verbose_name='Endereço do Cliente'
            ),
        ),
        migrations.AddField(
            model_name='singlesale',
            name='customer_address_number',
            field=models.CharField(
                blank=True, 
                max_length=20, 
                null=True,
                verbose_name='Número'
            ),
        ),
        migrations.AddField(
            model_name='singlesale',
            name='customer_address_complement',
            field=models.CharField(
                blank=True, 
                max_length=100, 
                null=True,
                verbose_name='Complemento'
            ),
        ),
        migrations.AddField(
            model_name='singlesale',
            name='customer_neighborhood',
            field=models.CharField(
                blank=True, 
                max_length=100, 
                null=True,
                verbose_name='Bairro'
            ),
        ),
        migrations.AddField(
            model_name='singlesale',
            name='customer_city',
            field=models.CharField(
                blank=True, 
                max_length=100, 
                null=True,
                verbose_name='Cidade'
            ),
        ),
        migrations.AddField(
            model_name='singlesale',
            name='customer_state',
            field=models.CharField(
                blank=True, 
                max_length=2, 
                null=True,
                verbose_name='Estado'
            ),
        ),
        migrations.AddField(
            model_name='singlesale',
            name='customer_zipcode',
            field=models.CharField(
                blank=True, 
                max_length=9, 
                null=True,
                verbose_name='CEP'
            ),
        ),
        migrations.AddField(
            model_name='singlesale',
            name='is_payment_confirmed',
            field=models.BooleanField(
                blank=True, 
                default=False, 
                null=True,
                verbose_name='Pagamento Confirmado'
            ),
        ),
    ] 