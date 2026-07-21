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


---

## 19 julio 2026 — Experimento 1: Markov-Switching en BNB/EUR

### Setup

Modelo: MarkovRegression (statsmodels) con 2 regímenes y varianza variable.
Datos: 364 días BNB/EUR (2025-07-21 → 2026-07-19).
Variable modelada: retornos logarítmicos diarios.

### Regímenes detectados

| Régimen | Retorno anualizado | Volatilidad anual | Persistencia |
|---------|-------------------|-------------------|--------------|
| 0 (CALMA) | +2.3% | 26.9% | 96.0% |
| 1 (TURBULENTO) | -95.2% | 77.3% | 85.1% |

El régimen CALMA es muy persistente (96%) — una vez en calma, tiende a quedarse.
El régimen TURBULENTO es menos persistente (85%) — los crashes son intensos pero acaban.

### Hallazgo 1: acuerdo con clasificador actual = 48.7%

El clasificador actual (precio < MA20 + RSI < 50) y el modelo Markov
acuerdan solo el 48.7% de los dias. Practicamente aleatorio.
Interpretacion: miden cosas distintas. Son potencialmente COMPLEMENTARIOS,
no redundantes. Un clasificador combinado podria ser mas robusto.

### Hallazgo 2: señales de enero 2026 (el caso clave)

Señales COMPRAR de BNB durante el crash de enero 2026:

| Fecha | Precio | P(turbulento) |
|-------|--------|---------------|
| 2026-01-25 | €729 | 5% (CALMA) |
| 2026-01-29 | €725 | 52% (TURBUL) |
| 2026-01-31 | €660 | 100% (TURBUL) |
| 2026-02-03 | €638 | 98% (TURBUL) |

El modelo detecto el cambio de regimen ANTES de que el precio colapsara:
ya el 29 de enero daba 52% de turbulento. El precio cayo -12.5% en esa
ventana. El clasificador actual habria dado COMPRAR todo el periodo.

Comparacion: señales de noviembre 2025 (CALMA 86-92%) y abril 2026 (CALMA
92%) — contextos donde la mean-reversion habria funcionado mejor.

### Conclusion preliminar

El modelo Markov SI distingue los dos casos de la Hipotesis 3:
- Señales en CALMA → contexto donde mean-reversion tiende a funcionar
- Señales en TURBULENTO → caida libre, bull trap probable

Esto responde afirmativamente la pregunta principal de la Hipotesis 3.

### Cautela critica: sesgo de retrospectiva (look-ahead bias)

Este experimento ajusta el modelo sobre TODOS los datos antes de clasificar.
En produccion real, el modelo solo veria el pasado. La señal de turbulencia
de enero puede llegar en retrospectiva mas clara que en tiempo real.

SIGUIENTE PASO: re-ejecutar en modo rolling (ajustar el modelo solo con
datos hasta el dia i, predecir el regimen del dia i+1). Si la señal de
turbulencia de enero sigue apareciendo en tiempo real, el resultado es
robusto. Si desaparece, era retrospectiva.

### Implicacion para el sistema (futura, post-validacion)

Añadir como filtro adicional: si P(turbulento) > umbral (ej. 40%), no
ejecutar señal aunque el score llegue al umbral. Testear en walk-forward
antes de implementar en produccion.

### Archivo

Script: ~/proyectos-quant/experimento_markov_bnb.py


---

## 20 julio 2026 — Experimento 2: Markov Rolling (sin lookahead bias)

### Setup

Mismo modelo que Experimento 1 pero en modo rolling:
en cada dia i, el modelo se ajusta solo con datos hasta i-1.
Ventana minima: 90 dias. Predice regimen del dia i sin ver el futuro.

### Resultado principal: el modelo rolling llega TARDE

Comparacion caso clave enero 2026:

| Fecha | Precio | P(turb) retrospectivo | P(turb) rolling |
|-------|--------|-----------------------|-----------------|
| 2026-01-25 | €729 | 5% CALMA | 5% CALMA |
| 2026-01-29 | €725 | 52% TURBUL | 4% CALMA |
| 2026-01-31 | €660 | 100% TURBUL | 8% CALMA |
| 2026-02-01 | €640 | 100% TURBUL | 100% TURBUL |

El modelo retrospectivo detecta el cambio el 29 enero.
El rolling lo detecta el 1 febrero — cuando el precio ya cayo -12%.

### Explicacion

El modelo necesita observar varios dias de alta volatilidad para actualizar
su estimacion del regimen. Un solo dia de caida parece ruido. La señal
llega despues del crash, no antes ni durante.

### Conclusion: resultado negativo pero informativo

El Markov-switching puro sobre retornos NO sirve como filtro en tiempo real
para este problema. Detecta el regimen turbulento retrospectivamente pero
no en tiempo util para evitar entrar en la trampa.

### Siguientes experimentos a probar (post-validacion)

1. Usar volatilidad realizada (rolling std 5d) en vez de retornos — la
   volatilidad explota antes de que el precio colapse del todo
2. Ventana mas corta (30-60 dias) — mas reactivo, menos estable
3. Variables adicionales: retorno acumulado 7d (Hipotesis 3 original)
4. Modelo hibrido: Markov + indicador de velocidad de caida

### Valor del experimento

Resultado negativo que cierra una via y abre tres nuevas.
Es investigacion honesta: saber que NO funciona es tan valioso como
saber que SI funciona. Citable en TFG como experimento con resultado nulo.

### Archivos

Script: ~/proyectos-quant/experimento_markov_rolling.py


---

## 20 julio 2026 — Experimento 3: Velocidad de caida como filtro

### Setup

Dos indicadores de velocidad de caida calculados en tiempo real:
- ret7d: retorno acumulado ultimos 7 dias
- vol5d_pct: percentil historico de la volatilidad rolling 5 dias

Ambos calculables sin lookahead bias.

### Resultado principal: FUNCIONA en tiempo real

A diferencia del Markov rolling (Experimento 2), estos indicadores
detectan el cambio de regimen SIN necesitar datos futuros.

Caso clave enero 2026:

| Fecha | Precio | ret7d | vol5d_pct | Decision |
|-------|--------|-------|-----------|---------|
| 2026-01-25 | €729 | -9.0% | 19% | ✅ pasaria |
| 2026-01-29 | €725 | -3.9% | 70% | ✅ pasaria |
| 2026-01-31 | €660 | -11.9% | 88% | BLOQUEADO |
| 2026-02-01 | €640 | -12.2% | 86% | BLOQUEADO |
| 2026-02-03 | €638 | -14.7% | 89% | BLOQUEADO |

### Impacto de los filtros (sobre 17 señales historicas)

ret7d < -10%: bloquea 4/17 (24%) — solo señales en caida acelerada
vol5d > p80:  bloquea 4/17 (24%) — exactamente las mismas 4 señales

Los filtros son concordantes: identifican el mismo subconjunto de señales.

### Discriminacion correcta

Las señales de noviembre 2025 (ret7d -1.5% a -9.8%) NO son bloqueadas.
BNB estaba cayendo pero moderadamente — y eventualmente reboto.
El filtro deja pasar caidas moderadas y bloquea caidas aceleradas.
Eso es exactamente la discriminacion buscada en la Hipotesis 3.

### Conclusion

Los indicadores simples de velocidad de caida superan al modelo
Markov-switching en tiempo real. Mas simples, mas reactivos,
mas interpretables.

Umbrales candidatos para walk-forward:
- ret7d < -10% (bloquea 24% de señales, todas en caida libre)
- vol5d > p80  (mismo efecto, confirmacion cruzada)
- Combinacion: bloquear si AMBOS se activan (reduce falsos positivos)

### Jerarquia de los 3 experimentos

1. Markov retrospectivo: detecta turbulencia (solo en retrospectiva)
2. Markov rolling: llega tarde (12% ya perdido antes de detectar)
3. Velocidad de caida: FUNCIONA en tiempo real — GANADOR

### Siguiente paso

Validar en walk-forward formal:
- Periodo train: definir umbrales optimos (ret7d, vol5d)
- Periodo test: comprobar que la mejora se mantiene fuera de muestra
- Metrica: Sharpe con filtro vs sin filtro, operaciones bloqueadas correctamente

NO implementar en produccion hasta cerrar validacion actual (10/30 ops).

### Archivo

Script: ~/proyectos-quant/experimento_velocidad_caida.py


---

## 20 julio 2026 — Experimento 4: Walk-Forward del filtro (resultado final)

### Setup

Train: jul-oct 2025 (103 dias)
Test: nov 2025 - feb 2026 (120 dias, periodo con señales reales)

### Resultado: el filtro NO mejora fuera de muestra

En el periodo de test, TODAS las 16 operaciones terminaron en STOP -2%.
Sin excepcion. El filtro (vol5d > p70) bloqueo 8 señales, pero tanto las
bloqueadas como las no bloqueadas habrian terminado en stop.

El Sharpe -999 en el test con filtro se debe a que las 8 operaciones
restantes tienen todas el mismo retorno (-2%), std = 0.

### Causa raiz

Entre nov 2025 y feb 2026, BNB cayo de €826 a €638 (-23%) de forma
sostenida. No hubo ningun rebote que alcanzara el take profit (+10%).
El sistema detecto sobreventa correctamente, pero el mercado siguio
cayendo mas alla del stop antes de recuperarse.

El filtro de velocidad de caida no resuelve este problema:
- Bloquea señales en caida rapida ✅ (jan-feb 2026)
- Pero deja pasar señales en caida moderada que tambien son stops ❌ (nov 2025)
- En caidas sostenidas del -23%, el stop de 2% es demasiado ajustado

### Conclusion del ciclo de 4 experimentos (Hipotesis 3)

| Experimento | Resultado |
|-------------|-----------|
| 1: Markov retrospectivo | Detecta turbulencia ✅ (solo retrospectiva) |
| 2: Markov rolling | Llega tarde ❌ |
| 3: Velocidad de caida | Discrimina en muestra ✅ |
| 4: Walk-forward filtro | No mejora fuera de muestra ❌ |

### Reformulacion de la Hipotesis 3

El problema no es solo CUANDO entrar (filtrar señales) sino COMO salir.
En caidas sostenidas del 20%+, un stop del 2% no sobrevive el camino
hasta el rebote. La hipotesis deberia incluir:

1. Filtro de entrada (velocidad de caida) — probado, resultado mixto
2. Stop adaptativo (mas amplio en regimenes de alta volatilidad)
3. O directamente no operar en regimenes de caida sostenida

Conecta con Hipotesis 2 (momentum + detector de regimen):
si el detector clasifica CAIDA SOSTENIDA, la accion correcta puede ser
no operar en absoluto, no filtrar señales individuales.

### Valor de investigacion

4 experimentos con resultados mixtos: 2 positivos en muestra, 2 negativos
fuera de muestra. Es investigacion honesta. El camino hacia una solucion
robusta requiere abordar simultaneamente entrada Y gestion de la salida.


---

## 20 julio 2026 — Experimento 5: Stop adaptativo (cierre Hipotesis 3)

### Setup

Comparacion stop fijo (2%) vs stop adaptativo basado en:
- Volatilidad rolling 14d (vol14d × multiplicador)
- ATR × multiplicador

### Resultado año completo

| Config | Sharpe | Win% |
|--------|--------|------|
| Stop fijo 2% | 7.15 | 43.3% |
| ATR × 1.5 | 8.10 | 53.7% |
| Vol14d × 1.5 | 7.99 | 56.7% |

Mejora marginal con stop adaptativo en el año completo.

### Resultado periodo problematico (nov 2025 - feb 2026)

| Config | Sharpe |
|--------|--------|
| Stop fijo 2% | -7.25 |
| Vol14d × 1.5 | -11.73 (peor) |
| Vol14d × 3.0 | -15.92 (aun peor) |

Cuanto mas amplio el stop, peor el resultado. El stop adaptativo
EMPEORA el resultado en el peor regimen.

### Hallazgo definitivo: el take profit era inalcanzable

Analisis de caidas maximas en nov 2025:

| Señal | Caida max | Subida max | Take |
|-------|-----------|------------|------|
| 11 nov €827 | -13.5% | +0.0% | NUNCA |
| 12 nov €822 | -13.1% | +0.0% | NUNCA |
| 14 nov €786 | -9.1% | +2.4% | NUNCA |
| 21 nov €721 | -1.8% | +9.7% | NUNCA |

Las señales del 11-17 nov NUNCA subieron +10% desde el punto de
entrada. Ni con stop infinito habrian ganado: el precio no subio.

### Conclusion del ciclo completo (Hipotesis 3, 5 experimentos)

El sistema tiene un problema estructural en caidas sostenidas del 20%+:
ni el filtro de entrada (Exp 3-4) ni el stop adaptativo (Exp 5)
resuelven el problema porque el take profit es inalcanzable.

La unica solucion para ese regimen es NO OPERAR.
Detectar "caida sostenida" y pausar el sistema hasta que el regimen cambie.

Esto conecta con Hipotesis 2: el detector de regimen no debe solo
FILTRAR señales sino PAUSAR el sistema completo en regimenes adversos.

La distincion es importante:
- Filtrar señales: el sistema sigue mirando, solo opera selectivamente
- Pausar el sistema: no se genera ninguna señal hasta que el regimen cambie

### Valor academico

5 experimentos que empezaron buscando un filtro de entrada y terminaron
descubriendo que el problema es la arquitectura de salida y la deteccion
de regimen. Es un arco de investigacion completo con conclusion no obvia.


---

## 20 julio 2026 — Experimento 3b: Velocidad de caida en ETH/EUR

### Motivacion

Los Experimentos 3-5 se centraron exclusivamente en BNB. Para saber si
las conclusiones generalizan, se replico el analisis en ETH/EUR.

### Parametros ETH vs BNB

| | BNB | ETH |
|---|---|---|
| Umbral | 7 | 4 |
| Stop | 2% | 3% |
| Take | 10% | 10% |

### Resultado: el filtro SI mejora en ETH (ano completo)

| Filtro | Sharpe | Ops |
|--------|--------|-----|
| Sin filtro | 2.18 | 142 |
| ret7d < -10% | 2.61 | 99 |
| vol5d > p80 | 3.02 | 100 |

El filtro de velocidad de caida MEJORA el Sharpe en ETH.
Contraste directo con BNB donde no mejoraba fuera de muestra.

### Por que ETH reacciona diferente

1. Stop mas amplio (3% vs 2%): ETH sobrevive mejor la volatilidad
   antes de tocar el stop. El filtro puede discriminar porque hay
   operaciones que sobreviven y operaciones que no.

2. Umbral mas bajo (4 vs 7): ETH genera 142 señales vs 67 de BNB.
   Mayor variedad de condiciones — algunas en caida libre (alertas
   altas) y otras en correcciones normales (sin alertas). El filtro
   separa mejor los dos grupos.

3. En BNB con umbral 7, todas las señales son en extremos maximos —
   condiciones similares, todas terminan en stop en caidas sostenidas.

### Conclusion general (BNB + ETH)

La efectividad del filtro de velocidad de caida depende de:
1. La amplitud del stop (mas amplio = mas margen para discriminar)
2. La variedad de condiciones que genera el umbral (mas bajo = mas variedad)

ETH con stop 3% y umbral 4 responde bien al filtro.
BNB con stop 2% y umbral 7 no responde (todas stops en caidas sostenidas).

Implicacion para el TFG: la Hipotesis 3 no tiene una respuesta universal.
La solucion optima depende de los parametros especificos de cada activo.
Esto añade riqueza al analisis comparativo.

### Pendiente

Replicar en ADA (umbral 5, stop 3%) y SOL (umbral 6, stop 3%) para
completar el cuadro. Especialmente ADA que capto 6/7 suelos.


---

## 20 julio 2026 — Experimento 3c: ADA y SOL (cuadro completo)

### Resultados ADA/EUR (umbral=5, stop=3%, take=8%)

| Filtro | Sharpe | Ops |
|--------|--------|-----|
| Sin filtro | 1.11 | 105 |
| ret7d < -5% | -0.83 | 40 |
| vol5d > p70 | 1.21 | 65 |
| vol5d > p80 | 1.21 | 78 |

ret7d empeora claramente. vol5d mejora marginalmente.

### Resultados SOL/EUR (umbral=6, stop=3%, take=10%)

| Filtro | Sharpe | Ops |
|--------|--------|-----|
| Sin filtro | 4.55 | 87 |
| ret7d < -10% | 4.34 | 58 |
| vol5d > p70 | 6.79 | 41 |
| vol5d > p80 | 5.89 | 56 |

vol5d > p70 mejora sustancialmente: 4.55 → 6.79 (+2.24).
La mayor mejora absoluta de los 4 activos.

### Cuadro comparativo final (4 activos)

| Activo | Umbral | Stop | Sharpe_base | vol5d_p70 | vol5d_p80 | ret7d_10% |
|--------|--------|------|-------------|-----------|-----------|-----------|
| BNB | 7 | 2% | 7.15 | empeora | empeora | empeora |
| ETH | 4 | 3% | 2.18 | +0.64 | +0.84 | +0.43 |
| ADA | 5 | 3% | 1.11 | +0.10 | +0.10 | empeora |
| SOL | 6 | 3% | 4.55 | **+2.24** | +1.34 | empeora |

### Patron emergente

1. vol5d mejora en 3/4 activos (ETH, SOL, ADA marginalmente)
2. ret7d empeora en 3/4 activos (solo ETH mejora)
3. BNB es el unico donde ambos filtros perjudican
4. La mayor mejora es SOL con vol5d > p70 (+2.24 Sharpe)

### Interpretacion

El filtro vol5d captura bien los momentos de panico extremo.
En activos con stop 3% hay suficiente margen para sobrevivir
la volatilidad inicial y beneficiarse de la discriminacion.
En BNB con stop 2%, el stop salta antes de que el filtro ayude.

La efectividad del filtro depende principalmente de:
- Stop amplio (3%) > Stop ajustado (2%)
- No depende linealmente del umbral

### Conclusion de la Hipotesis 3 (ciclo completo)

Tras 6 experimentos (3, 3b, 3c, 4, 4b, 5):

El filtro de volatilidad (vol5d > p70-80) es el candidato mas robusto.
Mejora en 3/4 activos en muestra. Pendiente validacion walk-forward
por activo antes de implementar en produccion.

BNB necesita tratamiento especial: su stop de 2% lo hace incompatible
con el filtro de volatilidad. La solucion para BNB puede ser diferente
(ampliar stop, bajar umbral, o pausar en regimenes adversos).


---

## 21 julio 2026 — Punto de control (pre-viaje)

### Estado del sistema

- Operaciones cerradas: 9/30 (validacion en curso)
- Operacion abierta: BNB/EUR €493.33, stop trailing €495.43 (+0.4%)
- Capital: €193 aprox
- Bugs resueltos: validador posiciones, evaluador fantasma, trailing alert
- Paper trading paralelo activo: registra señales con/sin filtro vol5d

### Estado de la investigacion (Hipotesis)

**H1 — Calibracion umbrales BNB/SOL**
Documentada. BNB 0/3 suelos, umbral demasiado alto.
Pendiente: walk-forward formal post-validacion.

**H2 — Momentum + detector de regimen**
Documentada. Idea: pausar sistema en regimen adverso (no solo filtrar).
Pendiente: implementacion post-validacion.

**H3 — Deteccion caida sostenida (CERRADA)**
6 experimentos completados:
- Markov retrospectivo detecta turbulencia (solo en retrospectiva)
- Markov rolling llega tarde
- vol5d > p70 mejora en 3/4 activos en muestra
- Walk-forward: no mejora OOS en BNB (stop 2% incompatible)
- Stop adaptativo no resuelve el problema (take inalcanzable)
- ETH/SOL responden mejor al filtro (stop 3% mas amplio)
Conclusion: problema es arquitectura de salida + pausar sistema en regimen adverso

**H4 — Filtro BTC (valor real?)**
Documentada. Perjudica BNB en 4/4 periodos.
Pendiente: walk-forward formal post-validacion.

### Proximos pasos (vuelta del viaje)

1. Crear cuenta nueva X (@donovan_quant) con estrategia clara
2. Acumular operaciones reales (objetivo: 30 cerradas)
3. Walk-forward formal H1 y H4 cuando haya suficientes datos
4. Implementar H2 (pausar sistema) post-validacion
5. Septiembre: retomar contacto con profesores ULL

### Literatura pendiente de leer

- Wood, Roberts & Zohren (arXiv 2105.13727) — Slow Momentum + CPD
- Hamilton (1989) — Econometrica 57
- Filardo (1994) — TVTP

