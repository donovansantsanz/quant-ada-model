# BUGS CONOCIDOS — Sistema Quant (pendientes de arreglar en frío)

Fecha de registro: 2026-06-30
Contexto: ambos bugs se manifestaron en el episodio del cron de las 10:30 del 30/06,
donde BTC se abrió, quedó desprotegida, y el evaluador la cerró por error.

Estado actual: ambos bugs documentados, sistema estabilizado. BTC abierta y
protegida manualmente. NO arreglar en caliente con operaciones parcheadas a mano.

---

## BUG 1 — Protección automática falla por latencia de saldo  [ARREGLADO 30/06, pendiente confirmar en operación real]

### Síntoma
Al abrir una operación, el ejecutor compra correctamente pero falla al colocar
las órdenes de protección (stop-limit + take-limit). Error de Binance:
`"Account has insufficient balance for requested action."`
Resultado: posición abierta y DESPROTEGIDA hasta intervención manual.

### Causa raíz
Latencia entre la ejecución de la compra y la actualización del saldo disponible
en Binance. El ejecutor intenta colocar la orden de venta (protección) milisegundos
después de la compra de mercado, antes de que Binance haya registrado el activo
comprado como disponible para vender. No es un problema de cantidad ni de fees
(se confirmó que las fees se cobran en BNB, no en el activo comprado).

### Evidencia
- 30/06 BTC: compra OK a $59,300, protección falló por "insufficient balance"
- 28/06 BNB: mismo patrón ("OCO MANUAL" / protección manual requerida)
- Intermitente: depende del timing de asentamiento del saldo

### Solución propuesta
En `ejecutor.py`, función `ejecutar_compra`, entre la compra de mercado y la
llamada a `colocar_ordenes_proteccion`:
1. Añadir un retardo de 1-2 segundos (`time.sleep(2)`) para dar tiempo al saldo
   a asentarse, O MEJOR:
2. Implementar reintento: si `colocar_ordenes_proteccion` falla por balance,
   esperar 2s y reintentar hasta 3 veces antes de caer al fallback manual.
3. Opción adicional: usar la cantidad REAL disponible (`fetch_balance`) en lugar
   de la cantidad teórica comprada, para evitar discrepancias de redondeo.

### Riesgo del arreglo: BAJO
Solo añade robustez, no cambia lógica de decisión. Se puede probar en testnet.

---

## BUG 2 — Evaluador empareja órdenes por símbolo, no por ID (vulnerable a zombis)

### Síntoma
El evaluador cierra por error una operación que está realmente abierta, si existe
una orden colgada ("zombi") de una operación anterior del mismo activo.
Resultado: operación viva marcada como cerrada en el CSV, con precio de cierre
incorrecto tomado del historial de la operación antigua.

### Causa raíz
La lógica del evaluador cuenta órdenes por símbolo:
- 0 órdenes → posición cerrada
- 1 orden → una protección se ejecutó, la otra es huérfana → CERRAR
- 2 órdenes → posición activa

El problema: no distingue entre las órdenes de la operación ACTUAL y las sobras
de operaciones pasadas del mismo activo. Si queda 1 orden zombi de una operación
vieja, y se abre una operación nueva, el evaluador ve "1 orden" y cierra la nueva
por error.

### Evidencia
- 30/06: BTC nueva (entrada $59,300) cerrada por error como stop_loss -1.30%
  usando el precio de cierre de la operación ANTIGUA ($58,529 del 26/06).
  La culpa: una orden zombi del take profit del 26/06 nunca cancelada.

### Solución propuesta
En `evaluador_real.py`, usar los IDs de órdenes guardados en el CSV
(`orden_stop_id`, `orden_take_id`) en lugar de contar órdenes por símbolo:
1. Para cada operación abierta, comprobar el estado de SUS órdenes por ID
   (`fetch_order(stop_id)` y `fetch_order(take_id)`).
2. Decidir el cierre según el estado de esas órdenes específicas:
   - Ambas abiertas → posición activa (trailing)
   - Una ejecutada (`closed/filled`) → posición cerrada, cancelar la otra por ID
   - Ambas canceladas/inexistentes → revisar manualmente
3. Ignorar cualquier orden del símbolo que NO esté en los IDs de la operación
   (esas son zombis de operaciones pasadas, no afectan a la actual).

### Prerequisito (YA HECHO)
- Columnas `orden_stop_id` y `orden_take_id` existen en el CSV ✅
- BTC del 30/06 ya tiene sus IDs registrados (9719290827 / 9719290828) ✅
- Operaciones antiguas (pre-IDs) tienen estas columnas vacías → el evaluador
  debe manejar el caso de IDs vacíos (fallback al método actual para esas).

### Riesgo del arreglo: MEDIO
Toca la lógica central del evaluador que corre cada hora sobre dinero real.
Requiere probar con cuidado. Arreglar SOLO en frío, sin operaciones recién
parcheadas a mano.

---

## ORDEN DE ARREGLO RECOMENDADO

1. **BUG 1 primero** (riesgo bajo, alto impacto): sin protección automática
   fiable, cada operación nueva requiere intervención manual. Es lo que más
   fricción genera ahora mismo.
2. **BUG 2 después** (riesgo medio): una vez el ejecutor cancele limpiamente y
   registre IDs siempre, el evaluador puede emparejar por ID con seguridad.

## NOTA DE PROCESO
Ambos bugs se manifestaron porque los despliegues por scp no siempre
sobrescribieron los archivos del servidor (pasó con ejecutor y evaluador).
LECCIÓN: tras cada `scp`, verificar SIEMPRE en el servidor con `grep` que la
versión nueva llegó, antes de confiar en ella.
