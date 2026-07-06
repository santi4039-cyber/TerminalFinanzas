import yfinance as yf
import pandas as pd
import google.generativeai as genai
import requests
import streamlit as st

def configurar_ia(api_key):
    genai.configure(api_key=api_key)
    return genai.GenerativeModel('gemini-2.5-flash')

# --- 1. DATOS BURSÁTILES CON CACHÉ (Evita el bloqueo NoneType de Yahoo) ---
@st.cache_resource(ttl=900, show_spinner=False)
def obtener_datos(ticker):
    """
    Descarga la información de Yahoo Finance sin sesión personalizada para evitar
    romper el método .history(), guardando el objeto en caché por 15 minutos.
    """
    # Dejamos que yfinance gestione la conexión nativamente
    stock = yf.Ticker(ticker)
    try:
        info = stock.info
        if not info: 
            return {}, stock
        return info, stock
    except Exception as e:
        print(f"Error capturando datos: {e}")
        return {}, stock

def calcular_indicadores(hist):
    if hist.empty:
        return hist
    # SMA 200
    hist['SMA200'] = hist['Close'].rolling(window=200).mean()
    # RSI (Optimizado con media móvil exponencial ewm)
    delta = hist['Close'].diff()
    gain = (delta.where(delta > 0, 0)).ewm(alpha=1/14, adjust=False).mean()
    loss = (-delta.where(delta < 0, 0)).ewm(alpha=1/14, adjust=False).mean()
    rs = gain / loss
    hist['RSI'] = 100 - (100 / (1 + rs))
    return hist

# --- 2. ÍNDICE DE MIEDO Y CODICIA CON CACHÉ ---
@st.cache_data(ttl=900, show_spinner=False)
def obtener_fear_and_greed():
    """
    Extrae el índice Fear & Greed en tiempo real desde CNN.
    Al usar caché, no congela la app ni interfiere con las peticiones de Yahoo.
    """
    url = "https://production.dataviz.cnn.io/index/fearandgreed/graphdata"
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36',
        'Referer': 'https://www.cnn.com/markets/fear-and-greed'
    }
    
    try:
        res = requests.get(url, headers=headers, timeout=5)
        if res.status_code == 200:
            data = res.json()
            actual_data = data.get('fear_and_greed', {})
            score = round(actual_data.get('score', 50), 1)
            rating = actual_data.get('rating', 'neutral').replace('_', ' ').title()
            return score, rating
        return None, "No disponible"
    except Exception as e:
        print(f"Error obteniendo Fear & Greed: {e}")
        return None, "Error de conexión"

# --- 3. INTELIGENCIA ARTIFICIAL ---
def analizar_con_ia(model, ticker, noticias):
    if not noticias: return "No hay noticias suficientes."
    titulares = [n.get('title') or n.get('content', {}).get('title') or "Noticia" for n in noticias[:5]]
    prompt = f"Analiza estos titulares sobre {ticker} y da un veredicto Bullish o Bearish con 3 razones: {titulares}"
    res = model.generate_content(prompt)
    return res.text

@st.cache_data(ttl=900, show_spinner=False)
def obtener_vix():
    try:
        vix = yf.Ticker("^VIX")
        hist = vix.history(period="2y")
        if hist.empty:
            raise ValueError("Historial del VIX vacío")
        
        precio_actual = round(hist['Close'].iloc[-1], 2)
        
        # Evaluamos el estado psicológico según el nivel del VIX
        if precio_actual < 15: estado = "Complacencia / Calma"
        elif precio_actual <= 25: estado = "Volatilidad Normal"
        else: estado = "Pánico / Alto Riesgo"
        
        return precio_actual, estado
    except Exception as e:
        print(f"Error obteniendo el VIX: {e}")
        return None, "No disponible"
    


def simular_backtest_rsi(hist, capital_inicial=10000.0, rsi_compra=30, rsi_venta=70):
    """
    Simula una estrategia de trading basada en el RSI y la compara contra Buy & Hold.
    Devuelve el DataFrame con las curvas de capital y un diccionario con los KPIs.
    """
    if hist.empty or 'RSI' not in hist.columns:
        return None, {}
    
    # Trabajamos con una copia limpia donde el RSI ya sea válido (después de los primeros 14 días)
    df = hist.copy().dropna(subset=['RSI'])
    
    efectivo = float(capital_inicial)
    acciones = 0.0
    posicion_abierta = False
    precio_compra = 0.0
    trades_cerrados = []
    
    curva_capital = []
    
    # Simulación día por día
    for index, row in df.iterrows():
        precio = row['Close']
        rsi = row['RSI']
        
        # 1. Señal de Compra: Si estamos fuera y el RSI indica sobreventa
        if not posicion_abierta and rsi < rsi_compra:
            acciones = efectivo / precio
            efectivo = 0.0
            posicion_abierta = True
            precio_compra = precio
            
        # 2. Señal de Venta: Si estamos dentro y el RSI indica sobrecompra
        elif posicion_abierta and rsi > rsi_venta:
            efectivo = acciones * precio
            # Calculamos la rentabilidad de este trade en porcentaje
            rentabilidad_trade = ((precio - precio_compra) / precio_compra) * 100.0
            trades_cerrados.append(rentabilidad_trade)
            acciones = 0.0
            posicion_abierta = False
            
        # 3. Registro del valor diario del portafolio
        val_actual = efectivo if not posicion_abierta else (acciones * precio)
        curva_capital.append(val_actual)
        
    df['Capital_Estrategia'] = curva_capital
    
    # Cálculo de la estrategia Buy & Hold (Comprar día 1 y mantener)
    acciones_bh = capital_inicial / df['Close'].iloc[0]
    df['Capital_BuyHold'] = acciones_bh * df['Close']
    
    # --- CÁLCULO DE MÉTRICAS (KPIs) ---
    cap_final_est = df['Capital_Estrategia'].iloc[-1]
    cap_final_bh = df['Capital_BuyHold'].iloc[-1]
    
    retorno_est = ((cap_final_est - capital_inicial) / capital_inicial) * 100.0
    retorno_bh = ((cap_final_bh - capital_inicial) / capital_inicial) * 100.0
    
    total_trades = len(trades_cerrados)
    trades_ganadores = len([t for t in trades_cerrados if t > 0])
    win_rate = (trades_ganadores / total_trades * 100.0) if total_trades > 0 else 0.0
    
    # Max Drawdown (Peor caída desde un pico anterior)
    picos = df['Capital_Estrategia'].cummax()
    drawdown = ((df['Capital_Estrategia'] - picos) / picos) * 100.0
    max_drawdown = drawdown.min()
    
    metricas = {
        "capital_final": round(cap_final_est, 2),
        "capital_bh": round(cap_final_bh, 2),
        "retorno_est": round(retorno_est, 2),
        "retorno_bh": round(retorno_bh, 2),
        "total_trades": total_trades,
        "win_rate": round(win_rate, 2),
        "max_drawdown": round(max_drawdown, 2)
    }
    
    return df, metricas