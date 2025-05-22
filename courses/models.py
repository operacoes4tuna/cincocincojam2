from django.db import models
from django.conf import settings
from django.utils.translation import gettext_lazy as _
from django.utils import timezone
from django.utils.text import slugify

class ClassGroup(models.Model):
    """
    Modelo para representar uma turma que agrupa alunos, professor e cursos.
    """
    name = models.CharField(_('nome'), max_length=200)
    description = models.TextField(_('descrição'), blank=True)
    professor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='class_groups',
        verbose_name=_('professor'),
        limit_choices_to={'user_type': 'PROFESSOR'}
    )
    students = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        related_name='enrolled_classes',
        verbose_name=_('alunos'),
        blank=True
    )
    courses = models.ManyToManyField(
        'Course',
        related_name='class_groups',
        verbose_name=_('cursos'),
        blank=True
    )
    created_at = models.DateTimeField(_('data de criação'), auto_now_add=True)
    updated_at = models.DateTimeField(_('última atualização'), auto_now=True)
    
    class Meta:
        verbose_name = _('turma')
        verbose_name_plural = _('turmas')
        ordering = ['-created_at']
        
    def __str__(self):
        return self.name
    
    def get_students_count(self):
        """Retorna o número de alunos na turma."""
        return self.students.count()
        
    def get_courses_count(self):
        """Retorna o número de cursos na turma."""
        return self.courses.count()

class Course(models.Model):
    """
    Modelo para representar um curso oferecido por um professor.
    """
    class Status(models.TextChoices):
        DRAFT = 'DRAFT', _('Rascunho')
        PUBLISHED = 'PUBLISHED', _('Publicado')
        ARCHIVED = 'ARCHIVED', _('Arquivado')
    
    # Relacionamentos
    professor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='courses',
        verbose_name=_('professor'),
        limit_choices_to={'user_type': 'PROFESSOR'}
    )
    
    # Campos básicos
    title = models.CharField(_('título'), max_length=200)
    slug = models.SlugField(_('slug'), max_length=200, unique=True, blank=True)
    short_description = models.CharField(_('descrição curta'), max_length=200, blank=True)
    description = models.TextField(_('descrição'), blank=True)
    price = models.DecimalField(_('preço'), max_digits=10, decimal_places=2, default=0)
    
    # Controle e metadados
    status = models.CharField(
        _('status'),
        max_length=10,
        choices=Status.choices,
        default=Status.DRAFT
    )
    image = models.ImageField(_('imagem'), upload_to='course_images/', blank=True, null=True)
    created_at = models.DateTimeField(_('data de criação'), auto_now_add=True)
    updated_at = models.DateTimeField(_('última atualização'), auto_now=True)
    
    class Meta:
        verbose_name = _('curso')
        verbose_name_plural = _('cursos')
        ordering = ['-created_at']
    
    def __str__(self):
        return self.title
    
    def save(self, *args, **kwargs):
        # Gerar slug automaticamente se não existir
        if not self.slug:
            self.slug = slugify(self.title)
            
            # Garantir que o slug seja único
            original_slug = self.slug
            count = 1
            while Course.objects.filter(slug=self.slug).exists():
                self.slug = f"{original_slug}-{count}"
                count += 1
                
        super().save(*args, **kwargs)
    
    @property
    def is_published(self):
        """Verifica se o curso está publicado."""
        return self.status == self.Status.PUBLISHED
    
    @property
    def is_draft(self):
        """Verifica se o curso está em rascunho."""
        return self.status == self.Status.DRAFT
    
    @property
    def is_archived(self):
        """Verifica se o curso está arquivado."""
        return self.status == self.Status.ARCHIVED
    
    def get_total_lessons(self):
        """Retorna o número total de aulas do curso."""
        return self.lessons.count()
    
    def publish(self):
        """Publica o curso."""
        self.status = self.Status.PUBLISHED
        self.save()
    
    def archive(self):
        """Arquiva o curso."""
        self.status = self.Status.ARCHIVED
        self.save()
    
    def get_enrolled_students_count(self):
        """Retorna o número de alunos matriculados no curso."""
        return self.enrollments.count()


class Lesson(models.Model):
    """
    Modelo para representar uma aula dentro de um curso.
    """
    class Status(models.TextChoices):
        DRAFT = 'DRAFT', _('Rascunho')
        PUBLISHED = 'PUBLISHED', _('Publicado')
    
    # Relacionamentos
    course = models.ForeignKey(
        Course,
        on_delete=models.CASCADE,
        related_name='lessons',
        verbose_name=_('curso')
    )
    
    # Campos básicos
    title = models.CharField(_('título'), max_length=200)
    description = models.TextField(_('descrição'), blank=True)
    video_url = models.URLField(_('URL do vídeo'), blank=True)
    private_video_url = models.URLField(
        _('URL do vídeo privado'), 
        blank=True, 
        help_text=_('URL para vídeos do play.giancorrea.55jam.com.br')
    )
    youtube_id = models.CharField(_('ID do YouTube'), max_length=30, blank=True)
    order = models.PositiveIntegerField(_('ordem'), default=0)
    
    # Controle e metadados
    status = models.CharField(
        _('status'),
        max_length=10,
        choices=Status.choices,
        default=Status.DRAFT
    )
    created_at = models.DateTimeField(_('data de criação'), auto_now_add=True)
    updated_at = models.DateTimeField(_('última atualização'), auto_now=True)
    
    class Meta:
        verbose_name = _('aula')
        verbose_name_plural = _('aulas')
        ordering = ['order', 'created_at']
        unique_together = [['course', 'order']]
    
    def __str__(self):
        return self.title
    
    @property
    def is_published(self):
        """Verifica se a aula está publicada."""
        return self.status == self.Status.PUBLISHED
    
    @property
    def is_draft(self):
        """Verifica se a aula está em rascunho."""
        return self.status == self.Status.DRAFT
    
    def publish(self):
        """Publica a aula."""
        self.status = self.Status.PUBLISHED
        self.save()
    
    def save(self, *args, **kwargs):
        # Se o campo youtube_id estiver vazio, mas o video_url for do youtube,
        # tenta extrair o ID do YouTube da URL
        if not self.youtube_id and 'youtube.com' in self.video_url:
            try:
                from urllib.parse import urlparse, parse_qs
                parsed_url = urlparse(self.video_url)
                if parsed_url.hostname in ('www.youtube.com', 'youtube.com'):
                    if 'v' in parse_qs(parsed_url.query):
                        self.youtube_id = parse_qs(parsed_url.query)['v'][0]
            except:
                pass
                
        super().save(*args, **kwargs)


class LessonRelease(models.Model):
    """
    Modelo para controlar a liberação de aulas por turma.
    """
    class_group = models.ForeignKey(
        ClassGroup,
        on_delete=models.CASCADE,
        related_name='lesson_releases',
        verbose_name=_('turma')
    )
    lesson = models.ForeignKey(
        Lesson,
        on_delete=models.CASCADE,
        related_name='releases',
        verbose_name=_('aula')
    )
    release_date = models.DateTimeField(_('data de liberação'))
    is_released = models.BooleanField(_('liberada'), default=False)
    
    class Meta:
        verbose_name = _('liberação de aula')
        verbose_name_plural = _('liberações de aulas')
        unique_together = ['class_group', 'lesson']
        ordering = ['release_date']
        
    def __str__(self):
        return f"{self.lesson.title} - {self.class_group.name}"
    
    def save(self, *args, **kwargs):
        # Verificar se a data de liberação já passou
        if self.release_date <= timezone.now():
            self.is_released = True
        super().save(*args, **kwargs)


class Enrollment(models.Model):
    """
    Modelo para representar a matrícula de um aluno em um curso.
    """
    class Status(models.TextChoices):
        ACTIVE = 'ACTIVE', _('Ativa')
        COMPLETED = 'COMPLETED', _('Concluída')
        CANCELLED = 'CANCELLED', _('Cancelada')
        PENDING = 'PENDING', _('Pendente')
    
    # Relacionamentos
    student = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='enrollments',
        verbose_name=_('aluno')
    )
    course = models.ForeignKey(
        Course,
        on_delete=models.CASCADE,
        related_name='enrollments',
        verbose_name=_('curso')
    )
    class_group = models.ForeignKey(
        ClassGroup,
        on_delete=models.CASCADE,
        related_name='enrollments',
        verbose_name=_('turma'),
        null=True,
        blank=True
    )
    
    # Campos de controle
    status = models.CharField(
        _('status'),
        max_length=10,
        choices=Status.choices,
        default=Status.PENDING
    )
    progress = models.IntegerField(_('progresso'), default=0, help_text=_('Progresso em porcentagem (0-100)'))
    enrolled_at = models.DateTimeField(_('matriculado em'), auto_now_add=True)
    completed_at = models.DateTimeField(_('concluído em'), null=True, blank=True)
    
    class Meta:
        verbose_name = _('matrícula')
        verbose_name_plural = _('matrículas')
        # Garante que um aluno só possa se matricular uma vez em cada curso por turma
        unique_together = ['student', 'course', 'class_group']
        ordering = ['-enrolled_at']
        
    def __str__(self):
        if self.class_group:
            return f"{self.student.email} - {self.course.title} - {self.class_group.name}"
        return f"{self.student.email} - {self.course.title}"
        
    def save(self, *args, **kwargs):
        # Verificar se é uma nova matrícula (sem ID ainda)
        is_new = self.pk is None
        
        # Salvar a matrícula
        super().save(*args, **kwargs)
        
        # Se for uma nova matrícula com preço > 0 e status não for PENDING, criar automaticamente uma transação de pagamento
        if is_new and self.course.price > 0 and self.status != self.Status.PENDING:
            from payments.models import PaymentTransaction
            
            # Criar uma transação pendente com o valor do curso
            PaymentTransaction.objects.create(
                enrollment=self,
                amount=self.course.price,
                status=PaymentTransaction.Status.PENDING
            )
    
    @property
    def is_active(self):
        """Verifica se a matrícula está ativa."""
        return self.status == self.Status.ACTIVE
    
    @property
    def is_completed(self):
        """Verifica se o curso foi concluído pelo aluno."""
        return self.status == self.Status.COMPLETED
    
    @property
    def is_cancelled(self):
        """Verifica se a matrícula foi cancelada."""
        return self.status == self.Status.CANCELLED
    
    def complete(self):
        """Marca o curso como concluído pelo aluno."""
        self.status = self.Status.COMPLETED
        self.completed_at = timezone.now()
        self.progress = 100
        self.save()
    
    def cancel(self):
        """Cancela a matrícula do aluno no curso."""
        self.status = self.Status.CANCELLED
        self.save()
    
    def update_progress(self, completed_lessons_count):
        """Atualiza o progresso do aluno com base no número de aulas concluídas."""
        total_lessons = self.course.get_total_lessons()
        if total_lessons > 0:
            self.progress = int((completed_lessons_count / total_lessons) * 100)
            self.save()
            
            # Se o progresso for 100%, marca o curso como concluído
            if self.progress == 100:
                self.complete()


class LessonProgress(models.Model):
    """
    Modelo para rastrear o progresso de um aluno em uma aula específica.
    """
    # Relacionamentos
    enrollment = models.ForeignKey(
        Enrollment,
        on_delete=models.CASCADE,
        related_name='lesson_progresses',
        verbose_name=_('matrícula')
    )
    lesson = models.ForeignKey(
        Lesson,
        on_delete=models.CASCADE,
        related_name='student_progresses',
        verbose_name=_('aula')
    )
    
    # Campos de controle
    is_completed = models.BooleanField(_('concluída'), default=False)
    completed_at = models.DateTimeField(_('concluída em'), null=True, blank=True)
    last_accessed_at = models.DateTimeField(_('último acesso em'), auto_now=True)
    
    class Meta:
        verbose_name = _('progresso de aula')
        verbose_name_plural = _('progressos de aulas')
        # Garante que cada aula só tenha um registro de progresso por matrícula
        unique_together = ['enrollment', 'lesson']
        ordering = ['lesson__order']
        
    def __str__(self):
        return f"{self.enrollment.student.email} - {self.lesson.title}"
    
    def complete(self):
        """Marca a aula como concluída pelo aluno."""
        if not self.is_completed:
            self.is_completed = True
            self.completed_at = timezone.now()
            self.save()
            
            # Atualiza o progresso geral do aluno no curso
            completed_lessons = LessonProgress.objects.filter(
                enrollment=self.enrollment,
                is_completed=True
            ).count()
            
            self.enrollment.update_progress(completed_lessons)


class VideoProgress(models.Model):
    """
    Modelo para rastrear o progresso detalhado de visualização de vídeos.
    """
    # Relacionamento
    lesson_progress = models.OneToOneField(
        LessonProgress,
        on_delete=models.CASCADE,
        related_name='video_progress',
        verbose_name=_('progresso da aula')
    )
    
    # Campos de rastreamento
    current_position = models.PositiveIntegerField(
        _('posição atual (segundos)'),
        default=0,
        help_text=_('Posição atual em segundos de onde o aluno parou de assistir')
    )
    video_duration = models.PositiveIntegerField(
        _('duração total (segundos)'),
        default=0,
        help_text=_('Duração total do vídeo em segundos')
    )
    watched_percentage = models.PositiveIntegerField(
        _('porcentagem assistida'),
        default=0,
        help_text=_('Porcentagem do vídeo que foi assistida (0-100)')
    )
    watched_segments = models.JSONField(
        _('segmentos assistidos'),
        null=True,
        blank=True,
        help_text=_('Registra os segmentos do vídeo já assistidos pelo aluno')
    )
    last_updated = models.DateTimeField(_('última atualização'), auto_now=True)
    
    class Meta:
        verbose_name = _('progresso de vídeo')
        verbose_name_plural = _('progressos de vídeos')
    
    def __str__(self):
        return f"Vídeo: {self.lesson_progress.lesson.title} - {self.watched_percentage}% assistido"
    
    def update_progress(self, current_time, watched_segments=None):
        """
        Atualiza o progresso do vídeo com base na posição atual e segmentos assistidos.
        """
        # Atualiza a posição atual
        self.current_position = current_time
        
        # Atualiza os segmentos assistidos, se fornecidos
        if watched_segments is not None:
            self.watched_segments = watched_segments
            
            # Calcula a porcentagem assistida com base nos segmentos
            if self.video_duration > 0 and self.watched_segments:
                total_watched_time = self.get_total_watched_time()
                self.watched_percentage = min(100, int((total_watched_time / self.video_duration) * 100))
        else:
            # Calcula a porcentagem com base apenas na posição atual
            if self.video_duration > 0:
                self.watched_percentage = min(100, int((current_time / self.video_duration) * 100))
        
        self.save()
        
        # Verifica se deve marcar a aula como concluída (se assistiu mais de 90%)
        if self.watched_percentage >= 90 and not self.lesson_progress.is_completed:
            self.lesson_progress.complete()
            
        return self.watched_percentage
    
    def get_total_watched_time(self):
        """
        Calcula o tempo total assistido com base nos segmentos.
        Retorna o tempo total em segundos.
        """
        if not self.watched_segments:
            return self.current_position
            
        total_time = 0
        for start, end in self.watched_segments:
            segment_duration = end - start
            if segment_duration > 0:
                total_time += segment_duration
                
        return total_time
