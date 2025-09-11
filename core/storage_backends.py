from storages.backends.s3boto3 import S3Boto3Storage
from django.conf import settings


class MediaStorage(S3Boto3Storage):
    """
    Storage customizado para arquivos de mídia (uploads de usuários).
    """
    bucket_name = settings.AWS_STORAGE_BUCKET_NAME if hasattr(settings, 'AWS_STORAGE_BUCKET_NAME') else None
    location = 'media-courses'
    file_overwrite = False
    default_acl = None  # Bucket não permite ACLs
    querystring_auth = False  # Não usar URLs pré-assinadas
    
    def get_available_name(self, name, max_length=None):
        """
        Retorna um nome de arquivo disponível, adicionando um timestamp se necessário
        para evitar sobrescrever arquivos existentes.
        """
        if self.file_overwrite:
            return name
        return super().get_available_name(name, max_length)


class StaticStorage(S3Boto3Storage):
    """
    Storage customizado para arquivos estáticos (CSS, JS, imagens do sistema).
    """
    bucket_name = settings.AWS_STORAGE_BUCKET_NAME if hasattr(settings, 'AWS_STORAGE_BUCKET_NAME') else None
    location = 'static'
    default_acl = None


class CourseImageStorage(S3Boto3Storage):
    """
    Storage específico para imagens de cursos.
    Organiza as imagens em pastas por ano/mês.
    """
    bucket_name = settings.AWS_STORAGE_BUCKET_NAME if hasattr(settings, 'AWS_STORAGE_BUCKET_NAME') else None
    location = 'media-courses/course_images'
    file_overwrite = False
    default_acl = None  # Bucket não permite ACLs
    querystring_auth = False  # Não usar URLs pré-assinadas
    
    def get_available_name(self, name, max_length=None):
        """
        Garante que o nome do arquivo seja único.
        """
        if self.file_overwrite:
            return name
        return super().get_available_name(name, max_length)