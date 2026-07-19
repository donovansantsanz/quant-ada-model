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


## 13 julio 2026 — Análisis retrospectivo: 8 ops Binance (23-30 junio)

**Resultado:** 8 ops, 1 win, 7 losses. Win rate 12.5%. Retorno -8.49%.
Todas cerradas por stop loss. Ningún take profit alcanzado.

**Contexto:** Mercado en caída pre-MiCA (Binance suspendió EU 1 julio).
Período de 7 días con ventas sostenidas.

**Diagnóstico:** El sistema detectó sobreventa correctamente (scores altos),
pero el mercado NO rebotó — siguió cayendo. Mean-reversion en mercado en
caída libre genera señales falsas (bull traps).

**Implicación para hipótesis 2:** Confirma necesidad de filtro de régimen.
En régimen ADVERSO (caída sostenida), el sistema debería NO operar.
El detector de régimen actual habría clasificado este período como
ADVERSO (precio < MA20 + MA20 slope negativo).

**Dato clave:** Si el detector hubiera estado activo, las 8 ops se habrían
bloqueado → retorno 0% en vez de -8.49%.


## 14 julio 2026 — CORRECCIÓN: Backtest detector de régimen vs 8 ops Binance

**Afirmación anterior (13 julio):** "Si el detector hubiera estado activo,
las 8 ops se habrían bloqueado."

**INCORRECTO.** Backtest real muestra que el detector clasificó TODAS las
fechas como FAVORABLE o MIXTO. No habría bloqueado NINGUNA operación.

**Razón:** Durante el crash pre-MiCA, precios estaban DEBAJO de MA20 con
RSI bajo — exactamente las condiciones que el detector clasifica como
"favorables para mean-reversion." Pero el mercado siguió cayendo.

**Problema fundamental:** El detector actual distingue:
- ADVERSO: precio > MA20 + RSI > 50 + trending up (momentum alcista)
- FAVORABLE: precio < MA20 + RSI < 50 (sobreventa)

Pero NO distingue entre:
- Sobreventa CON rebote inminente (genuina mean-reversion)
- Sobreventa EN caída libre (bull trap)

**Hipótesis 3 — Detector de caída sostenida:**
Necesitamos un indicador adicional que mida VELOCIDAD de caída.
Posibles candidatos:
- Retorno acumulado últimos 7 días (si < -10%, mercado en caída libre)
- Pendiente de precio (no de MA20) — si precio cae más rápido que MA20
- Volatilidad expandida + RSI bajando = pánico, no sobreventa normal

NO implementar hasta cerrar validación actual.


## 16 julio 2026 — Validador de posiciones: primera intervención real

El validador bloqueó una señal COMPRAR de BNB/EUR (Score 7/6, RSI 29.6)
mientras la posición del 8 julio seguía abierta. Sin el fix, se habría
ejecutado una segunda compra duplicada (~€93) sin protección automática.

Fix validado en producción.


---

## Formalización académica — Hipótesis 3 (17 julio 2026)

### Pregunta de investigación

¿Es posible distinguir estadísticamente, en el momento de la señal, entre
sobreventa que precede a una reversión (mean-reversion genuina) y sobreventa
dentro de una tendencia bajista sostenida (falsa señal / bull trap)?

### Motivación empírica

El backtest del 14 julio mostró que el detector de régimen actual (basado en
posición vs MA20 + RSI) clasificó las 8 operaciones perdedoras del crash
pre-MiCA como FAVORABLES. Es decir: las condiciones que el sistema considera
óptimas para mean-reversion (precio < MA20, RSI bajo) estuvieron presentes
durante toda la caída. El indicador de nivel (¿está barato?) no distingue de
un indicador de velocidad (¿sigue cayendo con fuerza?).

### Marco teórico (referencias a revisar)

- Modelos de cambio de régimen (regime-switching): Hamilton (1989),
  Markov-switching models aplicados a series financieras.
- Literatura mean-reversion vs momentum: bajo qué condiciones cada estrategia
  domina (Moskowitz, Asness, etc.).
- Detección de rupturas estructurales (structural breaks) y su relación con
  el fin de un régimen de reversión.

### Hipótesis operativa

Añadir un indicador de VELOCIDAD de caída (no solo de nivel) al scoring mejora
la separación entre reversión genuina y trampa bajista. Candidatos a testear:
1. Retorno acumulado 7d (umbral de "caída libre", p.ej. < -10%)
2. Pendiente del precio vs pendiente de la MA20 (precio cae más rápido = peligro)
3. Volatilidad expandida + RSI descendente (pánico, no sobreventa normal)

### Diseño experimental propuesto

1. Etiquetar retrospectivamente cada señal histórica como "reversión genuina"
   (el precio subió al take antes de tocar el stop) o "falsa" (tocó el stop).
2. Para cada señal, calcular los 3 indicadores candidatos.
3. Evaluar poder discriminante (p. ej. AUC / separación de distribuciones)
   de cada indicador entre las dos clases.
4. Validar walk-forward: entrenar el umbral en un periodo, testear en otro.

### Cautela metodológica

Muestra actual insuficiente (9 ops cerradas). Este experimento requiere
acumular operaciones o usar señales históricas simuladas (con cuidado del
lookahead bias). NO implementar en producción hasta cerrar la ventana de
validación actual.

### Conexión con el TFG

Candidato directo a pregunta central del TFG:
"Detección de régimen para estrategias de reversión a la media en cripto:
comparación mean-reversion vs momentum vs híbrido con validación walk-forward."


---

## 18 julio 2026 — Hipótesis 4: ¿aporta valor el filtro BTC?

### Origen

Stress test ejecutado sobre periodos históricos (crash mayo 2021, bear market
2022, colapso FTX nov 2022, bull market 2023, mercado actual), comparando el
Sharpe del sistema con y sin filtro BTC activado.

### Resultado

Balance por activo (solo los que tienen el filtro ACTIVO en produccion):

| Activo | Periodos donde ayuda | Periodos donde perjudica |
|--------|---------------------|-------------------------|
| ADA    | 2                   | 2                       |
| ETH    | 3                   | 2                       |
| BNB    | 0                   | 4                       |

BNB es el caso extremo: el filtro perjudica en los 4 periodos medidos.
Peor caso: bull market 2023, Sharpe pasa de -2.54 a -10.94 (-8.40).

En el periodo "mercado actual" el filtro perjudica en 4 de 5 activos,
bloqueando entre 33 y 107 señales por activo.

### Pregunta de investigacion

El filtro BTC (bloquear señales si BTC cae >5% en 3 dias) tiene una logica
macro defendible: la correlacion en cripto hace que una caida de BTC arrastre
al resto. Pero empiricamente parece bloquear demasiadas señales buenas junto
con las malas.

¿Aporta el filtro valor neto, o su beneficio teorico (proteccion macro) no
compensa el coste de oportunidad de las señales perdidas?

### Sub-preguntas a testear

1. ¿Deberia desactivarse el filtro en BNB especificamente? (0/4 a favor)
2. ¿Es el umbral -5% en 3d demasiado agresivo? Testear -8%, -10%.
3. ¿Deberia el filtro reducir el sizing en vez de bloquear por completo?
4. Analisis condicional: de las señales bloqueadas, ¿que porcentaje habria
   terminado en stop vs en take? (el stress test solo mide el agregado)

### Cautelas metodologicas

1. Los Sharpe del stress test provienen del mismo motor de simulacion que
   produce valores optimistas (Sharpe 11-16 no son realistas en trading real).
   Comparar diferencias relativas, no valores absolutos.
2. El stress test mide Sharpe agregado. Un filtro puede empeorar el Sharpe y
   aun asi proteger de la ruina en el peor escenario (tail risk), lo cual no
   se captura aqui.
3. Precedente de la Hipotesis 3: una conclusion que parecia obvia resulto
   incorrecta al backtestearla. No asumir.

### Estado

NO TOCAR hasta cerrar la ventana de validacion actual (9/30 ops).


---

## 18 julio 2026 — Actualizacion Hipotesis 1: convergencia de evidencia sobre BNB

### Analisis de suelos re-ejecutado (datos Bitvavo/EUR)

Relacion umbral vs captura de suelos, casi perfectamente monotona:

| Activo | Umbral | Suelos captados | Tasa |
|--------|--------|-----------------|------|
| ETH    | 4      | 7/7             | 100% |
| BTC    | 5      | 3/3             | 100% |
| ADA    | 5      | 6/7             | 86%  |
| SOL    | 6      | 3/6             | 50%  |
| BNB    | 7      | 0/3             | 0%   |

BNB fallo los 3 suelos con scores de 5, 6 y 6. El sistema detecto las tres
oportunidades pero el umbral 7 las bloqueo por 1-2 puntos.

### Convergencia con Hipotesis 4

Dos analisis independientes apuntan a que la configuracion de BNB es
demasiado restrictiva:

1. Stress test: el filtro BTC perjudica a BNB en 4/4 periodos historicos
2. Analisis de suelos: el umbral 7 pierde 3/3 suelos

Es ademas el activo donde mas se opera (el sistema 4h es exclusivamente BNB).

### Hallazgo adicional: timing de las señales

Practicamente todas las señales caen en dia -3 respecto al suelo real.
El sistema no llega tarde: llega temprano y aguanta la caida restante.

Esto explica la alta frecuencia de stops: se entra antes de que la caida
termine, y un stop de 2-3% salta facilmente en esos 3 dias.

Conexion directa con Hipotesis 3: si se pudiera distinguir "quedan 3 dias
de caida" de "el suelo es hoy", el sistema mejoraria sustancialmente sin
tocar el scoring.

### Cautelas (se mantienen las del 3 julio)

1. Este analisis mide PRECIO, no rentabilidad. "Capto el suelo" != "habria
   ganado": tras el suelo el precio debe alcanzar el take antes que el stop.
2. El umbral 7 salio de grid search maximizando Sharpe. Puede existir
   precisamente para filtrar señales falsas costosas en otras partes del
   historico. Este analisis solo ve los suelos perdidos, no las trampas
   evitadas.
3. NO tocar hasta cerrar la ventana de validacion (9/30 ops).


### Matiz importante: los parametros de BNB estan acoplados

Configuracion completa (config.py):

| Activo | Umbral | Stop | Take | Kelly | Filtro BTC |
|--------|--------|------|------|-------|------------|
| ADA    | 5      | 3%   | 8%   | 16.9% | Activo     |
| SOL    | 6      | 3%   | 10%  | 23.1% | Inactivo   |
| ETH    | 4      | 3%   | 10%  | 18.3% | Activo     |
| BNB    | 7      | 2%   | 10%  | 28.4% | Activo     |
| BTC    | 5      | 2%   | 8%   | 15.1% | Inactivo   |

BNB es el activo mas restrictivo en tres frentes simultaneos: umbral mas alto
(7), stop mas ajustado (2%) y filtro BTC activo. Y es donde mas se opera
(el sistema 4h es exclusivamente BNB).

El ratio b de BNB es 5:1 (take 10% / stop 2%), el mas asimetrico del sistema.
Eso justifica su Kelly alto (28.4%): con esa asimetria se puede acertar poco
y seguir siendo rentable. Pero un stop del 2% en un activo volatil salta con
facilidad, especialmente dado que las señales llegan en dia -3 antes del suelo.

CAUTELA CRITICA para el proximo ciclo de walk-forward:
Estos parametros salieron de un grid search que optimizaba el CONJUNTO
(umbral + stop + take simultaneamente). El stop de 2% puede funcionar
precisamente PORQUE el umbral 7 filtra las señales mas dudosas. Bajar el
umbral sin reajustar el stop podria empeorar el resultado, no mejorarlo.

Al re-optimizar: probar combinaciones completas, nunca parametros sueltos.


---

## 19 julio 2026 — Marco teórico: Hipótesis 3 y literatura de detección de regímenes

### Contexto

La Hipótesis 3 busca distinguir sobreventa que precede a rebote (mean-reversion
genuina) de sobreventa en caída libre (bull trap). Esta pregunta tiene nombre
propio en la literatura: changepoint detection aplicado a régimen de mercado.

### Literatura relevante (por orden de prioridad)

**1. Hamilton (1989) — El fundacional**
Hamilton, J.D. (1989). A new approach to the economic analysis of nonstationary
time series and the business cycle. Econometrica 57, 357–384.

Introduce el modelo Markov-switching: el régimen (calma vs turbulencia) es una
variable OCULTA que no se observa directamente, pero puede inferirse
probabilísticamente de los precios. El sistema actual usa reglas fijas
(precio < MA20 + RSI < 50 = FAVORABLE). Un modelo Markov-switching estima
probabilidades continuas de estar en cada régimen, sin umbrales arbitrarios.

**2. Filardo (1994) — Probabilidades de transición variables en el tiempo (TVTP)**
Filardo, A.J. (1994). Business-cycle phases and their transitional dynamics.
Journal of Business & Economic Statistics 12, 299–308.

Extiende Hamilton permitiendo que la probabilidad de cambiar de régimen dependa
de variables observadas (covariables). Esto es exactamente la Hipótesis 3:
usar retorno 7d o pendiente del precio como variable que modula la probabilidad
de que el régimen cambie. El marco matemático ya existe.

**3. Wood, Roberts & Zohren (2021) — El más cercano al problema**
arXiv:2105.13727 — "Slow Momentum with Fast Reversion"

Insertan un módulo de detección de changepoints en una estrategia de momentum.
El módulo produce una PUNTUACION DE SEVERIDAD del cambio (no un sí/no),
mejorando el Sharpe en un tercio. El problema es análogo al nuestro con el
signo cambiado: ellos tienen momentum que falla en giros, nosotros tenemos
mean-reversion que falla en caída libre. LECTURA PRIORITARIA — acceso libre.

**4. Evidencia en cripto**
Literatura reciente muestra que en cripto, momentum domina en tendencias
alcistas de baja volatilidad, mientras mean-reversion resulta valiosa en
mercados de alta volatilidad y periodos de transición. El Sharpe realista
en trabajo publicado con estrategias combinadas es ~1.71 (no 8-11).

### Implicación práctica inmediata

statsmodels (Python) implementa MarkovRegression y MarkovAutoregression.
Se puede ajustar un modelo de dos regimenes a datos de BNB en pocas lineas
y comparar sus estados estimados con el clasificador actual (MA20 + RSI).
Esto seria un experimento real documentable para el TFG.

### Conexion con el TFG

El titulo candidato del TFG conecta directamente:
"Deteccion de regimen para estrategias de reversion a la media en cripto:
comparacion mean-reversion vs momentum vs hibrido con validacion walk-forward"

La seccion de estado del arte ya tiene base:
1. Hamilton (1989): modelos de cambio de regimen
2. Filardo (1994): TVTP — regimen dependiente de covariables
3. Wood et al. (2021): changepoint detection + estrategia adaptativa
4. Literatura cripto: comportamiento diferencial por regimen

### Siguiente paso (cuando se cierre la validacion actual)

Ajustar MarkovRegression de dos regimenes a datos historicos de BNB.
Comparar estados estimados con clasificacion actual.
¿Coinciden? ¿Mejora la separacion entre reversiones genuinas y trampas?

