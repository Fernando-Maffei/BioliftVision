# Projeto TCC – Powerlifting App

Este projeto foi reestruturado para garantir abertura e execução sem erros no Windows com Python 3.10 (x64), mantendo todas as funcionalidades originais e adicionando testes, scripts de execução e documentação clara.

## Visão Geral
- Aplicação com interface em PyQt5 para login e menu principal.
- Modo de análise de vídeo baseado em `mediapipe` e `opencv`.
- Verificação de ambiente sem importar bibliotecas nativas pesadas (evita warnings de DLL na inicialização).
- Logs rotativos em `logs/powerlifting_app.log` para diagnóstico.

## Requisitos
- Windows 10/11 64-bit.
- Python 3.10 (64-bit) instalado.
- Microsoft Visual C++ Redistributable 2015–2022 (x64) atualizado.

## Configuração Rápida
1. Crie o ambiente virtual `venv310` na raiz do projeto:
   - `python -m venv venv310`
   - `venv310\Scripts\python.exe -m pip install --upgrade pip`
2. Instale as dependências:
   - `venv310\Scripts\pip.exe install -r config\requirements.txt`
3. (Opcional) Abra no VS Code. O projeto já aponta para `venv310` em `.vscode/settings.json`.

## Execução
- Aplicação padrão (login/menu):
  - `run_app.bat`
- Modo análise direto:
  - `run_analysis.bat`
- Verificação do ambiente (executa junto com a aplicação):
  - Veja logs em `logs/powerlifting_app.log`

## Testes
Foram adicionados testes unitários para a persistência das avaliações:
- `tests/test_persistence.py` valida `init_db` e `save_attempt` usando diretório temporário.
- Para executar: `venv310\Scripts\pytest.exe -q`.

## Estrutura de Pastas
- `common/` utilitários (logger, paths etc.)
- `core/` lógica principal (inclui `env_check.py` reescrito para checar versões sem importar nativos)
- `ui/` componentes PyQt5 (login, menu, etc.)
  - Novos módulos: `ui/chips.py` (chips de status) e `ui/responsive.py` (responsividade).
- `config/` configurações (`requirements.txt`, `scoring_config.json`)
- `logs/` arquivos de log rotativos
- `docs/` documentação
- `tools/` utilitários auxiliares
- `venv310/` ambiente virtual de desenvolvimento (não versionado)

## Logs e Diagnóstico
- Log principal: `logs/powerlifting_app.log` (rotativo, 1MB, até 5 arquivos).
- Mensagens úteis:
  - "Venv ativa: SIM" e "Ambiente OK" – verificação de ambiente passou.
  - Avisos de modelo: se não houver modelo treinado, o app entra em modo somente análise visual.
  - Qualquer erro é acompanhado de stacktrace.

## Ambiente de Desenvolvimento
- VS Code: `.vscode/settings.json` já configura `python.defaultInterpreterPath` para `venv310\\Scripts\\python.exe`.
- IntelliSense: `python.analysis.extraPaths` aponta para `./core` e `./ui` para importação facilitada.

## Compatibilidade e Notas
- Dependências foram fixadas para versões com wheels disponíveis para Python 3.10 no Windows.
- `core/env_check.py` usa `importlib.metadata` e `packaging` para checar versões sem carregar libs nativas de `mediapipe/opencv` durante a inicialização.

## Solução de Problemas
- Warning de DLL em `mediapipe`:
  - Instale/atualize Microsoft Visual C++ Redistributable (x64) 2015–2022.
  - Certifique-se de que o Python é 64-bit e a `venv310` foi criada com ele.
  - Reinstale dependências: `pip install --force-reinstall -r config\requirements.txt`.
- Qt plugins:
  - Em ambientes sem display, os testes usam `QT_QPA_PLATFORM=offscreen`.

## Pastas Externas para Treinamento
- A tela de Treinamento permite escolher uma pasta externa para os vídeos do dataset.
- Como usar:
  - Abra a tela de Treinamento.
  - Clique em `Selecionar Pasta do Dataset…` e aponte para qualquer pasta acessível no sistema.
  - O caminho fica persistido entre execuções (via `QSettings`).
- Requisitos de acesso:
  - Permissão de leitura na pasta escolhida (listagem e abertura de arquivos).
  - Em Windows, verifique se o recurso `Controlled Folder Access` (Proteção contra ransomware) não bloqueia o app.
    - Se necessário, mova os vídeos para uma pasta não protegida (ex.: `Documentos\BioLiftVision`),
      ou adicione uma exceção para o executável.
  - Em ambientes corporativos, políticas de segurança podem restringir pastas de rede; use uma pasta local.
- Tratamento de erros:
  - Se o acesso for negado, a UI apresenta um erro descritivo e registra detalhes no log.
  - O app continua funcionando e mantém o caminho padrão (`dataset/Exercicios`) caso a seleção falhe.

## Manutenção
- Para atualizar dependências, edite `config/requirements.txt` e reinstale com o script.
- Mantenha a `venv310` como ambiente padrão para desenvolvimento.

## Persistência de Avaliações (SQLite)
- O módulo `storage/persistence.py` inicializa o banco `storage/evaluations.db`.
- Cada tentativa salva armazena: `created_at`, `athlete`, `exercise`, `attempt`, `auto_valid`, `auto_summary` (JSON), `judge_valid`, `judge_notes`, `angles` (JSON).
- O botão `Salvar Tentativa` exige: exercício selecionado, atleta informado, decisão do juiz e notas preenchidas, além de a avaliação automática ter sido executada.

## Ajustes de UI
- O gráfico de ângulos (`pyqtgraph`) foi tornado opcional e está desativado por padrão.
- O redimensionamento da janela unificado centraliza e ajusta automaticamente a área do vídeo; há apenas um `resizeEvent` que atualiza o fundo, a largura do painel direito e a área do player.
- Alinhamento dos controles inferiores ajustado para a esquerda e cálculo de larguras reorganizado via `ui/responsive.py` (evita cortes com o painel direito).
- Criação e layout dos chips de status agora centralizados em `ui/chips.py`.

## Documentação complementar
- Estrutura do projeto: `docs/estrutura.md`
- Convenções: `docs/convenções.md`
- Guia de manutenção: `docs/guia_manutencao.md`

## Verificação rápida
1. Abra `python main.py` e carregue um vídeo.
2. Execute uma repetição para gerar avaliação automática.
3. Registre a decisão do juiz e preencha as notas.
4. Clique em `Salvar Tentativa` e verifique `storage/historico.csv` e `storage/evaluations.db`.
