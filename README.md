# Sistema de Inscrições para Eventos do Campus

Um evento reúne várias atividades (palestras, treinamentos, apresentações). Cada atividade acontece em uma sala, em um horário, e a capacidade da sala limita o número de inscritos.

## Integrantes

- **Maria Luiza**

## Atividade 08 — Testes

### Como rodar a suíte

```bash
python manage.py test
```

- **Quantos testes:** 49 (divididos em `tests/test_models`, `test_forms`, `test_views`, `test_api`, `test_queries`).
- **Quanto tempo levam:** ~21 s com `--parallel 4`, ~70 s em série.
- A suíte passa com `--shuffle` (testado 3×), com o `db.sqlite3` apagado, e cada módulo roda isolado.
- Nenhum teste usa `time.sleep`, endereço escrito à mão (todos via `reverse()`) ou dado pré-existente: cada teste cria o próprio cenário, e os compartilhados ficam em `setUpTestData`.

### Tabela de sabotagem

Cada sabotagem foi aplicada uma por vez, a suíte inteira rodada, e o código desfeito.

| Sabotagem | Teste que falhou | Verde na 1ª rodada? |
|-----------|------------------|---------------------|
| 1. Capacidade da sala comentada (`services.inscrever_em_atividade`) | `test_rn1_inscreve_ate_a_capacidade_e_recusa_a_terceira` (site) e `test_rn1_api_recusa_terceira_inscricao` (API) | não |
| 2. Horário sobreposto do participante comentado | `test_rn2_mesmo_horario_para_o_participante_e_recusado` (site) e `test_rn2_api_recusa_horario_sobreposto` (API) | não |
| 3. Sala ocupada comentada (`AtividadeForm.clean`) | `test_rn3_duas_atividades_na_mesma_sala_sobrepostas_e_recusado` e `test_rn3_sala_ocupada_e_recusada_pelo_formulario` | não |
| 4. Inscrição prévia no evento removida | `test_rn4_sem_inscricao_no_evento_e_recusado` e `test_rn4_api_recusa_sem_inscricao_no_evento` | não |
| 5. Cancelar o evento para de cancelar as atividades | `test_rn5_cancelar_evento_remove_inscricoes_das_atividades` e `test_post_cancelar_evento_apaga_e_redireciona` | não |
| 6. Redirect trocado por render após o POST de inscrição | nenhum na 1ª rodada → acrescentei `test_post_inscrever_atividade_redireciona_para_o_detalhe` | **sim** |
| 7. Verificação de dono removida da edição de evento | `test_organizador_nao_edita_evento_de_outro` | não |
| 8. Campo a mais no serializer da porta aberta | nenhum na 1ª rodada → o teste de chave virou `assertEqual` do conjunto exato de chaves (`test_lista_eventos_nao_expose_organizador_id_nem_senha`) | **sim** |
| 9. `prefetch_related`/`select_related` removidos da programação | `test_programacao_com_uma_atividade_usa_poucas_consultas` e `test_programacao_com_cinco_atividades_nao_cresce` (o N+1 aumenta o número de queries) | não |

Duas sabotagens (6 e 8) passaram na primeira rodada: os testes antigos visitavam o código sem observá-lo. Em ambos os casos o novo teste afirma algo que antes era implícito — o status 302 do redirect e o conjunto exato de chaves do JSON.

### Cobertura

`coverage run --source=eventos manage.py test && coverage report`: **80% total**
(`views.py` 57%, `api/views.py` 79%, `services.py` 91%, `models.py` 95%, `forms.py` 96%).

O parágrafo prometido: a cobertura de 80% conviveu com duas sabotagens que ninguém pegou. As linhas do redirect e do serializer estavam *cobertas* — os testes passavam por elas — mas nada observava o que elas faziam. Cobertura mede visita, não vigilância; a tabela de sabotagem é que diz quem vigia de verdade. O menor número (57% em `views.py`) vem das telas de CRUD de organizador, que têm testes de autorização mas não de renderização completa.

### Regras escritas em dois lugares

Na atividade anterior as regras moravam nas views (site) e no formulário. Quando os testes das duas portas foram escritos lado a lado, ficou claro que repetir as cinco regras no serializer seria duplicação — então elas foram extraídas para **`eventos/services.py`** (`inscrever_em_atividade` para RN1/RN2/RN4 e `validar_atividade` para RN3/RN5-complementos), chamado tanto por `views.py` quanto pela API (`api/serializers.py` e `api/views.py`). Hoje cada regra existe exatamente uma vez; a sabotagem 1, por exemplo, fez a suíte falhar nas duas portas com uma única edição.

### Nota sobre a API

Durante o início desta atividade a pasta `eventos/api/` tinha sido perdida (restavam apenas os `.pyc`). A API foi reconstruída com base nesses artefatos: DRF + `TokenAuthentication`, roteamento `atividades/` e `salas/` via router, endpoints de eventos/programação/agenda e `/api/token/`. Foi exatamente o "descobrir sem escrever teste" da seção 2 do enunciado — sem a exigência de testar a API, o desaparecimento não teria sido notado.

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

| Regra | Onde é verificada (uma única vez) |
|-------|-------------------|
| **RN1** — capacidade da sala | `Atividade.lotada()` chamada por `services.inscrever_em_atividade` (site e API) |
| **RN2** — conflito na agenda do participante | `services.inscrever_em_atividade` (site e API), considerando todos os eventos |
| **RN3** — sala ocupada | `services.validar_atividade`, chamado por `AtividadeForm.clean` (site) e `AtividadeSerializer.validate` (API) |
| **RN4** — inscrição condicionada | `services.inscrever_em_atividade`; também garantido pela modelagem (FK de `InscricaoAtividade` → `InscricaoEvento`) |
| **RN5** — cancelamento em cascata | `on_delete=CASCADE` de `InscricaoAtividade.inscricao_evento` |

Todas as verificações acontecem **no servidor**, consultando o banco no momento do envio.

## Restrições técnicas atendidas

1. Organizador e participante nunca aparecem em formulário (preenchidos pelo sistema em `criar_evento` / via `request.user`).
2. As 5 regras da seção 7 são verificadas no servidor, mesmo que a UI já as impeça.
3. `is_superuser` **não** é usado como critério de autorização — apenas `organizador == request.user`.
4. Proteção por **decorador**: `@login_required` em várias views. Proteção por **mixin**: `EditarEventoView(LoginRequiredMixin, UserPassesTestMixin, UpdateView)`.
5. Vagas restantes são **calculadas** do banco (`sala.capacidade - inscricoes.count()`), nunca guardadas em campo.
6. Ações que alteram estado (inscrever, cancelar, excluir) usam **POST**.
7. Bibliotecas externas: `djangorestframework` (API, atividade anterior) e `coverage` (a única permitida nesta atividade).
8. Senhas via `set_password` / `UserCreationForm` — nunca atribuídas direto ao model.

## Requisitos por fazer

Nenhum. Todos os RF1–RF13 da atividade 08 estão implementados (a suíte: `python manage.py test`).

*(Opcional "Lista de espera" (seção 13) não foi implementada.)*

## Estrutura

```
config/          # settings, urls principais
eventos/         # app: models, views, forms, urls, admin, templates, api/
eventos/services.py  # lugar único das cinco regras de negócio
tests/           # suíte: base, test_models, test_forms, test_views, test_api, test_queries
seed.py          # cria as 5 contas + dados de teste (idempotente)
db.sqlite3       # banco já populado
```
