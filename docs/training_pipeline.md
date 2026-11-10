# Pipeline de Treinamento (Vídeo → Metadados → OneClassSVM)

Este documento descreve o processo completo solicitado: extração de metadados/feature básicas de vídeos, preparação dos dados, configuração e execução do treinamento (com validação cruzada e otimização de hiperparâmetros), e documentação de resultados.

## 1) Extração de Metadados
- Comando:
  - `python tools/extract_video_metadata.py --input-dir "dataset" --out-csv "dataset/metadata/video_metadata.csv" --out-json "dataset/metadata/video_metadata.json"`
- Saídas:
  - `dataset/metadata/video_metadata.csv` (tabela com colunas numéricas e descritivas)
  - `dataset/metadata/video_metadata.json` (lista de objetos por vídeo)
- Campos relevantes (numéricos usados no treino): `duration_seconds`, `width`, `height`, `fps`, `frames`, `bitrate`, `has_subtitles (0/1)`, `codec_fourcc (se disponível)`
- Observação: se `ffprobe` estiver disponível, codecs, bitrate e legendas incorporadas são detectados com maior confiança; caso contrário, OpenCV fornece metadados básicos.

## 2) Preparação e Configuração
- Arquivo de configuração: `config/pipeline_video_metadata.json`
  - `data.train_path`: caminho do CSV gerado
  - `data.ignore_cols`: lista de colunas não numéricas a excluir
  - `training.optimize`: `true` para realizar busca em grade
  - `training.param_grid`: grade simples em `nu`, `gamma` e `kernel`

## 3) Treinamento com Validação
- Comando:
  - `python core/train_model.py --config config/pipeline_video_metadata.json`
- Modelo: `OneClassSVM` com `StandardScaler` e `SimpleImputer`
- Validação:
  - Sem rótulos, usa K-Fold e estatísticas de `decision_function` como métrica proxy na otimização
- Saídas:
  - `model/model.pkl` (alias)
  - Versão com timestamp em `model/`
  - `model/manifest.json` com histórico, hiperparâmetros e métricas

## 4) Relatório de Resultados
- Comando:
  - `python tools/generate_training_report.py`
- Saída:
  - `docs/training_report.md` com hiperparâmetros escolhidos e métricas (ou instruções se nenhum treino foi registrado)

## 5) Próximos Passos (opcionais)
- Expandir features além de metadados estáticos (p.ex., keypoints de pose via MediaPipe), gerando CSVs por vídeo para melhorar o poder preditivo.
- Introduzir rótulos (`label=1/0`) para validação supervisionada (acurácia/precisão/recall/F1).
- Ajustar `ignore_cols` e engenharia de atributos (one-hot para codecs/containers, normalizações específicas).
