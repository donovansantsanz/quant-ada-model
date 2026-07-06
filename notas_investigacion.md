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
