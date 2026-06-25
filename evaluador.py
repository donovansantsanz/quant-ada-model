import os
import pandas as pd
import requests
from dotenv import load_dotenv

load_dotenv()
TOKEN   = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

ARCHIVO = "paper_trading_registro.csv"

def enviar_telegram(mensaje):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    requests.post(url, data={"chat_id": CHAT_ID, "text": mensaje, "parse_mode": "HTML"})

if not os.path.exists(ARCHIVO):
    print("No hay registro todavía.")
    exit()

df = pd.read_csv(ARCHIVO)
evaluados = df[df['evaluado'] == True]
pendientes = df[df['evaluado'] == False]

# ── RESUMEN GENERAL ──────────────────────────────────────────────
total_señales = len(df)
total_compras = len(df[df['decision'] == 'COMPRAR'])
total_evaluados = len(evaluados[evaluados['decision'] == 'COMPRAR'])

mensaje = f"<b>📊 Resumen semanal — Paper Trading</b>\n\n"
mensaje += f"📅 Señales registradas: <b>{total_señales}</b>\n"
mensaje += f"✅ Señales COMPRAR: <b>{total_compras}</b>\n"
mensaje += f"🔍 Evaluadas (14d): <b>{total_evaluados}</b>\n"
mensaje += f"⏳ Pendientes: <b>{len(pendientes[pendientes['decision'] == 'COMPRAR'])}</b>\n\n"

# ── RESULTADOS POR ACTIVO ────────────────────────────────────────
if total_evaluados > 0:
    compras_eval = evaluados[evaluados['decision'] == 'COMPRAR']
    mensaje += "<b>Resultados por activo:</b>\n"

    for activo in df['activo'].unique():
        subset = compras_eval[compras_eval['activo'] == activo]
        if len(subset) == 0:
            continue
        win_rate = subset['acierto'].mean() * 100
        retorno_medio = subset['retorno_pct'].mean()
        stops = len(subset[subset['salida'] == 'stop_loss'])
        takes = len(subset[subset['salida'] == 'take_profit'])
        emoji = "✅" if retorno_medio > 0 else "❌"
        mensaje += f"\n{emoji} <b>{activo}</b>\n"
        mensaje += f"   Win rate: {win_rate:.1f}%\n"
        mensaje += f"   Retorno medio: {retorno_medio:.2f}%\n"
        mensaje += f"   Stop loss: {stops} | Take profit: {takes}\n"

    # ── MEJOR Y PEOR OPERACIÓN ───────────────────────────────────
    mejor = compras_eval.loc[compras_eval['retorno_pct'].idxmax()]
    peor  = compras_eval.loc[compras_eval['retorno_pct'].idxmin()]
    mensaje += f"\n🏆 Mejor operación: {mejor['activo']} {mejor['retorno_pct']:+.2f}% ({mejor['fecha']})\n"
    mensaje += f"💀 Peor operación:  {peor['activo']} {peor['retorno_pct']:+.2f}% ({peor['fecha']})\n"
else:
    mensaje += "⏳ Aún no hay operaciones evaluadas. Primeras evaluaciones a partir del 4 de julio.\n"

print(mensaje)
enviar_telegram(mensaje)
print("✅ Resumen enviado por Telegram")
