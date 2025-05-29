import random
from django.core.management.base import BaseCommand
from django.utils.text import slugify
from core.models import User

class Command(BaseCommand):
    help = 'Cria usuários de teste (estudantes e professores) para fins de desenvolvimento'

    def add_arguments(self, parser):
        parser.add_argument(
            '--students',
            type=int,
            default=10,
            help='Número de estudantes a serem criados'
        )
        parser.add_argument(
            '--professors',
            type=int,
            default=3,
            help='Número de professores a serem criados'
        )
        
    def handle(self, *args, **options):
        num_students = options['students']
        num_professors = options['professors']
        
        # Lista de domínios de email fictícios
        domains = ['example.com', 'teste.com.br', 'educacional.org', 'aluno.br', 'professor.edu']
        
        # Lista de nomes fictícios
        first_names = ['Ana', 'Carlos', 'Julia', 'Pedro', 'Marina', 'Fernando', 'Luiza', 'Roberto', 
                      'Camila', 'Diego', 'Sofia', 'Gabriel', 'Beatriz', 'Thiago', 'Larissa']
        last_names = ['Silva', 'Oliveira', 'Santos', 'Costa', 'Pereira', 'Ferreira', 'Rodrigues', 
                     'Almeida', 'Nascimento', 'Lima', 'Araújo', 'Ribeiro', 'Lopes', 'Martins']
        
        students_created = 0
        professors_created = 0
        
        # Criar estudantes
        for i in range(num_students):
            first_name = random.choice(first_names)
            last_name = random.choice(last_names)
            domain = random.choice(domains)
            
            email = f"{slugify(first_name)}.{slugify(last_name)}{random.randint(1, 999)}@{domain}"
            
            if User.objects.filter(email=email).exists():
                continue
                
            User.objects.create_user(
                email=email,
                password='senha123',
                first_name=first_name,
                last_name=last_name,
                user_type=User.Types.STUDENT,
                bio=f"Estudante de música interessado em aprimorar habilidades."
            )
            students_created += 1
            
        # Criar professores
        for i in range(num_professors):
            first_name = random.choice(first_names)
            last_name = random.choice(last_names)
            domain = random.choice(domains)
            
            email = f"prof.{slugify(first_name)}.{slugify(last_name)}{random.randint(1, 999)}@{domain}"
            
            if User.objects.filter(email=email).exists():
                continue
                
            User.objects.create_user(
                email=email,
                password='senha123',
                first_name=first_name,
                last_name=last_name,
                user_type=User.Types.PROFESSOR,
                bio=f"Professor com experiência em ensino de música e performance."
            )
            professors_created += 1
            
        self.stdout.write(self.style.SUCCESS(f'Criados {students_created} estudantes e {professors_created} professores com sucesso!'))
