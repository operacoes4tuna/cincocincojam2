from django.core.management.base import BaseCommand
from courses.models import LessonAttachment
from django.conf import settings
import boto3
from botocore.exceptions import ClientError


class Command(BaseCommand):
    help = 'Testa URLs do S3 e gera URLs pré-assinadas'

    def handle(self, *args, **kwargs):
        self.stdout.write("Verificando configurações do S3...")
        self.stdout.write(f"USE_S3: {settings.USE_S3}")
        self.stdout.write(f"AWS_QUERYSTRING_AUTH: {settings.AWS_QUERYSTRING_AUTH}")
        self.stdout.write(f"BUCKET: {settings.AWS_STORAGE_BUCKET_NAME}")

        # Pegar um anexo de teste
        attachment = LessonAttachment.objects.filter(file__isnull=False).first()

        if attachment:
            self.stdout.write(f"\nTestando anexo: {attachment.title}")
            self.stdout.write(f"Arquivo: {attachment.file.name}")

            # URL padrão do Django
            django_url = attachment.file.url
            self.stdout.write(f"\nURL do Django: {django_url}")

            # Gerar URL pré-assinada diretamente com boto3
            try:
                s3_client = boto3.client(
                    's3',
                    aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
                    aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
                    region_name=settings.AWS_S3_REGION_NAME
                )

                # Construir a chave do objeto
                key = f"media-courses/{attachment.file.name}"
                self.stdout.write(f"\nChave S3: {key}")

                # Gerar URL pré-assinada
                presigned_url = s3_client.generate_presigned_url(
                    'get_object',
                    Params={
                        'Bucket': settings.AWS_STORAGE_BUCKET_NAME,
                        'Key': key
                    },
                    ExpiresIn=3600
                )

                self.stdout.write(self.style.SUCCESS(f"\nURL pré-assinada gerada com sucesso:"))
                self.stdout.write(presigned_url)

            except ClientError as e:
                self.stdout.write(self.style.ERROR(f"\nErro ao gerar URL: {e}"))
        else:
            self.stdout.write(self.style.WARNING("Nenhum anexo com arquivo encontrado"))