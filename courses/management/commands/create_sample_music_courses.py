from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from courses.models import Course, Lesson
from django.utils.text import slugify

User = get_user_model()

class Command(BaseCommand):
    help = 'Cria cursos de música de exemplo para o professor de teste'

    def handle(self, *args, **kwargs):
        # Buscar professor de teste
        try:
            professor = User.objects.get(email='professor@example.com')
        except User.DoesNotExist:
            self.stdout.write(self.style.ERROR('Professor de teste não encontrado. Execute o comando create_default_users primeiro.'))
            return

        # Definir os cursos de música de exemplo
        music_courses = [
            {
                'title': 'Teoria Musical para Iniciantes',
                'slug': 'teoria-musical-iniciantes',
                'short_description': 'Aprenda os fundamentos da teoria musical de forma simples e prática',
                'description': '''
                # Teoria Musical para Iniciantes

                Este curso foi desenvolvido para quem quer começar a entender música de forma estruturada, mesmo sem experiência prévia.
                
                Você vai aprender:
                - Notação musical básica
                - Escalas e intervalos fundamentais
                - Acordes e suas estruturas básicas
                
                Ao final do curso, você terá o conhecimento teórico necessário para avançar em qualquer instrumento musical.
                ''',
                'price': 79.90,
                'status': 'PUBLISHED',
                'lessons': [
                    {
                        'title': 'Fundamentos da Notação Musical',
                        'description': 'Nesta aula, você aprenderá sobre as notas musicais, pauta, claves e figuras rítmicas básicas.',
                        'youtube_id': 'dZxfZQYlbOA',
                        'order': 1,
                        'status': 'PUBLISHED'
                    },
                    {
                        'title': 'Escalas Maiores e Menores',
                        'description': 'Vamos explorar as escalas musicais mais importantes: a escala maior natural e as escalas menores (natural, harmônica e melódica).',
                        'youtube_id': 'Vq2xt2D3e3E',
                        'order': 2,
                        'status': 'PUBLISHED'
                    },
                    {
                        'title': 'Acordes Básicos e Progressões',
                        'description': 'Aprenda como são formados os acordes maiores e menores, e como eles se conectam em progressões harmônicas simples.',
                        'youtube_id': '4M5FJYLrRxs',
                        'order': 3,
                        'status': 'PUBLISHED'
                    }
                ]
            },
            {
                'title': 'Piano para Iniciantes',
                'slug': 'piano-iniciantes',
                'short_description': 'Do básico às primeiras músicas completas no piano',
                'description': '''
                # Piano para Iniciantes
                
                Este curso foi projetado para levar você do zero até tocar suas primeiras músicas completas no piano.
                
                ## O que você vai aprender:
                - Postura correta e posicionamento das mãos
                - Leitura básica de partituras para piano
                - Técnicas fundamentais de digitação
                - Suas primeiras músicas completas
                
                Não é necessário ter um piano de cauda! Um teclado com teclas sensíveis ao toque é suficiente para começar.
                ''',
                'price': 89.90,
                'status': 'PUBLISHED',
                'lessons': [
                    {
                        'title': 'Introdução ao Piano e Primeiras Notas',
                        'description': 'Nesta primeira aula, você conhecerá o instrumento, a postura correta e aprenderá a tocar suas primeiras notas.',
                        'youtube_id': 'QBH6IpRkVDs',
                        'order': 1,
                        'status': 'PUBLISHED'
                    },
                    {
                        'title': 'Coordenação entre as Mãos',
                        'description': 'Vamos trabalhar a independência e coordenação entre as mãos, um desafio fundamental para pianistas iniciantes.',
                        'youtube_id': 'X1ky_zsXL6E',
                        'order': 2,
                        'status': 'PUBLISHED'
                    },
                    {
                        'title': 'Sua Primeira Música Completa',
                        'description': 'Chegou a hora de aplicar o que aprendeu! Vamos aprender uma música simples do início ao fim.',
                        'youtube_id': 'Ym9sdY6k61c',
                        'order': 3,
                        'status': 'PUBLISHED'
                    }
                ]
            },
            {
                'title': 'Introdução à Produção Musical',
                'slug': 'introducao-producao-musical',
                'short_description': 'Aprenda o básico para criar suas primeiras músicas em um DAW',
                'description': '''
                # Introdução à Produção Musical
                
                Quer criar suas próprias músicas? Este curso te mostra os primeiros passos na produção musical digital.
                
                ## Conteúdo do curso:
                - Introdução às DAWs (Digital Audio Workstations)
                - Princípios de MIDI e áudio digital
                - Criação de beats, melodias e harmonias básicas
                - Mixagem introdutória
                
                Ao final do curso, você terá produzido sua primeira demo musical completa!
                ''',
                'price': 129.90,
                'status': 'PUBLISHED',
                'lessons': [
                    {
                        'title': 'Introdução às DAWs e Setup Inicial',
                        'description': 'Conheça as principais ferramentas de produção musical e configure seu primeiro projeto.',
                        'youtube_id': 'IJ7RHHIC1RI',
                        'order': 1,
                        'status': 'PUBLISHED'
                    },
                    {
                        'title': 'Criando Ritmos e Melodias com MIDI',
                        'description': 'Aprenda a criar seus primeiros beats e melodias usando controladores MIDI e instrumentos virtuais.',
                        'youtube_id': 'rgCJGjUJj1c',
                        'order': 2,
                        'status': 'PUBLISHED'
                    },
                    {
                        'title': 'Noções Básicas de Mixagem',
                        'description': 'Descubra como equilibrar os elementos da sua música para que ela soe profissional.',
                        'youtube_id': 'D7v6cQKQsa4',
                        'order': 3,
                        'status': 'PUBLISHED'
                    }
                ]
            }
        ]

        # Criar os cursos e suas aulas
        for course_data in music_courses:
            lessons_data = course_data.pop('lessons')
            
            # Verificar se o curso já existe
            existing_course = Course.objects.filter(slug=course_data['slug']).first()
            if existing_course:
                self.stdout.write(self.style.WARNING(f"Curso '{course_data['title']}' já existe. Pulando."))
                continue
                
            # Criar o curso
            course = Course.objects.create(
                professor=professor,
                **course_data
            )
            
            # Criar as aulas do curso
            for lesson_data in lessons_data:
                video_url = f"https://www.youtube.com/watch?v={lesson_data['youtube_id']}" if lesson_data['youtube_id'] else ""
                
                Lesson.objects.create(
                    course=course,
                    title=lesson_data['title'],
                    description=lesson_data['description'],
                    video_url=video_url,
                    youtube_id=lesson_data['youtube_id'],
                    order=lesson_data['order'],
                    status=lesson_data['status']
                )
                
            self.stdout.write(self.style.SUCCESS(f"Curso criado: {course.title} com {len(lessons_data)} aulas"))
            
        self.stdout.write(self.style.SUCCESS("Cursos de música de exemplo criados com sucesso!"))
