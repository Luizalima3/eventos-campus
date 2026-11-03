"""Cria contas de teste e dados de demonstração.

Uso: python manage.py shell < seed.py   (a partir da raiz do projeto)
"""
from django.contrib.auth import get_user_model
from django.utils import timezone
from datetime import date, datetime, timedelta

from eventos.models import Sala, Evento, Atividade, InscricaoEvento, InscricaoAtividade

User = get_user_model()

SENHA_PADRAO = 'rad2026#senha'


def criar_usuario(username, email, first_name, **kwargs):
    user, created = User.objects.get_or_create(
        username=username,
        defaults={'email': email, 'first_name': first_name, **kwargs},
    )
    if created:
        user.set_password(SENHA_PADRAO)
        user.save()
    return user


def seed():
    # 1) Superusuário
    admin = criar_usuario('admin', 'admin@ifpb.edu.br', 'Administrador', is_superuser=True, is_staff=True)

    # 2) Organizador 1
    org1 = criar_usuario('org.carlos', 'carlos@ifpb.edu.br', 'Carlos Organizador')

    # 3) Organizador 2
    org2 = criar_usuario('org.beatriz', 'beatriz@ifpb.edu.br', 'Beatriz Organizadora')

    # 4) Participante 1
    part1 = criar_usuario('part.ana', 'ana@ifpb.edu.br', 'Ana Participante')

    # 5) Participante 2
    part2 = criar_usuario('part.bruno', 'bruno@ifpb.edu.br', 'Bruno Participante')

    # Salas
    sala_a, _ = Sala.objects.get_or_create(nome='Auditório Central', bloco='A', defaults={'capacidade': 100})
    sala_b, _ = Sala.objects.get_or_create(nome='Lab 201', bloco='B', defaults={'capacidade': 30})
    sala_pequena, _ = Sala.objects.get_or_create(nome='Sala 12', bloco='C', defaults={'capacidade': 2})

    # Evento 1 — Semana Acadêmica de Informática (organizador 1)
    hoje = date.today()
    ev1, _ = Evento.objects.get_or_create(
        nome='Semana Acadêmica de Informática',
        organizador=org1,
        defaults={
            'descricao': 'Semana com palestras e treinamentos do curso de Informática.',
            'inicio': hoje + timedelta(days=7),
            'fim': hoje + timedelta(days=9),
            'inscricoes_abertas': True,
        },
    )

    # Evento 2 — Jornada Científica (organizador 2), período que se cruza com ev1
    ev2, _ = Evento.objects.get_or_create(
        nome='Jornada Científica do Campus',
        organizador=org2,
        defaults={
            'descricao': 'Apresentações de trabalhos e palestras convidadas.',
            'inicio': hoje + timedelta(days=8),
            'fim': hoje + timedelta(days=11),
            'inscricoes_abertas': True,
        },
    )

    def base_dt(dia, hora):
        return timezone.make_aware(datetime.combine(hoje + timedelta(days=dia), datetime.min.time()).replace(hour=hora))

    # Atividades do evento 1
    at1, _ = Atividade.objects.get_or_create(
        evento=ev1, titulo='Palestra: IA Generativa na Prática',
        defaults={
            'tipo': 'palestra', 'responsavel': 'Profa. Marina Costa',
            'sala': sala_a, 'inicio': base_dt(7, 9), 'fim': base_dt(7, 11),
            'descricao': 'Como usar IA generativa com responsabilidade.',
        },
    )
    at2, _ = Atividade.objects.get_or_create(
        evento=ev1, titulo='Treinamento: Django Básico',
        defaults={
            'tipo': 'treinamento', 'responsavel': 'Prof. Igor Lima',
            'sala': sala_b, 'inicio': base_dt(8, 14), 'fim': base_dt(8, 17),
            'descricao': 'Introdução prática ao framework Django.',
        },
    )
    # Duas atividades no MESMO horário em salas DIFERENTES (evento 1)
    at3, _ = Atividade.objects.get_or_create(
        evento=ev1, titulo='Apresentação: Projetos Integradores',
        defaults={
            'tipo': 'apresentacao', 'responsavel': 'Prof. Igor Lima',
            'sala': sala_pequena, 'inicio': base_dt(8, 9), 'fim': base_dt(8, 11),
            'descricao': 'Apresentação dos projetos dos alunos.',
        },
    )
    at4, _ = Atividade.objects.get_or_create(
        evento=ev1, titulo='Palestra: Carreira em TI',
        defaults={
            'tipo': 'palestra', 'responsavel': 'Profa. Marina Costa',
            'sala': sala_a, 'inicio': base_dt(9, 14), 'fim': base_dt(9, 16),
            'descricao': 'Mercado de trabalho e primeiros passos.',
        },
    )

    # Atividades do evento 2 (mesmo horário de at1, em sala diferente)
    at5, _ = Atividade.objects.get_or_create(
        evento=ev2, titulo='Palestra: Computação Quântica',
        defaults={
            'tipo': 'palestra', 'responsavel': 'Prof. Renato Souza',
            'sala': sala_b, 'inicio': base_dt(7, 9), 'fim': base_dt(7, 11),
            'descricao': 'Introdução à computação quântica.',
        },
    )
    at6, _ = Atividade.objects.get_or_create(
        evento=ev2, titulo='Apresentação: Iniciação Científica',
        defaults={
            'tipo': 'apresentacao', 'responsavel': 'Profa. Helena Dias',
            'sala': sala_pequena, 'inicio': base_dt(9, 9), 'fim': base_dt(9, 11),
            'descricao': 'Resultados das pesquisas de iniciação científica.',
        },
    )

    # Inscrições de exemplo
    ie1, _ = InscricaoEvento.objects.get_or_create(evento=ev1, participante=part1)
    ie2, _ = InscricaoEvento.objects.get_or_create(evento=ev2, participante=part1)
    InscricaoAtividade.objects.get_or_create(inscricao_evento=ie1, atividade=at1)
    InscricaoAtividade.objects.get_or_create(inscricao_evento=ie1, atividade=at2)
    InscricaoAtividade.objects.get_or_create(inscricao_evento=ie2, atividade=at5)

    print('Seed concluído. Senha padrão das contas:', SENHA_PADRAO)
    print('Contas:', [u.username for u in [admin, org1, org2, part1, part2]])


seed()
