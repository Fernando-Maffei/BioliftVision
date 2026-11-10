# Guia de Estruturação e Manutenção

Este guia ajuda a planejar mudanças, evitar regressões e manter compatibilidade com sistemas dependentes.

## Antes de alterar
- Verifique logs recentes em `logs/` (ex.: avisos de ODBC/ODBC Driver).
- Rode testes disponíveis (quando aplicável): `venv310\Scripts\python.exe tests\run_tests.py`.
- Confirme versão do Python (3.10 x64) e venv ativa.

## Padrões de refatoração
- UI:
  - Isolar componentes reutilizáveis (`ui/chips.py`) e utilitários (`ui/responsive.py`).
  - Evitar lógica complexa dentro de `ui/interface.py`; delegue a módulos.
  - Manter cálculos de largura usando `responsive.clamp_left_width` e breakpoints.
- Core:
  - Manter funções puras onde possível; facilitar testes.
  - Registrar alterações de modelo em `model/manifest.json`.
- Common:
  - Centralizar logs e caminhos; não depender de UI.

## Compatibilidade com sistemas dependentes
- Banco de Dados (ODBC/SQL):
  - Falha de conexão não deve bloquear a UI. Use `storage/evaluations.db` como fallback.
  - Em produção, configure DSN/ODBC e credenciais em variáveis de ambiente ou arquivo dedicado.
  - Teste `db/test_db.py` e `db/test_analysis_repository.py` se presentes.
- Arquivos e permissões:
  - Valide acesso a `dataset/` e pasta externa de vídeos.
  - Em Windows, verifique “Controlled Folder Access”.

## Checklist pós-mudança
1. Abrir a aplicação (`main.py`) e navegar pela tela principal.
2. Verificar chips de status e barra do player sem cortes visuais.
3. Redimensionar janela e checar responsividade do painel direito.
4. Executar uma avaliação automática e persistir tentativa em `storage/evaluations.db`.
5. Conferir logs por avisos/erros (ODBC, DLLs, Qt plugins).

## Como estender
- Adicionar novo chip de status:
  - Incluir mapeamento de cor em `ui/style.py`.
  - Permitir status no `chips.make_chip()`.
  - Atualizar layout em `chips.update_chips_grid()` se necessário.
- Ajustar breakpoints:
  - Editar `responsive.compute_right_panel_width()`.
  - Validar em resoluções comuns (1366×768, 1920×1080, 2560×1440).

## Registros e documentação
- Atualize `README.md` com as mudanças relevantes.
- Documente fluxos ou decisões em `docs/system_flow.md` quando afetar o pipeline.
- Mantenha este guia sincronizado com convenções e estrutura.

## Solução de problemas
- ODBC/SQL: se houver erros, o app deve continuar com armazenamento local. Investigue driver/credenciais.
- Qt: se notar cortes ou sobreposição, revise `clamp_left_width` e alinhamentos.
- Mediapipe/OpenCV: reinstale dependências e verifique Redistributable (x64).