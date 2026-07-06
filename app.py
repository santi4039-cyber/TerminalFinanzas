import streamlit as st
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import streamlit.components.v1 as components
import socket
import os
import auth as auth
import Finance_IA as fin

# Configuración inicial
st.set_page_config(page_title="Terminal Acciones", layout="wide")

# Buscar la API Key en variables de entorno primero, y luego en los secrets de Streamlit de forma segura
API_KEY = os.getenv("GEMINI_API_KEY", "")
try:
    if "GEMINI_API_KEY" in st.secrets:
        API_KEY = st.secrets["GEMINI_API_KEY"]
except Exception:
    # Si el archivo secrets.toml no existe, ignoramos el error y mantenemos lo que haya en os.getenv
    pass

if API_KEY:
    model = fin.configurar_ia(API_KEY)
else:
    st.error("Falta la API Key. Configúrala en el archivo .streamlit/secrets.toml o como variable de entorno.")

# LOGIN Y REGISTRO
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

# DASHBOARD
# DASHBOARD PRINCIPAL CON PESTAÑAS
st.title("📊 PredicAI: Nasdaq 100 Terminal")

# Función auxiliar con caché para descargar historial en el Backtest sin errores
@st.cache_data(ttl=900, show_spinner=False)
def obtener_historial_seguro(tck, periodo="2y"):
    try:
        return fin.yf.Ticker(tck).history(period=periodo)
    except Exception:
        return fin.pd.DataFrame()

# Creamos las dos pestañas de navegación
tab_terminal, tab_backtest = st.tabs(["📈 Terminal de Mercado (TradingView)", "🧪 Simulador de Backtesting"])

# =========================================================
# PESTAÑA 1: TERMINAL DE MERCADO CON TRADINGVIEW
# =========================================================
with tab_terminal:
    tickers = ["AAPL", "MSFT", "GOOGL", "AMZN", "NVDA", "META", "TSLA", "MU", "ORCL", "AVGO", "KO", "AMD"]
    ticker = st.selectbox("Activo a analizar:", tickers, key="sel_terminal")

    if ticker:
        info, stock_obj = fin.obtener_datos(ticker)
        
        # MÉTRICAS DE VALORACIÓN
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Precio Actual", f"${info.get('currentPrice', 'N/A')}")
        c2.metric("Market Cap", f"{info.get('marketCap', 0)/1e9:.2f}B")
        c3.metric("P/E Ratio", info.get('trailingPE', 'N/A'))
        c4.metric("Beta (Volatilidad)", info.get('beta', 'N/A'))

        # MÉTRICAS DE OPERACIÓN
        c5, c6, c7, c8 = st.columns(4)
        c5.metric("EPS (Beneficio/Acción)", f"${info.get('trailingEps', 'N/A')}")
        c6.metric("Volumen Diario", f"{info.get('volume', 0):,}")
        c7.metric("Máx 52 Semanas", f"${info.get('fiftyTwoWeekHigh', 'N/A')}")
        c8.metric("Mín 52 Semanas", f"${info.get('fiftyTwoWeekLow', 'N/A')}")

        # Gráfico Oficial Interactivo de TradingView
        st.markdown("### 📈 Gráfico Interactivo (Powered by TradingView)")
        
        simbolo_tv = f"NASDAQ:{ticker}"
        
        tradingview_html = f"""
        <div class="tradingview-widget-container" style="height: 600px; width: 100%;">
          <div id="tradingview_app" style="height: calc(100% - 32px); width: 100%;"></div>
          <script type="text/javascript" src="https://s3.tradingview.com/tv.js"></script>
          <script type="text/javascript">
          new TradingView.widget({{
            "autosize": true,
            "symbol": "{simbolo_tv}",
            "interval": "D",
            "timezone": "America/Argentina/Buenos_Aires",
            "theme": "dark",
            "style": "1",
            "locale": "es",
            "enable_publishing": false,
            "hide_top_toolbar": false,
            "hide_legend": false,
            "save_image": false,
            "calendar": false,
            "hide_volume": false,
            "support_host": "https://www.tradingview.com",
            "studies": [
              "RSI@tv-basicstudies",
              "MASimple@tv-basicstudies"
            ],
            "container_id": "tradingview_app"
          }});
          </script>
        </div>
        """
        
        components.html(tradingview_html, height=610, scrolling=False)

        # Inteligencia Artificial
        st.divider()
        if st.button("Generar Análisis IA", key="btn_ia_terminal"):
            with st.spinner("Analizando noticias con Gemini..."):
                analisis = fin.analizar_con_ia(model, ticker, stock_obj.news)
                
                # --- FORMATO DE TARJETA IA CON ENLACES A FUENTES ---
                with st.container(border=True):
                    st.markdown("#### 🤖 Veredicto Cuantitativo (Gemini 2.5 Flash)")
                    st.markdown(analisis)
                    
                    # --- SECCIÓN DE FUENTES ANALIZADAS ---
                    st.divider()
                    st.markdown("##### 📰 Fuentes y Referencias")
                    
                    if stock_obj.news:
                        for n in stock_obj.news[:5]:
                            # Extracción segura compatible con versiones antiguas y nuevas de yfinance
                            titulo = n.get('title') or n.get('content', {}).get('title', 'Sin título')
                            link = n.get('link') or n.get('content', {}).get('canonicalUrl', {}).get('url', '#')
                            editorial = n.get('publisher') or n.get('content', {}).get('provider', {}).get('displayName', 'Yahoo Finance')
                            
                            # Renderizamos como lista de Markdown con su link y su editorial
                            if link != '#':
                                st.markdown(f"• **[{titulo}]({link})** *(Fuente: {editorial})*")
                            else:
                                st.markdown(f"• **{titulo}** *(Fuente: {editorial})*")
                    else:
                        st.caption("No se encontraron enlaces a fuentes periodísticas recientes.")


# =========================================================
# PESTAÑA 2: SIMULADOR DE BACKTESTING CUANTITATIVO
# =========================================================
with tab_backtest:
    st.subheader("🧪 Simulador Algorítmico: Reversión a la Media (RSI)")
    st.markdown("Evalúa qué rendimiento habría obtenido un algoritmo en los **últimos 2 años** comprando automáticamente en zonas de sobreventa y vendiendo en sobrecompra.")
    
    # Parámetros interactivos del Backtest
    with st.expander("⚙️ Configuración de la Estrategia", expanded=True):
        col_b1, col_b2, col_b3, col_b4 = st.columns(4)
        ticker_bt = col_b1.selectbox("Activo:", tickers, key="sel_backtest")
        cap_inicial = col_b2.number_input("Capital Inicial ($)", min_value=100.0, value=10000.0, step=500.0)
        rsi_compra = col_b3.slider("RSI Compra (Sobreventa)", min_value=10, max_value=45, value=30, step=1)
        rsi_venta = col_b4.slider("RSI Venta (Sobrecompra)", min_value=55, max_value=90, value=70, step=1)

    if st.button("🚀 Ejecutar Simulación", use_container_width=True, key="btn_run_bt"):
        with st.spinner(f"Simulando transacciones históricas para {ticker_bt}..."):
            hist_bt = obtener_historial_seguro(ticker_bt, periodo="2y")
            
            if hist_bt.empty:
                st.error("❌ No se pudieron descargar los datos bursátiles para realizar el backtest.")
            else:
                # Calculamos RSI y ejecutamos el motor de simulación de Finance_IA.py
                hist_bt = fin.calcular_indicadores(hist_bt)
                df_sim, kpis = fin.simular_backtest_rsi(hist_bt, cap_inicial, rsi_compra, rsi_venta)
                
                # Métricas de Rendimiento (KPIs)
                st.divider()
                st.markdown(f"### 🎯 Resultados Clave para **{ticker_bt}**")
                
                m1, m2, m3, m4 = st.columns(4)
                m1.metric(
                    "Capital Final (Estrategia)", 
                    f"${kpis['capital_final']:,.2f}", 
                    f"{kpis['retorno_est']:+.2f}%",
                    help="Dinero resultante siguiendo estrictamente las señales de compra/venta del RSI."
                )
                m2.metric(
                    "Capital Final (Buy & Hold)", 
                    f"${kpis['capital_bh']:,.2f}", 
                    f"{kpis['retorno_bh']:+.2f}%",
                    help="Dinero resultante si hubieras comprado el día 1 y mantenido la acción sin vender."
                )
                m3.metric(
                    "Win Rate (% Aciertos)", 
                    f"{kpis['win_rate']:.1f}%", 
                    f"{kpis['total_trades']} Trades",
                    help="Porcentaje de operaciones cerradas con ganancias."
                )
                m4.metric(
                    "Max Drawdown (Riesgo)", 
                    f"{kpis['max_drawdown']:.2f}%", 
                    delta_color="inverse",
                    help="La mayor caída porcentual que sufrió la cuenta desde su punto más alto."
                )
                
                # Gráfico Comparativo de Curvas de Capital (Estilo Dark / TradingView)
                st.markdown("### 📈 Curva de Equidad: Estrategia RSI vs Benchmark")
                
                fig_bt = go.Figure()
                # Línea de la Estrategia (Verde fluorescente tipo TradingView)
                fig_bt.add_trace(go.Scatter(
                    x=df_sim.index, y=df_sim['Capital_Estrategia'], 
                    name=f"Estrategia RSI ({rsi_compra}/{rsi_venta})", 
                    line=dict(color='#00E676', width=2.5)
                ))
                # Línea Buy and Hold (Azul institucional)
                fig_bt.add_trace(go.Scatter(
                    x=df_sim.index, y=df_sim['Capital_BuyHold'], 
                    name="Benchmark (Buy & Hold)", 
                    line=dict(color='#2979FF', width=1.5, dash='dot')
                ))
                
                fig_bt.update_layout(
                    template="plotly_dark",
                    height=450,
                    hovermode="x unified",
                    xaxis_title="Fecha",
                    yaxis_title="Capital Acumulado ($ USD)",
                    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
                    margin=dict(l=10, r=10, t=30, b=10)
                )
                
                st.plotly_chart(fig_bt, use_container_width=True)
                
                # Conclusión automática del algoritmo
                if kpis['retorno_est'] > kpis['retorno_bh']:
                    st.success(f"🏆 **¡Estrategia Ganadora!** El algoritmo superó al mercado por **{kpis['retorno_est'] - kpis['retorno_bh']:+.2f}%** operando de forma activa en {ticker_bt}.")
                else:
                    st.info(f"💡 **Nota de Mercado:** En una tendencia alcista tan fuerte como la de {ticker_bt}, simplemente comprar y mantener (Buy & Hold) superó al trading activo por **{kpis['retorno_bh'] - kpis['retorno_est']:+.2f}%**.")

 # --- ÍNDICE DE MIEDO Y CODICIA + VIX (MACRO) ---
st.sidebar.divider()
st.sidebar.subheader("🧭 Sentimiento de Mercado")

# Realizamos las dos consultas a tu archivo de finanzas
score, rating = fin.obtener_fear_and_greed()
vix_val, vix_estado = fin.obtener_vix()

# === RENDER DEL VELOCÍMETRO DE CNN ===
if score is not None:
    colores_map = {
        "Extreme Fear": "#ff4d4d",
        "Fear": "#ffa64d",
        "Neutral": "#ffff4d",
        "Greed": "#99e699",
        "Extreme Greed": "#2eb82e"
    }
    color_texto = colores_map.get(rating, "white")

    st.sidebar.markdown(
        f"Mercado General: <span style='color:{color_texto}; font-size:1.1em; font-weight:bold;'>{rating}</span>", 
        unsafe_allow_html=True
    )

    fig_gauge = go.Figure(go.Indicator(
        mode = "gauge+number",
        value = score,
        gauge = {
            'axis': {'range': [0, 100], 'tickwidth': 1, 'tickcolor': "white"},
            'bar': {'color': "white", 'thickness': 0.2},
            'bgcolor': "rgba(0,0,0,0)",
            'borderwidth': 1,
            'bordercolor': "gray",
            'steps': [
                {'range': [0, 25], 'color': "#8b0000"},       
                {'range': [25, 45], 'color': "#d9534f"},      
                {'range': [45, 55], 'color': "#f0ad4e"},      
                {'range': [55, 75], 'color': "#5cb85c"},      
                {'range': [75, 100], 'color': "#2e7d32"}      
            ]
        }
    ))
    
    fig_gauge.update_layout(
        height=130, 
        margin=dict(l=15, r=15, t=5, b=10),
        template="plotly_dark",
        paper_bgcolor="rgba(0,0,0,0)"
    )
    st.sidebar.plotly_chart(fig_gauge, use_container_width=True)
else:
    st.sidebar.warning(f"Índice CNN: {rating}")


# === RENDER DE LA MÉTRICA DEL VIX (CENTRADO) ===
if vix_val is not None:
    st.sidebar.markdown("<br>", unsafe_allow_html=True) # Pequeño espacio de separación
    
    # 🎨 TRUCO CSS: Le decimos a Streamlit que centre los componentes st.metric en la barra lateral
    st.sidebar.markdown(
        """
        <style>
        [data-testid="stSidebar"] [data-testid="stMetric"] {
            display: flex;
            flex-direction: column;
            align-items: center;
            text-align: center;
        }
        [data-testid="stSidebar"] [data-testid="stMetricLabel"] > div {
            justify-content: center;
        }
        [data-testid="stSidebar"] [data-testid="stMetricDelta"] > div {
            justify-content: center;
        }
        </style>
        """, 
        unsafe_allow_html=True
    )
    
    # Renderizamos la métrica normalmente (ahora se dibujará en el centro exacto)
    st.sidebar.metric(
        label="📊 Índice de Pánico (VIX)", 
        value=f"{vix_val} pts", 
        delta=vix_estado,
        delta_color="inverse"
    )
else:
    st.sidebar.warning("Índice VIX: No disponible")