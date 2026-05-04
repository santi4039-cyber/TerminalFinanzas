import yfinance as yf
import pandas as pd
import google.generativeai as genai
import requests

def configurar_ia(api_key):
    genai.configure(api_key=api_key)
    return genai.GenerativeModel('gemini-2.5-flash')

def crear_sesion():
    session = requests.Session()
    # Esto simula ser un navegador real
    session.headers.update({
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36'
    })
    return session

import yfinance as yf

def obtener_datos(ticker):
    # Ya no pasamos session=sesion. 
    # yfinance detectará curl_cffi y se "disfrazará" de Chrome automáticamente.
    stock = yf.Ticker(ticker)
    
    try:
        # Intentamos obtener la info
        info = stock.info
        if not info: # A veces devuelve un dict vacío si hay error de red
            return {}, stock
        return info, stock
    except Exception as e:
        print(f"Error capturando datos: {e}")
        return {}, stock

def calcular_indicadores(hist):
    # SMA 200
    hist['SMA200'] = hist['Close'].rolling(window=200).mean()
    # RSI
    delta = hist['Close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    rs = gain / loss
    hist['RSI'] = 100 - (100 / (1 + rs))
    return hist

def analizar_con_ia(model, ticker, noticias):
    if not noticias: return "No hay noticias suficientes."
    titulares = [n.get('title') or n.get('content', {}).get('title') or "Noticia" for n in noticias[:5]]
    prompt = f"Analiza estos titulares sobre {ticker} y da un veredicto Bullish o Bearish con 3 razones: {titulares}"
    res = model.generate_content(prompt)
    return res.text