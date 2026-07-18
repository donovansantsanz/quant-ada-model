import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import numpy as np
import os
from datetime import datetime

ARCHIVO = '/root/proyectos-quant/operaciones_reales.csv'
OUTPUT_DIR = os.path.expanduser('~/proyectos-quant/graficos')
os.makedirs(OUTPUT_DIR, exist_ok=True)

df = pd.read_csv(ARCHIVO)
df['fecha_entrada'] = pd.to_datetime(df['fecha_entrada'], format='mixed')

# Solo operaciones cerradas
cerradas = df[df['fecha_cierre'].notna() & (df['resultado'] != 'cerrado_manual')].copy()
cerradas['fecha_cierre'] = pd.to_datetime(cerradas['fecha_cierre'], format='mixed')
cerradas['retorno_pct'] = pd.to_numeric(cerradas['retorno_pct'], errors='coerce')

# ── 1. EQUITY CURVE ──────────────────────────────────────────────
fig, ax = plt.subplots(figsize=(12, 6))
fig.patch.set_facecolor('#1a1a2e')
ax.set_facecolor('#1a1a2e')

if len(cerradas) > 0:
    cerradas = cerradas.sort_values('fecha_cierre')
    cerradas['equity'] = (1 + cerradas['retorno_pct'] / 100).cumprod() * 100
    
    # Colorear por venue
    colores_venue = {'binance': '#e94560', 'bitvavo': '#0f3460'}
    
    ax.plot(cerradas['fecha_cierre'], cerradas['equity'], 
            color='#00d2ff', linewidth=2, zorder=3)
    
    # Puntos por venue
    for venue, color in colores_venue.items():
        mask = cerradas['venue'] == venue
        if mask.any():
            ax.scatter(cerradas.loc[mask, 'fecha_cierre'], 
                      cerradas.loc[mask, 'equity'],
                      color=color, s=60, zorder=4, label=venue.capitalize(),
                      edgecolors='white', linewidth=0.5)
    
    # Línea base 100
    ax.axhline(y=100, color='#ffffff', linestyle='--', alpha=0.3, linewidth=0.8)
    
    # Anotaciones
    for _, row in cerradas.iterrows():
        emoji = '✓' if row['retorno_pct'] > 0 else '✗'
        color = '#00ff88' if row['retorno_pct'] > 0 else '#ff4444'
        ax.annotate(f"{emoji} {row['retorno_pct']:+.1f}%", 
                   (row['fecha_cierre'], row['equity']),
                   textcoords="offset points", xytext=(0, 12),
                   fontsize=7, color=color, ha='center')

ax.set_title('Equity Curve — Sistema Quant V2', color='white', fontsize=14, fontweight='bold')
ax.set_ylabel('Equity (base 100)', color='white', fontsize=11)
ax.tick_params(colors='white')
ax.spines['bottom'].set_color('#333333')
ax.spines['left'].set_color('#333333')
ax.spines['top'].set_visible(False)
ax.spines['right'].set_visible(False)
ax.grid(alpha=0.15, color='white')
ax.legend(facecolor='#1a1a2e', edgecolor='#333333', labelcolor='white')
ax.xaxis.set_major_formatter(mdates.DateFormatter('%d %b'))

plt.tight_layout()
plt.savefig(f'{OUTPUT_DIR}/equity_curve.png', dpi=150, facecolor='#1a1a2e')
print(f"✅ Equity curve → {OUTPUT_DIR}/equity_curve.png")

# ── 2. DISTRIBUCIÓN DE RETORNOS ──────────────────────────────────
fig2, ax2 = plt.subplots(figsize=(10, 5))
fig2.patch.set_facecolor('#1a1a2e')
ax2.set_facecolor('#1a1a2e')

if len(cerradas) > 0:
    retornos = cerradas['retorno_pct'].dropna()
    colores = ['#00ff88' if r > 0 else '#ff4444' for r in retornos]
    ax2.bar(range(len(retornos)), retornos, color=colores, edgecolor='white', linewidth=0.5)
    ax2.axhline(y=0, color='white', linewidth=0.8, alpha=0.5)
    ax2.axhline(y=retornos.mean(), color='#00d2ff', linewidth=1, linestyle='--', 
               label=f'Media: {retornos.mean():.2f}%')
    
    # Labels por operación
    for i, (_, row) in enumerate(cerradas.iterrows()):
        ax2.text(i, retornos.iloc[i] + 0.1, row['activo'].split('/')[0], 
                ha='center', fontsize=7, color='white', alpha=0.7)

ax2.set_title('Retorno por Operación', color='white', fontsize=14, fontweight='bold')
ax2.set_ylabel('Retorno (%)', color='white', fontsize=11)
ax2.set_xlabel('Operación #', color='white', fontsize=11)
ax2.tick_params(colors='white')
ax2.spines['bottom'].set_color('#333333')
ax2.spines['left'].set_color('#333333')
ax2.spines['top'].set_visible(False)
ax2.spines['right'].set_visible(False)
ax2.grid(alpha=0.15, color='white', axis='y')
ax2.legend(facecolor='#1a1a2e', edgecolor='#333333', labelcolor='white')

plt.tight_layout()
plt.savefig(f'{OUTPUT_DIR}/retornos.png', dpi=150, facecolor='#1a1a2e')
print(f"✅ Distribución retornos → {OUTPUT_DIR}/retornos.png")

# ── 3. RESUMEN ESTADÍSTICO ───────────────────────────────────────
if len(cerradas) > 0:
    retornos = cerradas['retorno_pct'].dropna()
    wins = (retornos > 0).sum()
    losses = (retornos <= 0).sum()
    
    print(f"\n📊 RESUMEN:")
    print(f"  Operaciones: {len(retornos)}")
    print(f"  Wins: {wins} | Losses: {losses}")
    print(f"  Win rate: {wins/len(retornos)*100:.1f}%")
    print(f"  Retorno medio: {retornos.mean():.2f}%")
    print(f"  Mejor op: {retornos.max():+.2f}%")
    print(f"  Peor op: {retornos.min():+.2f}%")
    print(f"  Retorno acumulado: {((1 + retornos/100).prod() - 1) * 100:.2f}%")
else:
    print("⚠️ No hay operaciones cerradas para graficar")
