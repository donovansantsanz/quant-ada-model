import os
import ccxt
from dotenv import load_dotenv

load_dotenv(os.path.expanduser("~/proyectos-quant/.env"))

def get_exchange():
    return ccxt.bitvavo({
        'apiKey': os.getenv("BITVAVO_API_KEY"),
        'secret': os.getenv("BITVAVO_API_SECRET"),
        'enableRateLimit': True,
        'options': {'operatorId': int(os.getenv("BITVAVO_OPERATOR_ID"))},
    })
