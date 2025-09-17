from django.core.management.base import BaseCommand
from courses.models import LessonAttachment
from django.conf import settings
import boto3
import os


class Command(BaseCommand):
    help = 'Faz upload dos anexos locais para o S3'

    def handle(self, *args, **kwargs):
        if not settings.USE_S3:
            self.stdout.write(self.style.ERROR("S3 não está configurado"))
            return

        s3_client = boto3.client(
            's3',
            aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
            region_name=settings.AWS_S3_REGION_NAME
        )

        attachments = LessonAttachment.objects.filter(file__isnull=False)
        self.stdout.write(f"Encontrados {attachments.count()} anexos com arquivos")

        for att in attachments:
            local_path = os.path.join(settings.MEDIA_ROOT, att.file.name)

            if os.path.exists(local_path):
                # Chave no S3
                s3_key = f"media-courses/{att.file.name}"

                self.stdout.write(f"\nEnviando: {att.title}")
                self.stdout.write(f"  Arquivo local: {local_path}")
                self.stdout.write(f"  Chave S3: {s3_key}")

                try:
                    # Upload para S3
                    with open(local_path, 'rb') as f:
                        s3_client.put_object(
                            Bucket=settings.AWS_STORAGE_BUCKET_NAME,
                            Key=s3_key,
                            Body=f,
                            ContentType=self.get_content_type(att.file.name)
                        )

                    self.stdout.write(self.style.SUCCESS(f"  ✓ Upload concluído"))

                except Exception as e:
                    self.stdout.write(self.style.ERROR(f"  ✗ Erro: {e}"))
            else:
                self.stdout.write(self.style.WARNING(f"\nArquivo não encontrado localmente: {local_path}"))

    def get_content_type(self, filename):
        """Determina o content-type baseado na extensão do arquivo."""
        ext = filename.lower().split('.')[-1]
        content_types = {
            'pdf': 'application/pdf',
            'doc': 'application/msword',
            'docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
            'jpg': 'image/jpeg',
            'jpeg': 'image/jpeg',
            'png': 'image/png',
            'gif': 'image/gif',
            'mp3': 'audio/mpeg',
            'wav': 'audio/wav',
            'ogg': 'audio/ogg',
        }
        return content_types.get(ext, 'application/octet-stream')