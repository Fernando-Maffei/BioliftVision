# Powerlifting App – Estrutura e Fluxo Modernizados

Este projeto foi limpo e organizado para oferecer uma operação simples e intuitiva: extração de dados, treinamento de modelo, validação e uso em produção. Abaixo você encontra a nova estrutura de pastas, convenções e comandos de acesso rápido.

## Visão Geral
- Foco em um pipeline claro: `prepare_dataset` → `train_model` → `run_model`.
 - Operação assistida pela UI unificada (`core.unified_processing`) e por CLIs: `core/train_model.py` (treino) e `core/run_model.py` (avaliação/inferência).
- Modelo carregado via `core/model_loader.py`, com `manifest.json` e alias `model/model.pkl`.
- Logs centralizados em `logs/` e resultados de avaliação em `results_oneclass/`.

## Estrutura de Pastas
- `common/` utilitários compartilhados
  - `logger.py` logging simples (`log_info`, `log_warning`, `log_error`)
  - `paths.py` caminhos padrão (`app_root`, `models_dir`, `model_file`, `results_dir`, `resource_path`)
- `core/` lógica de negócio
  - `env_check.py` verificação de ambiente e dependências
  - `keypoints.py`, `angulos.py`, `scoring_system.py` componentes analíticos
  - `model_loader.py` carregamento e validação do modelo (manifesto e alias)
- `tools/` CLIs e scripts
  - `extract_video_metadata.py` coleta metadados de vídeos para diagnóstico
  - `generate_training_report.py` gera relatório de treinamento consolidado
  - `export_diagram.py` exporta diagramas de fluxo/documentação
- `dataset/` dados brutos e processados
  - `Exercicios/Agachamento`, `Exercicios/Terra` vídeos de entrada
  - `processed_oneclass/` saída de features (`correct_movements.parquet`, `feature_config.json`)
- `model/` armazenamento do modelo treinado
  - `model.pkl` alias do último modelo pronto
  - `manifest.json` histórico e metadados do treinamento
- `results_oneclass/` métricas e imagens de avaliação
  - `evaluation_results.json`, `oneclass_confusion_matrix.png`
- `ui/` interface PyQt5 (login, menu, configurações)
  - Novos módulos: `ui/chips.py` (criação e layout de chips) e `ui/responsive.py` (cálculos de breakpoints e limites de largura)
- `config/` requisitos e configurações
  - `requirements.txt`, `pipeline.json`, `scoring_config.json`
- `tests/` testes unitários e de fumaça
  - `run_tests.py`, `test_env.py`, `test_model_loading.py`, `test_inference.py`
- `docs/` documentação
  - `workflow.md`, `libs_utilizadas.txt`
- `storage/` dados persistentes (ex.: `athletes.json`, `historico.csv`)
- `results_oneclass/`, `logs/` artefatos gerados

Notas:
- Legado: `models_oneclass/powerlifting_model.joblib` é mantido como fallback até você treinar e salvar `model/model.pkl`.
- Módulos pesados não são mais importados em `core/__init__.py` para evitar falhas em ambientes sem libs nativas.

## Convenções de Nomenclatura
- Arquivos de modelo: `model/model.pkl` (payload via `joblib`).
- Manifesto: `model/manifest.json` (lista cronológica dos treinamentos).
- Dataset processado: `dataset/processed_oneclass/correct_movements.parquet`.
- Logs: `logs/app_YYYYMM.log` e subpastas por data.

## Primeiros Passos
1) Instalar dependências:
   - `venv310\Scripts\python.exe -m pip install -r config\requirements.txt`
2) Extrair features (via UI unificada):
   - `venv310\Scripts\python.exe main.py --train`
3) Treinar modelo (CLI):
   - `venv310\Scripts\python.exe core\train_model.py --optimize`
4) Avaliar em lote:
- `venv310\Scripts\python.exe core\run_model.py --dataset dataset\processed_oneclass\correct_movements.parquet --save-results`
5) Executar inferência:
- `venv310\Scripts\python.exe core\run_model.py --video path\to\video.mp4`

Alternativa robusta (modo módulo):
- `venv310\Scripts\python.exe -m core.train_model --help`
- `venv310\Scripts\python.exe -m core.run_model --help`

## Comandos Úteis
- Treino do modelo:
  - `venv310\Scripts\python.exe core\train_model.py --optimize`
- Inferência em vídeo:
  - `venv310\Scripts\python.exe core\run_model.py --video path\to\video.mp4`
- Avaliação em lote e salvamento de métricas:
  - `venv310\Scripts\python.exe core\run_model.py --dataset dataset\processed_oneclass\correct_movements.parquet --save-results`

## Interface de Treinamento Automatizada
- A tela dedicada de treinamento orquestra todo o fluxo: extração de keypoints → pré-processamento → treinamento (com otimização) → análise pós-treino.
- Como abrir:
  - `venv310\Scripts\python.exe main.py --train`
- O que você verá:
  - Barra de progresso e logs em tempo real durante a extração e o treino.
  - Métricas de validação (acurácia, precisão, recall, F1) quando disponíveis; caso o dataset não tenha rótulos, mostra estatísticas do score (decision_function).
  - Carregamento automático do último modelo e aplicação das regras IPF (quando o módulo `core/scoring_system.py` oferece as funções apropriadas).
  - Botão "Abrir Análise em Tempo Real" para testar imediatamente o modelo na interface principal.

### Pastas externas para o dataset
- Você pode selecionar qualquer pasta de vídeos no sistema:
  - Use o botão `Selecionar Pasta do Dataset…` na tela.
  - O caminho escolhido é persistido e usado na próxima execução.
- Requisitos de acesso (Windows):
  - O app precisa de permissão de leitura na pasta.
  - Verifique o `Controlled Folder Access` (Proteção contra ransomware); adicione exceção ou use pasta não protegida.
  - Em ambientes com políticas corporativas, evite pastas de rede restritas.
- Em caso de bloqueio, a UI mostrará uma mensagem clara e manterá o caminho padrão `dataset/Exercicios`.

### Pipeline interno utilizado pela tela
- Extração: integrada à própria tela (`core.unified_processing`)
- Treinamento: `core/train_model.py --optimize` (OneClassSVM com busca simples de hiperparâmetros)
- Pós-análise: `core/run_model.py --dataset dataset\processed_oneclass\correct_movements.parquet --save-results`
- Integração de modelo: `core.run_model.ensure_model_ready()` e `latest_model_info()`

### Compatibilidade e desempenho
- A tela usa o Python da `venv310` quando disponível e captura stdout/stderr em modo não-bloqueante para atualização contínua.
- O treinamento atual (OneClassSVM) não possui épocas/loss; a otimização e validação são exibidas conforme o grid de parâmetros e métricas calculadas.
- A validação IPF depende das funções presentes em `core/scoring_system.py`; quando ausentes, a verificação ocorre na interface de análise.

## Validação
- Rode os testes:
  - `venv310\Scripts\python.exe tests\run_tests.py`
- O que é verificado:
  - Ambiente (`core.env_check`)
  - Modelo pronto (`core.run_model.ensure_model_ready`)
  - Inferência básica (`run_model.vectorize_features`, `run_model.predict`)
- Treinamento automatizado: execução do pipeline e salvamento de resultados em `results_oneclass/evaluation_results.json` (via `core/run_model.py`).

## Mudanças Recentes
- Removidos scripts obsoletos: `tools/train_oneclass.py`, `tools/extract_features.py`.
- `core/__init__.py` agora é leve e não importa módulos pesados por padrão.
- `core/train_model.py` e `core/run_model.py` ajustados com bootstrap de caminho para evitar `ModuleNotFoundError`.
- Adicionada `ui/training.py`: tela exclusiva de treinamento com automação, integração e exibição de métricas.
- Adicionada `ui/unified_processing.py`: tela unificada para processar vídeos (frames/keypoints/features), salvar em formatos compatíveis e opcionalmente treinar/avaliar.
- Refatoração da UI principal:
  - Alinhamento dos controles inferiores de `Qt.AlignHCenter` para `Qt.AlignLeft`.
  - Criação dos módulos `ui/chips.py` (chips de status) e `ui/responsive.py` (responsividade) e uso em `ui/interface.py`.
  - Limitação de larguras à esquerda via `responsive.clamp_left_width` e cálculo do painel direito via `responsive.compute_right_panel_width`.

## Documentação complementar
- Estrutura do projeto: `docs/estrutura.md`
- Convenções de nomes e organização: `docs/convencoes.md`
- Guia de manutenção e compatibilidade: `docs/guia_manutencao.md`

## Tela Unificada de Processamento
- O que faz:
  - Lista e processa vídeos em `dataset/Exercicios/*`, extraindo keypoints e calculando features de movimento via `core/keypoints.py`.
  - Salva os dados em formatos compatíveis com treinamento: `.npz` (default), `.hdf5` ou `.parquet`.
  - Pode disparar o treino ao finalizar (usa `core/train_model.py`).
- Como abrir:
- `venv310\Scripts\python.exe -c "from core.unified_processing import UnifiedProcessingWindow as W; import sys; from PyQt5.QtWidgets import QApplication; app=QApplication(sys.argv); win=W(); win.show(); app.exec_()"`
  - Integração futura pelo menu principal (`MainMenu`) conforme necessidade.
- Parâmetros configuráveis:
  - `stride` (amostragem de frames), `max_frames` (limite por vídeo), `workers` (extrator), `formato de saída`.
- Formato de saída (documentação):
  - `.npz`: contém `X` (float64, N x F), `y` (int, N), `features` (lista de nomes), `videos` (lista de arquivos). Carregado automaticamente pelo `train_model.load_dataset()`.
  - `.hdf5`: datasets `X`, `y`, `features`, `videos` (strings UTF-8). Carregado por `train_model.load_dataset()` quando `h5py` disponível.
  - `.parquet`: DataFrame com colunas de features numéricas, mais `label` e `video`.
- Tratamento de erros:
  - Vídeos corrompidos ou não abríveis são logados e ignorados.
  - Falhas de exportação `.hdf5/.parquet` geram fallback para `.npz` com aviso.


## Próximos Melhorias (Opcional)
- Consolidar `results_oneclass/` para `results/` com namespaces por tarefa.
 - Criar testes específicos para `core/train_model.py` e `core/run_model.py`.
- Adicionar validação automática pós-treino e registro no `manifest.json`.
## Diagrama de Fluxo do Sistema

Para uma visão completa e compartilhável do processo (extração → pré-processamento → treinamento → validação → implementação → monitoramento), consulte o diagrama em `docs/system_flow.md`.

Você pode visualizar e exportar para PNG/PDF via Mermaid (ver instruções no próprio arquivo).
