import streamlit as st
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import socket
import os

# IMPORTAMOS NUESTROS MÓDULOS
import auth as auth
import Finance_IA as fin

# --- PARCHE DE RED ---
socket.getaddrinfo = lambda *args, **kwargs: [r for r in (socket.getaddrinfo(*args, **kwargs) if hasattr(socket, '_orig_getaddrinfo') else socket.getaddrinfo(*args, **kwargs)) if r[0] == socket.AF_INET]

# Configuración inicial
st.set_page_config(page_title="PredicAI Terminal", layout="wide")
if "GEMINI_API_KEY" in st.secrets:
    API_KEY = st.secrets["GEMINI_API_KEY"]
else:
    # Esto es por si lo corrés en tu PC y tenés una variable de entorno
    API_KEY = os.getenv("GEMINI_API_KEY", "")

# Validamos que la clave exista antes de configurar
if API_KEY:
    model = fin.configurar_ia(API_KEY)
else:
    st.error("Falta la API Key. Configurala en los Secrets de Streamlit.")


# --- SIDEBAR: LOGIN Y REGISTRO ---
auth.conectar_db()
with st.sidebar:
    st.title("👤 Usuario")
    if 'logged_in' not in st.session_state: st.session_state['logged_in'] = False

    if not st.session_state['logged_in']:
        u = st.text_input("Nombre de Usuario")
        p = st.text_input("Contraseña", type="password")
        c1, c2 = st.columns(2)
        if c1.button("Entrar"):
            if auth.validar_login(u, p):
                st.session_state['logged_in'], st.session_state['username'] = True, u
                st.rerun()
        if c2.button("Registrar"):
            if auth.registrar_usuario(u, p): st.success("Creado")
    else:
        st.success(f"Sesión: {st.session_state['username']}")
        if st.button("Cerrar Sesión"):
            st.session_state['logged_in'] = False
            st.rerun()

# --- DASHBOARD ---
st.title("📊 PredicAI: Nasdaq 100 Terminal")
tickers = ["AAPL", "MSFT", "GOOGL", "AMZN", "NVDA", "META", "TSLA"]
ticker = st.selectbox("Activo:", tickers)

if ticker:
    info, stock_obj = fin.obtener_datos(ticker)
    
    # --- FILA 1: MÉTRICAS DE VALORACIÓN ---
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Precio Actual", f"${info.get('currentPrice', 'N/A')}")
    c2.metric("Market Cap", f"{info.get('marketCap', 0)/1e9:.2f}B")
    c3.metric("P/E Ratio", info.get('trailingPE', 'N/A'))
    c4.metric("Beta (Volatilidad)", info.get('beta', 'N/A'))

    # --- FILA 2: MÉTRICAS DE OPERACIÓN ---
    c5, c6, c7, c8 = st.columns(4)
    c5.metric("EPS (Beneficio/Acción)", f"${info.get('trailingEps', 'N/A')}")
    c6.metric("Volumen Diario", f"{info.get('volume', 0):,}")
    c7.metric("Máx 52 Semanas", f"${info.get('fiftyTwoWeekHigh', 'N/A')}")
    c8.metric("Mín 52 Semanas", f"${info.get('fiftyTwoWeekLow', 'N/A')}")

    # Gráficos
    hist = fin.calcular_indicadores(stock_obj.history(period="2y"))
    fig = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.08, 
                       row_heights=[0.7, 0.3], subplot_titles=("Precio y SMA 200", "RSI"))
    
    fig.add_trace(go.Candlestick(x=hist.index, open=hist['Open'], high=hist['High'], low=hist['Low'], close=hist['Close'], name="Velas"), row=1, col=1)
    fig.add_trace(go.Scatter(x=hist.index, y=hist['SMA200'], name="SMA 200", line=dict(color='gold')), row=1, col=1)
    fig.add_trace(go.Scatter(x=hist.index, y=hist['RSI'], name="RSI", line=dict(color='magenta')), row=2, col=1)
    
    fig.update_layout(xaxis_rangeslider_visible=False, template="plotly_dark", height=600)
    st.plotly_chart(fig, use_container_width=True)

    # IA
    st.divider()
    if st.button("Generar Análisis IA"):
        with st.spinner("Analizando noticias..."):
            analisis = fin.analizar_con_ia(model, ticker, stock_obj.news)
            st.info(analisis)