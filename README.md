# Sistema de Inscrições para Eventos do Campus

Projeto Django desenvolvido para a atividade **Ponto Extra II** da disciplina de RAD (IFPB).

Um evento reúne várias atividades (palestras, treinamentos, apresentações). Cada atividade acontece em uma sala, em um horário, e a capacidade da sala limita o número de inscritos.

## Integrantes

- **Luiz Antonio Lima** (e demais integrantes, editar aqui)

## Como rodar

```bash
python -m venv .venv
.venv\Scripts\activate        # Windows
pip install -r requirements.txt
python manage.py runserver
```

O banco `db.sqlite3` já vem com os dados de teste cadastrados — basta rodar o servidor e acessar `http://127.0.0.1:8000/`.

## Contas de teste

A senha de todas as contas é: **rad2026#senha**

| # | Usuário | Papel | Para que serve |
|---|---------|-------|----------------|
| 1 | `admin` | Superusuário | Cadastrar salas pelo Admin (`/admin/`) |
| 2 | `org.carlos` | Organizador | Criar eventos e atividades |
| 3 | `org.beatriz` | Organizador | Confirmar que NÃO altera o que é da conta 2 |
| 4 | `part.ana` | Participante | Inscrever-se em eventos/atividades |
| 5 | `part.bruno` | Participante | Ocupar a última vaga de uma sala |

> Atenção: o superusuário `admin` passa em qualquer verificação de permissão. Use as contas 2–5 para testar as regras de verdade.

## Dados de teste cadastrados

### Salas (cadastradas pelo Admin)

| Sala | Bloco | Capacidade |
|------|-------|-----------|
| Auditório Central | A | 100 |
| Lab 201 | B | 30 |
| **Sala 12** | C | **2** (usada para testar o limite de vagas) |

### Eventos (períodos que se cruzam)

| Evento | Organizador | Período |
|--------|-------------|---------|
| Semana Acadêmica de Informática | org.carlos | +7 a +9 dias a partir de hoje |
| Jornada Científica do Campus | org.beatriz | +8 a +11 dias (cruza com o anterior) |

### Atividades

| Atividade | Evento | Sala | Horário (relativo) |
|-----------|--------|------|--------------------|
| Palestra: IA Generativa na Prática | Semana | Auditório Central | dia +7, 9h–11h |
| **Palestra: Computação Quântica** | Jornada | Lab 201 | **dia +7, 9h–11h (sobrepõe com a anterior, sala diferente — testa RN2/RN3)** |
| Treinamento: Django Básico | Semana | Lab 201 | dia +8, 14h–17h |
| Apresentação: Projetos Integradores | Semana | **Sala 12 (cap. 2)** | dia +8, 9h–11h |
| Apresentação: Iniciação Científica | Jornada | Sala 12 | dia +9, 9h–11h |
| Palestra: Carreira em TI | Semana | Auditório Central | dia +9, 14h–16h |

Duas atividades na mesma sala em horários que NÃO se sobrepõem: "Treinamento: Django Básico" (dia +8, 14h) e nada mais no Lab 201 naquele dia — aceite, pois não conflita.

`part.ana` já está inscrita na "Semana Acadêmica" e na "Jornada Científica", e inscrita em 3 atividades (uma em cada evento).

## Regras de negócio implementadas (seção 7)

| Regra | Onde é verificada |
|-------|-------------------|
| **RN1** — capacidade da sala | `Atividade.lotada()` / `vagas_restantes()` em `eventos/models.py`; usada em `views.inscrever_atividade` |
| **RN2** — conflito na agenda do participante | `views.inscrever_atividade`: consulta no banco, considerando atividades de **todos** os eventos |
| **RN3** — sala ocupada | `AtividadeForm.clean` em `eventos/forms.py` (criação e edição) |
| **RN4** — inscrição condicionada | `views.inscrever_atividade` exige `InscricaoEvento` prévia; também garantido pela modelagem (FK de `InscricaoAtividade` → `InscricaoEvento`) |
| **RN5** — cancelamento em cascata | `on_delete=CASCADE` de `InscricaoAtividade.inscricao_evento`; ao apagar `InscricaoEvento`, as atividades vão junto |

Todas as verificações acontecem **no servidor**, consultando o banco no momento do envio.

## Restrições técnicas atendidas

1. Organizador e participante nunca aparecem em formulário (preenchidos pelo sistema em `criar_evento` / via `request.user`).
2. As 5 regras da seção 7 são verificadas no servidor, mesmo que a UI já as impeça.
3. `is_superuser` **não** é usado como critério de autorização — apenas `organizador == request.user`.
4. Proteção por **decorador**: `@login_required` em várias views. Proteção por **mixin**: `EditarEventoView(LoginRequiredMixin, UserPassesTestMixin, UpdateView)`.
5. Vagas restantes são **calculadas** do banco (`sala.capacidade - inscricoes.count()`), nunca guardadas em campo.
6. Ações que alteram estado (inscrever, cancelar, excluir) usam **POST**.
7. Sem bibliotecas de terceiros além do Django.
8. Senhas via `set_password` / `UserCreationForm` — nunca atribuídas direto ao model.

## Requisitos por fazer

Nenhum. Todos os RF1–RF10 e RN1–RN5 estão implementados.

*(Opcional "Lista de espera" (seção 13) não foi implementada.)*

## Estrutura

```
config/          # settings, urls principais
eventos/         # app: models, views, forms, urls, admin, templates
seed.py          # cria as 5 contas + dados de teste (idempotente)
db.sqlite3       # banco já populado
```
