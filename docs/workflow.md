# Guia de Fluxo de Trabalho — Powerlifting App

Este guia redesenha o fluxo de trabalho para torná-lo simples, intuitivo e autoexplicativo. Use-o como referência rápida para executar extração de dados, treinamento e avaliação do modelo.

## Sequência de Execução (Etapas Numeradas)
1) 🔴 [CRÍTICO] Preparar ambiente
   - Ativar `venv310` e instalar dependências (`config/requirements.txt`).
   - Verificar disponibilidade de `pyarrow`, `mediapipe`, `numpy`, `scikit-learn`.

2) 🟡 [DEPENDÊNCIA] Extrair features dos vídeos
   - Fonte: `dataset/Exercicios/Agachamento` e `dataset/Exercicios/Terra`.
   - Saída: `dataset/processed_oneclass/correct_movements.parquet`.

3) 🔴 [CRÍTICO] Treinar modelo (OneClassSVM)
   - Entrada: Parquet de features.
   - Saída: `model/model.pkl` e `models_dir/manifest.json` com `sha256`/`features_count`.

4) 🟢 [MILESTONE] Validar e registrar métricas
   - Avaliar em lote com `core/run_model.py --dataset ... --save-results`.
   - Saída: `results_oneclass/evaluation_results.json` e gráficos (se aplicável).

5) 🟢 [MILESTONE] Operação
   - Inferência pontual por vídeo/JSON (`core/run_model.py --video`/`--features-json`).

Legenda visual:
- 🔴 Crítico (execute primeiro)
- 🟡 Dependência (pré-requisito para próximos passos)
- 🟢 Marco (milestone concluído)

## Mecanismo de Acompanhamento
- Progresso atual: calculado por etapas concluídas (0–100%).
- Próximas ações imediatas: sugeridas conforme a etapa atual.
- Bloqueadores potenciais: ambiente não ativo, dataset não encontrado, dependências ausentes, modelo não pronto.

Use a CLI de acompanhamento para visualizar:

```
venv310\Scripts\python.exe tools\workflow.py status
```

Exemplo de saída:
```
Etapas:
1. 🔴 Preparar ambiente — OK
2. 🟡 Extrair features — PENDENTE
3. 🔴 Treinar modelo — PENDENTE
4. 🟢 Validar métricas — PENDENTE
5. 🟢 Operação — PENDENTE

Progresso: 20%
Próximas ações: Executar extração pela tela unificada (`main.py --train`)
Bloqueadores: Falta arquivo dataset/processed_oneclass/correct_movements.parquet
```

## Indicadores Visuais de Eficácia
- Treinamento: exibe métricas de validação (accuracy/precision/recall/F1) ou estatísticas do score.
- Avaliação em lote: mostra métricas salvas em `results_oneclass/evaluation_results.json`.
- Status do modelo: verificado via `core.run_model.ensure_model_ready()`.

## Primeiros Passos (Acesso Rápido)
1) Ativar ambiente
   - `venv310\Scripts\python.exe -m pip install -r config\requirements.txt`

2) Extrair features (UI)
   - `venv310\Scripts\python.exe main.py --train`

3) Treinar modelo (CLI)
   - `venv310\Scripts\python.exe core\train_model.py --optimize`

4) Avaliar em lote
   - `venv310\Scripts\python.exe core\run_model.py --dataset dataset\processed_oneclass\correct_movements.parquet --save-results`

5) Inferência pontual
   - `venv310\Scripts\python.exe core\run_model.py --video path\to\video.mp4`

## Exemplos de Execução Bem-sucedida
- Treino concluído: cria `models_dir/model.pkl` e atualiza `manifest.json` com `sha256`.
- Avaliação salva: `results_oneclass/evaluation_results.json` contém métricas calculadas.
- Inferência: saída JSON com `biomechanical_valid`, `raw_pred` e `score` impressa no console.

