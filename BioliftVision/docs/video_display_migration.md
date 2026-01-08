# Migração para nova label de exibição de vídeo

Este documento registra a análise do problema de cortes em vídeos (especialmente retrato) e a implementação de uma nova label independente para exibição, evitando herança e vínculos da label original.

## 1) Onde e quando ocorriam os cortes
- O corte era observado quando `cv2.resize` redimensionava o frame diretamente para `target_w x target_h` sem aplicar letterbox/pillarbox.
- Na UI, `_resize_video_area` limitava a altura útil do vídeo, reservando espaço para controles, o que penalizava vídeos com razão `w/h` baixa (retrato).
- Renderização e eventos estavam acoplados à `video_label` (mesmo container), herdeando estilo e dimensões durante mudanças de layout.

Locais principais identificados em `ui/interface.py`:
- `_resize_video_area`: linhas ~3038–3072 (limites e estilo da label).
- `_seek_to_frame` e `_update_frame`: linhas ~3460–3595 (uso de `cv2.resize`, `setPixmap`, `size`).
- `_fit_frame_to_label`: função criada para encaixe proporcional com padding.

## 2) Nova label independente
- Criada `self.video_display` (`QLabel`) com `objectName: videoDisplay` e `setScaledContents(False)`.
- A label original `self.video_label` foi mantida oculta (`setVisible(False)`) para compatibilidade, sem uso na renderização principal.
- A nova label é adicionada ao `video_layout`, não herda propriedades da antiga.

Arquivos modificados:
- `ui/interface.py`
  - Criação e configuração de `self.video_display` (substitui visualmente `self.video_label`).
  - Eventos de clique e mapeamento (`_on_video_click`) passam a usar `video_display`.
  - `~_resize_video_area`: aplica `setFixedSize` e `setStyleSheet` em `video_display`.
  - `_fit_frame_to_label`: utiliza dimensões da `video_display` para cálculo de padding.
  - `_seek_to_frame` e `_update_frame`: definem `pixmap` e `scaled` direcionando à `video_display`.
  - `_capture_frame`: salva a imagem exibida a partir de `video_display`.

## 3) Parâmetros e garantias de independência
- Estilo: aplicado diretamente em `video_display`, incluindo `background-color`, `border` e `border-radius`.
- Dimensões: todos cálculos de `width/height/size` referenciam `video_display` quando presente.
- Eventos: `mousePressEvent` da nova label aponta para `_on_video_click` e o cálculo usa `video_display.width/height`.
- Compatibilidade: a label antiga continua disponível somente como fallback explícito, nunca como fonte primária.

## 4) Testes e validação
### Cenários
- Vídeo retrato (ex.: 1080x1920).
- Vídeo paisagem (ex.: 1920x1080).
- Redimensionamento da janela e alternância de tela cheia.
- Pausar/retomar, seek, snapshot.

### Resultados
- Independência: `video_display` funciona isolada; alterações na label antiga não afetam a exibição.
- Qualidade sem cortes: frames são encaixados via `_fit_frame_to_label` com letterbox/pillarbox; não há distorção ou crop.
- Compatibilidade: player, sliders e botões continuam operacionais; snapshots usam `video_display`.

## 5) Observações finais
- Para cenários com UI mais estreita, `_resize_video_area` foi ajustado para liberar maior altura em modo retrato.
- Caso necessário, o `objectName` facilita aplicar estilos específicos via QSS.

## 6) Referência rápida (diff lógico)
- `self.video_label` → oculta; mantida para fallback.
- Nova: `self.video_display` adicionada ao layout; todos `setPixmap`, `size`, `width/height` e eventos direcionados para ela.
- Novo utilitário: `_fit_frame_to_label(frame)` para preservar proporção com padding.