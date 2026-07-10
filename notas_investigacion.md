# Notas de investigación — Sistema Quant

Hipótesis y observaciones registradas para futuros ciclos de walk-forward.
**Regla:** nada de esto se aplica en producción durante una ventana de validación abierta.
Son preguntas a testear con rigor, no cambios a aplicar en caliente.

---

## 2026-07-03 — Calibración de umbrales: ¿BNB y SOL demasiado altos?

**Contexto.** El sistema llevaba días sin dar señales. Análisis de régimen mostró
que los activos están baratos en marco anual (percentil 365d medio ~7%) pero
rebotando en la última semana (+10-13% en 7d), por encima de sus MM20. Surgió la
duda de si el sistema "llega tarde a los suelos" por usar ventana corta.

**Qué se hizo.** Análisis retrospectivo (`analisis_suelos.py`): identificar suelos
del último año (caída >15% + mínimo local) y comprobar si el sistema dio señal
cerca de cada suelo, y con cuánto retraso.

**Resultado — la hipótesis del "retraso" queda DESCARTADA.**
Cuando el sistema da señal, la da temprano (día -1 a -3 vs el suelo), no tarde.
- ETH (umbral 4): capturó 7/7 suelos, todos anticipados.
- BTC (umbral 5): 3/3, todos en día -3.
- ADA (umbral 5): 5/6 con señal, casi todas anticipadas.

**Hallazgo real y distinto — calibración de umbrales.**
Los activos con umbral alto pierden suelos que el sistema SÍ detecta parcialmente:
- BNB (umbral 7): 0/3 suelos con señal. Mejor score en los tres fue 5-6. El
  sistema estuvo cerca pero el umbral 7 nunca se alcanzó.
- SOL (umbral 6): 3/6 sin señal, todos con mejor score 3-5.
- Contraste: ETH (umbral 4) captura todo.

**Pregunta de investigación para el próximo walk-forward:**
¿Los umbrales de BNB (7) y SOL (6) están demasiado altos? Capturan menos suelos
que ETH (4). Testear si bajarlos mejora el retorno ajustado por riesgo, O si el
umbral alto está filtrando señales falsas necesarias (ruido).

**Cautelas antes de tocar nada:**
1. Los umbrales salieron de optimización/walk-forward previos, no a dedo. El
   umbral alto de BNB puede existir para filtrar señales falsas que perdían dinero
   en otras partes del histórico. Este análisis solo ve un lado de la balanza
   (suelos perdidos), no las señales malas evitadas.
2. El análisis mira PRECIO, no rentabilidad. "Captó el suelo" ≠ "habría ganado":
   tras el suelo el activo debe subir hasta el take antes de tocar el stop. No medido.
3. NO tocar hasta cerrar la ventana de validación actual de Bitvavo (0/30 ops).

---

## 2026-07-06 — ¿Complementar mean-reversion con momentum?

**Contexto.** El sistema lleva ~5 días sin operar tras la migración a Bitvavo.
Los activos están en pleno rebote (scores negativos, RSI altos), y el sistema
mean-reversion no encuentra sobreventa. Esto genera periodos largos sin actividad
cuando el mercado está en tendencia alcista o rebotando con fuerza.

**Observación.** El sistema actual es mean-reversion puro: solo compra debilidad.
Eso implica un sesgo estructural a ciertos regímenes — funciona en mercados
laterales/volátiles (sobrerreacciones frecuentes), pero se queda completamente
fuera en tendencias alcistas sostenidas o rebotes fuertes.

**Pregunta de investigación para el futuro:**
¿Añadir una pata de momentum (comprar fuerza confirmada) complementaría el
sistema, cubriendo los regímenes donde mean-reversion no opera? Los sistemas
profesionales suelen combinar ambas filosofías con un filtro de régimen que
decide cuál activar.

**Posible ángulo para el TFG:** comparación sistemática mean-reversion vs momentum
vs combinación en cripto spot, con walk-forward y análisis de régimen. Tema
cuantitativo con aplicación directa al sistema real.

**Cautelas:**
1. NO tocar el sistema actual hasta cerrar la ventana de validación (0/30 ops).
2. Añadir momentum es un orden de magnitud más complejo que lo actual.
3. Explorar solo después de que mean-reversion tenga datos suficientes para
   evaluar si su edge sobrevive en producción real.

---

## Análisis de Régimen — 7 julio 2026

**Confirmación:** Sistema NO está roto. Régimen es adverso.

**Estado actual:**
- SOL/ETH: TRENDING UP fuerte + ARRIBA MA20 + OVERBOUGHT → mean-reversion muerta
- ADA/BNB/BTC: MIXTO — precios arriba MA20 pero sin tendencia clara

**Por qué no hay señales:**
- Mean-reversion busca sobreventa (RSI < 30, precio < MA20)
- Post-rebote (+10-13% últimos 7d): mercado está arriba, no abajo
- Kelly rolling 90d NEGATIVO en todos los activos

**Cuándo vuelve el edge:**
- Siguiente corrección significativa (precio < MA20 o RSI < 40)
- O inversión sostenida en MA20 slope

**Acción:** Vigilancia. No tocar parámetros hasta 30 ops de Bitvavo completadas.


## 8 julio 2026 — Bug corregido: Acumulación de posiciones BNB

Monitor_4h ejecutó dos compras BNB simultáneamente (mismo 4H):
- 1ª: €498.54 × 0.2006 = €100.00 (OCO protegida)
- 2ª: €493.52 × 0.1883 = €92.85 (sin protección)

Total expuesto: 0.3889 BNB = riesgo de liquidación si ambos stops se ejecutaban.

Acción tomada: Cerré manualmente la 2ª orden a mercado (€493.53, +€0.01).

FIX requerido: Bloquear monitor_4h para NO ejecutar nueva orden si activo ya tiene posición abierta.
Esto afecta también monitor_v2 (diario).


## 8 julio 2026 — Fix implementado: Validador de posiciones

Bug: monitor_4h ejecutó 3 compras BNB simultáneamente en el mismo día.
Causa: No validaba si el activo ya tenía posición abierta.

Fix: validador_posiciones.py + integrado en monitor_4h.py y monitor_v2.py.
Antes de ejecutar compra, chequea operaciones_reales.csv por posiciones sin fecha_cierre.
Si activo ya tiene posición abierta → SKIP + alerta Telegram.

Testado: BNB/EUR con posición abierta → correctamente bloqueado.


## 8 julio 2026 — Bugs detectados y corregidos (sesión completa)

### Bug 1: Acumulación de posiciones
Monitor_4h ejecutó 3 compras BNB simultáneamente.
FIX: validador_posiciones.py integrado en monitor_4h.py y monitor_v2.py.

### Bug 2: Cierres fantasma (evaluador_real.py)
Evaluador usaba fallback "sin IDs": si fetch_open_orders devuelve 0, cerraba.
Pero ccxt NO ve OCO manuales de Bitvavo → cerraba operaciones que siguen abiertas.
FIX: Fallback eliminado. Operaciones sin IDs requieren cierre manual.

### Bug 3: ccxt no ve OCO manuales de Bitvavo
API de Bitvavo no expone órdenes OCO colocadas desde la web.
Ejecutor.py coloca SL y TP como órdenes separadas (bloquean balance).
Bitvavo web coloca OCO vinculadas (comparten balance).
LIMITACION CONOCIDA: No hay fix por API. Operaciones futuras se colocan por ejecutor.py con IDs.

### Operación actual
BNB 0.2006 a €498.54 con OCO manual (SL €488.50 / TP €548.32).
Cuando se ejecute: actualizar CSV manualmente.

