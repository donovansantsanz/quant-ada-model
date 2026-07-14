import os
import pandas as pd
from datetime import datetime, timezone

ARCHIVO = '/root/proyectos-quant/operaciones_reales.csv'

# ── CRITERIOS DE EXPANSIÓN ───────────────────────────────────────
MIN_OPERACIONES_CERRADAS = 30
MIN_WIN_RATE = 0.30
TOLERANCIA_BACKTEST = 0.15
WIN_RATE_BACKTEST = 0.42
MIN_RETORNO_ACUMULADO = 0.0

ahora = datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')
print("=" * 64)
print(f"  CHECKLIST DE EXPANSIÓN — Quant Trading System")
print(f"  {ahora}")
print("=" * 64)

if not os.path.exists(ARCHIVO):
    print("\n  No hay operaciones registradas")
    exit()

df = pd.read_csv(ARCHIVO)
# Ventana de validacion: SOLO operaciones de Bitvavo (las de Binance son otra poblacion)
if 'venue' not in df.columns:
    df['venue'] = 'binance'
df['venue'] = df['venue'].fillna('binance')
# Contar todas las operaciones (Binance + Bitvavo)
cerradas = df[df['resultado'].notna() & (df['resultado'] != '') & (df['resultado'] != 'cerrado_manual')].copy()
abiertas = df[df['resultado'].isna() | (df['resultado'] == '')]

n_cerradas = len(cerradas)
print(f"\n  Operaciones cerradas: {n_cerradas}")
print(f"  Operaciones abiertas: {len(abiertas)}")

if n_cerradas == 0:
    print("\n  Sin operaciones cerradas — imposible evaluar todavía")
    print("=" * 64)
    exit()

cerradas['retorno_pct'] = cerradas['retorno_pct'].astype(float)
aciertos = (cerradas['retorno_pct'] > 0).sum()
win_rate_real = aciertos / n_cerradas
retorno_acumulado = cerradas['retorno_pct'].sum()
retorno_medio = cerradas['retorno_pct'].mean()

print(f"\n  ── METRICAS REALES ──")
print(f"  Win rate real:        {win_rate_real*100:.1f}%")
print(f"  Win rate backtest:    {WIN_RATE_BACKTEST*100:.1f}%")
print(f"  Retorno acumulado:    {retorno_acumulado:+.2f}%")
print(f"  Retorno medio/trade:  {retorno_medio:+.2f}%")

print(f"\n  ── CRITERIOS DE EXPANSION ──")
criterios = []

c1 = n_cerradas >= MIN_OPERACIONES_CERRADAS
criterios.append(c1)
print(f"  {'OK' if c1 else 'NO'} Volumen: {n_cerradas}/{MIN_OPERACIONES_CERRADAS} operaciones cerradas")

c2 = win_rate_real >= MIN_WIN_RATE
criterios.append(c2)
print(f"  {'OK' if c2 else 'NO'} Win rate minimo: {win_rate_real*100:.1f}% >= {MIN_WIN_RATE*100:.0f}%")

desviacion = abs(win_rate_real - WIN_RATE_BACKTEST)
c3 = desviacion <= TOLERANCIA_BACKTEST
criterios.append(c3)
print(f"  {'OK' if c3 else 'NO'} Consistencia backtest: desviacion {desviacion*100:.1f}% (max {TOLERANCIA_BACKTEST*100:.0f}%)")

c4 = retorno_acumulado > MIN_RETORNO_ACUMULADO
criterios.append(c4)
print(f"  {'OK' if c4 else 'NO'} Retorno acumulado positivo: {retorno_acumulado:+.2f}%")

print(f"\n  ── VEREDICTO ──")
cumplidos = sum(criterios)
total = len(criterios)

if cumplidos == total:
    print(f"  LUZ VERDE — {cumplidos}/{total} criterios cumplidos")
    print(f"  Sistema listo para considerar expansion de capital.")
    print(f"  Recomendacion: subir capital gradualmente (+50%), no de golpe.")
elif cumplidos >= total * 0.5:
    print(f"  EN PROGRESO — {cumplidos}/{total} criterios cumplidos")
    print(f"  El sistema avanza pero aun no cumple todos los requisitos.")
    print(f"  Recomendacion: mantener capital actual, seguir acumulando datos.")
else:
    print(f"  NO EXPANDIR — {cumplidos}/{total} criterios cumplidos")
    print(f"  Datos insuficientes o sistema no validado en vivo.")
    print(f"  Recomendacion: no tocar capital, dejar operar y registrar.")

print("=" * 64)
