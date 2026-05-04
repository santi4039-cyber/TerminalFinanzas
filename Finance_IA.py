import yfinance as yf
import pandas as pd
import google.generativeai as genai

def configurar_ia(api_key):
    genai.configure(api_key=api_key)
    return genai.GenerativeModel('gemini-2.5-flash')

def obtener_datos(ticker):
    stock = yf.Ticker(ticker)
    return stock.info, stock

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