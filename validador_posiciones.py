import os
from conexion import get_exchange

def tiene_posicion_abierta(activo):
    """
    Chequea si hay posicion abierta consultando el BALANCE REAL en Bitvavo.
    Mas fiable que el CSV porque las OCO manuales no actualizan el CSV.
    """
    try:
        exchange = get_exchange()
        base = activo.split('/')[0]
        balance = exchange.fetch_balance()
        cantidad = balance['total'].get(base, 0)
        ticker = exchange.fetch_ticker(activo)
        precio = ticker['last']
        valor_eur = cantidad * precio
        return valor_eur > 10
    except Exception as e:
        print(f"Error validando posicion {activo}: {e}")
        return False
