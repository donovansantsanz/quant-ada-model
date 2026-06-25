import pandas as pd
from pathlib import Path

CSV = Path('/root/proyectos-quant/paper_trading_4h_registro.csv')

if not CSV.exists():
    print("No hay registros todavía.")
    exit()

df = pd.read_csv(CSV)
df['fecha'] = pd.to_datetime(df['fecha'])

total     = len(df)
compras   = (df['decision'] == 'COMPRAR').sum()
mantener  = (df['decision'] == 'MANTENER').sum()
evaluadas = df['evaluado'].sum()
pendientes = (~df['evaluado']).sum()

print("=" * 70)
print("  HISTORIAL PAPER TRADING 4H")
print("=" * 70)
print(f"  Total registros:     {total}")
print(f"  Señales COMPRAR:     {compras}")
print(f"  Señales MANTENER:    {mantener}")
print(f"  Evaluadas (2d):      {evaluadas}")
print(f"  Pendientes:          {pendientes}")
print("-" * 70)
print(f"  {'Fecha':<18} {'Activo':<12} {'Decisión':<12} {'Score':<8} {'RSI':<8} {'Precio'}")
print("-" * 70)

for _, r in df.iterrows():
    fecha  = r['fecha'].strftime('%Y-%m-%d %H:%M')
    activo = r['activo']
    dec    = '🟢 COMPRAR' if r['decision'] == 'COMPRAR' else '⏸ MANTENER'
    score  = r['score']
    rsi    = f"{r['rsi']:.1f}"
    precio = f"${r['precio_entrada']:.4f}" if r['precio_entrada'] < 1 else f"${r['precio_entrada']:.2f}"
    print(f"  {fecha:<18} {activo:<12} {dec:<12} {score:<8} {rsi:<8} {precio}")

if evaluadas > 0:
    ganadoras = df[df['acierto'] == True]
    win_rate  = len(ganadoras) / evaluadas * 100
    print("-" * 70)
    print(f"  Win rate real: {win_rate:.1f}% ({len(ganadoras)}/{int(evaluadas)} evaluadas)")

print("=" * 70)
print(f"  Próxima evaluación: {(df['fecha_evaluacion'].dropna().iloc[0]) if pendientes > 0 else 'N/A'}")
print("=" * 70)
