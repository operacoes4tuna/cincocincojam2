from django.core.management.base import BaseCommand
from courses.models import Course
from django.conf import settings
import boto3
import os


class Command(BaseCommand):
    help = 'Faz upload das imagens de curso locais para o S3'

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

        courses = Course.objects.exclude(image='').exclude(image__isnull=True)
        self.stdout.write(f"Encontrados {courses.count()} cursos com imagens")

        for course in courses:
            local_path = os.path.join(settings.MEDIA_ROOT, str(course.image))

            if os.path.exists(local_path):
                # Chave no S3
                s3_key = f"media-courses/{course.image}"

                self.stdout.write(f"\nEnviando imagem do curso: {course.title}")
                self.stdout.write(f"  Arquivo local: {local_path}")
                self.stdout.write(f"  Chave S3: {s3_key}")

                try:
                    # Upload para S3
                    with open(local_path, 'rb') as f:
                        s3_client.put_object(
                            Bucket=settings.AWS_STORAGE_BUCKET_NAME,
                            Key=s3_key,
                            Body=f,
                            ContentType=self.get_content_type(str(course.image))
                        )

                    self.stdout.write(self.style.SUCCESS(f"  ✓ Upload concluído"))

                    # Verificar se foi enviado
                    try:
                        s3_client.head_object(
                            Bucket=settings.AWS_STORAGE_BUCKET_NAME,
                            Key=s3_key
                        )
                        self.stdout.write(self.style.SUCCESS(f"  ✓ Verificado no S3"))
                    except:
                        self.stdout.write(self.style.ERROR(f"  ✗ Não foi possível verificar no S3"))

                except Exception as e:
                    self.stdout.write(self.style.ERROR(f"  ✗ Erro: {e}"))
            else:
                self.stdout.write(self.style.WARNING(f"\nArquivo não encontrado localmente: {local_path}"))

    def get_content_type(self, filename):
        """Determina o content-type baseado na extensão do arquivo."""
        ext = filename.lower().split('.')[-1]
        content_types = {
            'jpg': 'image/jpeg',
            'jpeg': 'image/jpeg',
            'png': 'image/png',
            'gif': 'image/gif',
            'webp': 'image/webp',
        }
        return content_types.get(ext, 'application/octet-stream')