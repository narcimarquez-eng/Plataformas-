# Plataformas-
Juego plataformas

## Juego

Abre `plataformas_nuevo.html` en el navegador (necesita conexión para cargar three.js y cannon-es desde unpkg).

**Teclado**
- ← → / A D: mover
- ↑ / W / Espacio: saltar (Narci puede saltar dos veces)
- Z / J: disparar
- Shift / X: esquivar
- B / E: colocar bloque
- F: pescar (solo Miguel)
- P / Esc: pausa (se pausa sola al cambiar de pestaña)

**Pantalla táctil**: gira la ruleta de la izquierda para avanzar (cuanto más giras, más rápido; al soltarla vuelve al centro), botones para saltar y actuar, arrastrar para girar la cámara, rueda o pellizco para el zoom.

## Optimizar modelos

Los modelos `.glb` se optimizan con Blender (`tools/optimizar_glb.py`):

```
blender -b -P tools/optimizar_glb.py -- gltf3 gltf3_optimizado
```

El script reduce a la mitad las mallas grandes sin nombre y conserva los nodos con nombre,
porque el juego anima partes por nombre (`head`, `wingL`, `legL`...). Antes de sustituir
los modelos, comprueba que los nodos con nombre no cambian de posición.
