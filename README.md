# Sistema de Inscrições para Eventos do Campus

Um evento reúne várias atividades (palestras, treinamentos, apresentações). Cada atividade acontece em uma sala, em um horário, e a capacidade da sala limita o número de inscritos.

Esta versão adiciona uma **API REST** (Django REST Framework) ao lado do site HTML, que continua funcionando exatamente como antes. A API atende o app de celular, o painel em React/Vue e scripts de importação — nenhum deles precisa de HTML.

**Branch:** `api-rest` (o `main`/original permanece intacto — é a entrega anterior).

## API

- Documentação navegável (Swagger): **`/api/docs/`** — lista todos os endpoints
- Schema OpenAPI: `/api/schema/`
- Prefixo único: `/api/`
- Autenticação por **Token** no cabeçalho: `Authorization: Token <token>`

### Endpoints

| Método | Rota | Auth | O que faz |
|--------|------|------|-----------|
| GET | `/api/eventos/?q=termo` | pública | Lista de eventos, com busca |
| POST | `/api/eventos/` | token | Cria evento (organizador = quem autenticou) |
| GET | `/api/eventos/{id}/` | pública | Detalhe do evento |
| PUT/PATCH/DELETE | `/api/eventos/{id}/` | token do organizador | Altera/exclui |
| GET | `/api/eventos/{id}/programacao/` | pública | **Desafio**: evento + atividades + sala + vagas em 1 requisição |
| POST | `/api/eventos/{id}/inscrever/` | token | Participante se inscreve no evento |
| DELETE | `/api/eventos/{id}/cancelar/` | token | Cancela inscrição no evento (RN5: atividades somem) |
| GET | `/api/atividades/?search=&ordering=inicio&page=` | pública | Lista paginada, buscável e ordenável (ViewSet) |
| POST | `/api/atividades/` | token do organizador do evento | Cria atividade (RN3 verificado) |
| PUT/PATCH/DELETE | `/api/atividades/{id}/` | token do organizador | Altera/exclui |
| POST | `/api/atividades/{id}/inscrever/` | token | RN1, RN2 e RN4 verificados |
| DELETE | `/api/atividades/{id}/cancelar/` | token | Cancela inscrição na atividade |
| GET | `/api/agenda/` | token | Atividades de quem apresentou o token, ordenadas |
| GET | `/api/salas/` | pública | Salas |
| POST | `/api/token/` | usuário+senha | Devolve o token |

### Tokens das contas de teste

Senha de todas: **rad2026#senha**. Obtenha o token com:

```bash
curl -X POST http://127.0.0.1:8000/api/token/ -d "username=org.carlos&password=rad2026#senha"
```

| Usuário | Papel | Token |
|---------|-------|-------|
| `admin` | Superusuário | `cf737b9f3068e0694084d5bdaf4eab3a1ff9f317` |
| `org.carlos` | Organizador | `65efb5fa8ac6b85706c4c381e6cf22c4a4eef8e0` |
| `org.beatriz` | Organizador | `3dbca5bb7c2c3f74d3b5c269c5bfa9f277a109f1` |
| `part.ana` | Participante | `50a435f50ffbdc6761be812bbd1a6ef23920b098` |
| `part.bruno` | Participante | `e3380598c0217c69c27431c2aa301886f4367bcb` |

## Integrantes

- **Maria Luiza**

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

## Regras de negócio implementadas (seção 7 da atividade anterior / seção 4 desta)

**Onde as regras moram e por quê:** as cinco regras vivem em **um único lugar**, o módulo `eventos/services.py`, que é chamado pelos DOIS caminhos até o banco (site HTML e API). Escolhi isso em vez de reescrever as regras no serializer porque duas cópias divergem no primeiro ajuste: se a regra mudasse (ex.: tolerância de 10 min entre atividades), teria de ser corrigida em dois lugares — e um deles seria esquecido. Com o serviço compartilhado, o serializer (API) e o `ModelForm` (site) apenas repassam os erros que o serviço devolve; nenhum dos dois reimplementa nada.

| Regra | Onde é verificada (única vez) | Quem chama |
|-------|-------------------|-----------|
| **RN1** — capacidade da sala | `services.inscrever_em_atividade` → `Atividade.lotada()` | site (`views.inscrever_atividade`) **e** API (`api.views.inscrever_atividade`) |
| **RN2** — conflito na agenda do participante | `services.inscrever_em_atividade` (consulta considerando **todos** os eventos) | idem, ambos |
| **RN3** — sala ocupada | `services.validar_atividade` | site (`AtividadeForm.clean`) **e** API (`AtividadeSerializer.validate`) |
| **RN4** — só quem está no evento | `services.inscrever_em_atividade` + FK `InscricaoAtividade → InscricaoEvento` | ambos |
| **RN5** — cancelar evento cancela atividades | `on_delete=CASCADE` no model (estrutura do banco, um só lugar) | ambos |

### Teste da seção 8 — violar RN3 pela API

Operação: POST `/api/atividades/` com token de `org.carlos`, criando atividade no Auditório Central (sala 1) das 09:30 às 10:30 do dia em que "Palestra: IA Generativa" (mesma sala) ocupa 09:00–11:00.

- **Código HTTP:** `400`
- **Corpo:** `{"detalhe":["A sala Auditório Central já está ocupada nesse horário (atividade: Palestra: IA Generativa na Prática, x)."]}`
- **Arquivo e método:** `eventos/services.py`, função `validar_atividade` — chamada por `AtividadeSerializer.validate` (`eventos/api/serializers.py`) na API e por `AtividadeForm.clean` (`eventos/forms.py`) no site.
- **O site HTML, na mesma operação:** repassa o MESMO código (`forms.py` apenas repassa o retorno do serviço e exibe a mensagem no template). As duas camadas verificam a regra no MESMO lugar — não há duas cópias, e a restrição técnica 2 é cumprida.

## ViewSet × APIView — por quê

- **ViewSet + router:** `Atividade` (`/api/atividades/`). É o único recurso com CRUD padrão completo e precisa de paginação, busca por `?search=` e ordenação por `?ordering=inicio` (RF10) — o `ModelViewSet` + `SearchFilter`/`OrderingFilter` dão tudo isso pronto e uniforme.
- **`@api_view` / `APIView`:** eventos (GET/POST + PUT/DELETE com dono), programação pública, inscrição/cancelamento de evento e atividade, e agenda. São **ações pontuais do domínio**, não CRUD: um ViewSet criaria rotas sem sentido (PUT de inscrição, POST de agenda). `@api_view` mantém cada endpoint explícito e pequeno.

## Restrições técnicas atendidas

1. Organizador e participante nunca aparecem em formulário (preenchidos pelo sistema em `criar_evento` / via `request.user`). Na API, `organizador` e `participante` são `read_only`/injetados de `request.user` — nunca do JSON.
2. As 5 regras são verificadas no servidor, em UM lugar (`services.py`), pelos dois caminhos.
3. `is_superuser` **não** é usado como critério de autorização — apenas `organizador == request.user`.
4. Proteção por **decorador**: `@login_required` em várias views. Proteção por **mixin**: `EditarEventoView(LoginRequiredMixin, UserPassesTestMixin, UpdateView)`. Na API: `IsAuthenticated`, `IsAuthenticatedOrReadOnly` e `IsOrganizadorDoEvento`.
5. Vagas restantes são **calculadas** do banco (`sala.capacidade - inscricoes.count()`; na listagem da API, via `annotate(Count('inscricoes'))`), nunca guardadas em campo.
6. Ações que alteram estado (inscrever, cancelar, excluir) usam **POST/DELETE**.
7. Terceiros: apenas **DRF** e **drf-spectacular** (permitidos).
8. Senhas via `set_password` / `UserCreationForm` — nunca atribuídas direto ao model.
9. Nada de `request.data` lido direto na lógica de negócio: os dados entram validados pelo serializer/form, e o service só recebe objetos prontos.

## Requisitos por fazer

Nenhum. RF1–RF11 implementados, incluindo o desafio da programação em uma requisição (`/api/eventos/{id}/programacao/` — 3 consultas fixas: evento, atividades+salas e contagem de inscrições via `annotate`; não cresce com o número de atividades).

*(Opcional "Lista de espera" da atividade anterior não foi implementada.)*

## Estrutura

```
config/          # settings, urls principais
eventos/         # app: models, views (HTML), forms, urls, admin, templates
eventos/api/     # API REST: serializers, views, permissions, urls
eventos/services.py  # ÚNICO lugar das 5 regras de negócio
seed.py          # cria as 5 contas + dados de teste (idempotente)
db.sqlite3       # banco já populado (com migrations e tokens)
```

## Como testar a API rapidamente

```bash
# 1. eventos públicos
curl http://127.0.0.1:8000/api/eventos/
# 2. programação com sala e vagas
curl http://127.0.0.1:8000/api/eventos/1/programacao/
# 3. criar sem token → 401
curl -X POST http://127.0.0.1:8000/api/atividades/ -H "Content-Type: application/json" -d '{}'
# 4. criar com token do organizador → 201
curl -X POST http://127.0.0.1:8000/api/atividades/ -H "Content-Type: application/json" -H "Authorization: Token 65efb5fa8ac6b85706c4c381e6cf22c4a4eef8e0" -d '{"evento":1,"titulo":"Nova","tipo":"palestra","responsavel":"X","sala":2,"inicio":"2026-12-01T09:00:00-03:00","fim":"2026-12-01T10:00:00-03:00"}'
```
