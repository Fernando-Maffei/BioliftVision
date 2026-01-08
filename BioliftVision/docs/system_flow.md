# Diagrama de Fluxo do Sistema

Este diagrama descreve, passo a passo, o fluxo completo do sistema: Extração de Dados, Pré-processamento, Treinamento, Validação, Implementação e Monitoramento. Inclui entradas/saídas, ferramentas, critérios de qualidade e pontos de verificação.

```mermaid
flowchart TD
  %% Estilo e classes
  classDef etapa fill:#eef,stroke:#336,stroke-width:1px,color:#111
  classDef criterio fill:#ffe,stroke:#b80,stroke-width:1px,color:#111
  classDef dado fill:#efe,stroke:#393,stroke-width:1px,color:#111
  classDef proc fill:#eef,stroke:#336,stroke-width:1px,color:#111

  %% EXTRAÇÃO DE DADOS
  subgraph E[1) Extração de Dados]
    direction TB
    E1[/CSV Agachamento (*.csv)/]
    E2[/CSV Terra (*.csv)/]
    E3{CSV(s) válidos encontrados?}
    E4([Coletar CSVs]):::proc
    E5[(Dataset combinado - linhas brutas)]:::dado
    E1 --> E3
    E2 --> E3
    E3 -- Sim --> E4 --> E5
    E3 -- Não --> E6[[Revisar diretórios e dependências]]
  end

  %% PRÉ-PROCESSAMENTO
  subgraph P[2) Pré-processamento]
    direction TB
    P1([Adicionar metadados: 'exercise', 'label', 'video'])
    P2([Incremental e deduplicação por 'video'])
    P3{Colunas e tipos esperados?}
    P4[(Parquet: dataset/processed_oneclass/correct_movements.parquet)]:::dado
    E5 --> P1 --> P2 --> P3
    P3 -- Sim --> P4
    P3 -- Não --> P5[[Corrigir schema/linhas inválidas]]
  end

  %% TREINAMENTO
  subgraph T[3) Treinamento]
    direction TB
    T1([Carregar Parquet de entrada])
    T2([Selecionar modelo e parâmetros])
    T2a[[Ex.: --optimize habilita busca de hiperparâmetros]]
    T3([Treinar e salvar artefatos])
    T4[(Modelo: models_oneclass/powerlifting_model.joblib)]:::dado
    T5[(Manifest: model/manifest.json)]:::dado
    P4 --> T1 --> T2 --> T3 --> T4 --> T5
  end

  %% VALIDAÇÃO
  subgraph V[4) Validação]
    direction TB
    V1([Definir método: hold-out ou k-fold])
    V2([Calcular métricas])
    V2a[[FPR, TPR, AUC, Precision@k, Threshold]]
    V3{Métricas acima de limiares?}
    V4[(results_oneclass/evaluation_results.json)]:::dado
    V5[(results_oneclass/oneclass_confusion_matrix.png)]:::dado
    T4 --> V1 --> V2 --> V3
    V3 -- Sim --> V4 --> V5
    V3 -- Não --> V6[[Ajustar dados/parâmetros, retreinar]] --> T2
  end

  %% IMPLEMENTAÇÃO
  subgraph I[5) Implementação]
    direction TB
    I1([ensure_model_ready()])
    I2([Carregar modelo via common.paths.model_file()])
    I3([Vectorize e predict (core/run_model.py)])
    I4[[Integração com UI / APIs]]
    V4 --> I1 --> I2 --> I3 --> I4
  end

  %% MONITORAMENTO
  subgraph M[6) Monitoramento]
    direction TB
    M1([Logs e eventos de inferência])
    M2([Métricas contínuas])
    M2a[[Taxa de FP/FN, distribuição de confiança, latência]]
    M3{Drift ou degradação detectada?}
    M4[[Acionar retreinamento (pipeline auto)]]
    I3 --> M1 --> M2 --> M3
    M3 -- Sim --> M4 --> T1
    M3 -- Não --> M5[[Operação normal]]
  end

  %% Ferramentas
  F1[[Python 3.10, Pandas]]
  F2[[Scikit-learn / Joblib]]
  F3[[Mermaid (documentação), Unittest (testes)]]
  E --- F1
  P --- F1
  T --- F2
  V --- F2
  I --- F2
  M --- F3

  %% Critérios globais
  C1{{Qualidade mínima para avançar}}
  C1 --> E3
  C1 --> P3
  C1 --> V3
```

## Entradas e Saídas por Etapa
- Extração de Dados
  - Entradas: `dataset/Exercicios/Agachamento/*.csv`, `dataset/Exercicios/Terra/*.csv`
  - Saída: linhas combinadas (brutas) para pré-processamento
  - Ferramentas: Python 3.10, Pandas
  - Critérios: CSVs presentes, legíveis, colunas esperadas; logs sem erros críticos
  - Verificações: amostragem de linhas, validação de schema

- Pré-processamento
  - Entradas: linhas brutas combinadas
  - Saída: `dataset/processed_oneclass/correct_movements.parquet`
  - Ferramentas: Pandas
  - Critérios: colunas `exercise`, `label`, `video` presentes; deduplicação efetiva
  - Verificações: contagem de registros, proporção de duplicados removidos, tipos de dados

- Treinamento
  - Entradas: Parquet de features
  - Saídas: `models_oneclass/powerlifting_model.joblib`, `model/manifest.json`
  - Ferramentas: Scikit-learn, Joblib
  - Critérios: convergência do treinamento; parâmetros registrados; sem erros
  - Verificações: logs de treinamento, tamanho do modelo, versão das dependências

- Validação
  - Entradas: modelo treinado, conjunto de validação
  - Saídas: `results_oneclass/evaluation_results.json`, `results_oneclass/oneclass_confusion_matrix.png`
  - Ferramentas: Scikit-learn
  - Critérios: métricas acima de limiares; estabilidade das previsões
  - Verificações: análise de FPR/TPR, inspeção da matriz de confusão

- Implementação
  - Entradas: artefatos do modelo
  - Saídas: previsões integradas ao sistema (UI/API)
  - Ferramentas: `core/model_loader.py`, `core/run_model.py`
  - Critérios: `ensure_model_ready()` retorna ok; latência aceitável
  - Verificações: smoke test de previsão, validação no UI

- Monitoramento
  - Entradas: eventos e métricas de inferência
  - Saídas: alertas/ações de retreinamento quando necessário
  - Ferramentas: logs do app, testes automatizados
  - Critérios: limites para drift e erros; SLOs definidos
  - Verificações: revisão periódica, dashboards de métricas

## Legenda (Notação)
- `[Processo]` retângulo: atividade/ação
- `{Decisão}` losango: condição/critério
- `[/Entrada|Saída/]` paralelogramo: dados externos
- `[(Armazenamento)]` cilindro: arquivo/artefato persistente
- `[[Nota]]` retângulo duplo: anotação/informação

## Compartilhamento e Exportação
- Formato fonte: este arquivo (`docs/system_flow.md`) com diagrama Mermaid.
- Exportar para imagem/PDF:
  - VSCode: usar a extensão “Markdown Preview Mermaid Support” e exportar.
  - CLI: `npm i -g @mermaid-js/mermaid-cli` e executar `mmdc -i docs/system_flow.md -o system_flow.png`.
  - Alternativo: colar o bloco Mermaid em https://mermaid.live e exportar PNG/PDF.

## Observações
- O fluxo atual usa CSVs de features pré-gerados; se desejar extrair direto de vídeo, integrar um `tools/extract_features.py` moderno e ajustar a etapa 1 para produzir CSVs.
- Limiares de qualidade devem ser mantidos em `config/pipeline.json` ou documentação técnica, para reprodutibilidade.
