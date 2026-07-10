import pandas as pd
import os

def tiene_posicion_abierta(activo):
    """Chequea si hay posicion abierta para un activo"""
    ops_file = os.path.expanduser('~/proyectos-quant/operaciones_reales.csv')
    df = pd.read_csv(ops_file)
    abierta = df[(df['activo'] == activo) & (df['fecha_cierre'].isna())]
    return len(abierta) > 0
