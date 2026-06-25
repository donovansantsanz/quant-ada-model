import pandas as pd
import os

ARCHIVO = "/root/proyectos-quant/paper_trading_registro.csv"

if not os.path.exists(ARCHIVO):
    print("No hay registro todavía.")
    exit()

df = pd.read_csv(ARCHIVO)

print("=" * 70)
print("  HISTORIAL PAPER TRADING")
print("=" * 70)

# Resumen general
total = len(df)
compras = len(df[df['decision'] == 'COMPRAR'])
mantener = len(df[df['decision'] == 'MANTENER'])
evaluadas = len(df[df['evaluado'] == True])

print(f"\n  Total registros:     {total}")
print(f"  Señales COMPRAR:     {compras}")
print(f"  Señales MANTENER:    {mantener}")
print(f"  Evaluadas (14d):     {evaluadas}")
print(f"  Pendientes:          {total - evaluadas}")

# Detalle por día
print("\n" + "─" * 70)
print(f"  {'Fecha':<12} {'Activo':<12} {'Decisión':<10} {'Score':>6} {'RSI':>6} {'Precio':>12}")
print("─" * 70)

for _, row in df.iterrows():
    decision = row['decision']
    emoji = "✅" if decision == 'COMPRAR' else "⏸"
    precio = f"${float(row['precio_entrada']):.4f}" if float(row['precio_entrada']) < 10 else f"${float(row['precio_entrada']):.2f}"
    print(f"  {str(row['fecha']):<12} {row['activo']:<12} {emoji} {decision:<8} {int(row['score']):>6} {float(row['rsi']):>6.1f} {precio:>12}")

# Track record si hay evaluadas
if evaluadas > 0:
    print("\n" + "─" * 70)
    print("  TRACK RECORD\n")
    compras_eval = df[(df['evaluado'] == True) & (df['decision'] == 'COMPRAR')]
    if len(compras_eval) > 0:
        for activo in compras_eval['activo'].unique():
            subset = compras_eval[compras_eval['activo'] == activo]
            win_rate = subset['acierto'].mean() * 100
            retorno = subset['retorno_pct'].mean()
            print(f"  {activo}: Win rate {win_rate:.1f}% | Retorno medio {retorno:.2f}%")

print("\n" + "=" * 70)
print(f"  Próxima evaluación: {df['fecha_evaluacion'].min()}")
print("=" * 70 + "\n")
