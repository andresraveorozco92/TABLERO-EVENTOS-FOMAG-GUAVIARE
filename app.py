import streamlit as st
import pandas as pd
import sqlite3
import plotly.express as px
import plotly.graph_objects as go

# ─────────────────────────────────────────────────────────────────────────────
# CONFIGURACIÓN DE PÁGINA — SIEMPRE PRIMERA
# ─────────────────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Tablero Epidemiológico FOMAG",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─────────────────────────────────────────────────────────────────────────────
# CSS GLOBAL — sin tocar elementos del sistema de Streamlit
# ─────────────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
/* ── Fondo general ── */
.stApp { background-color: #eef1f8; }

/* ── Sidebar con fondo azul pálido ── */
[data-testid="stSidebar"] { background-color: #dde2f5; }
[data-testid="stSidebarContent"] { background-color: #dde2f5; }

/* ── KPI cards ── */
.kpi-card {
    background: #ffffff;
    border-radius: 12px;
    padding: 22px 14px 18px 14px;
    text-align: center;
    box-shadow: 0 3px 10px rgba(0,0,0,0.09);
    border-top: 7px solid #1E6FBF;
    margin-bottom: 4px;
}
.kpi-card.green  { border-top-color: #27AE60; }
.kpi-card.red    { border-top-color: #C0392B; }
.kpi-card.purple { border-top-color: #8E44AD; }
.kpi-label { font-size: 1.1rem; font-weight: 700; color: #555; text-transform: uppercase; letter-spacing: .04rem; }
.kpi-num   { font-size: 3.4rem; font-weight: 900; color: #222; line-height: 1.2; margin-top: 6px; }

/* ── Títulos de sección ── */
.sec-title {
    font-size: 1.3rem;
    font-weight: 800;
    color: #2c3e70;
    letter-spacing: .05rem;
    text-align: center;
    margin-bottom: 10px;
    text-transform: uppercase;
    border-bottom: 2px solid #c3cbe8;
    padding-bottom: 6px;
}

/* ── Botones de año más grandes ── */
div.stButton > button {
    height: 56px !important;
    min-width: 110px !important;
    font-size: 1.4rem !important;
    font-weight: 800 !important;
    border-radius: 10px !important;
    letter-spacing: .05rem !important;
}
</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────────────────────
# CARGA DE DATOS
# ─────────────────────────────────────────────────────────────────────────────
DB_PATH = "eventos.db"

@st.cache_data
def load_data() -> pd.DataFrame:
    conn = sqlite3.connect(DB_PATH)
    df = pd.read_sql("SELECT * FROM eventos", conn)
    conn.close()
    df.columns = [c.strip() for c in df.columns]

    df["Evento Notificado"] = df["Evento Notificado"].str.strip().str.upper()
    df["Municipio"]         = df["Municipio"].str.strip()
    df["Año"]               = df["Año"].astype(int)
    df["Semana"]            = df["Semana"].astype(int)
    for c in ["Confirmados", "Descartados", "Pendientes por Ajuste"]:
        df[c] = pd.to_numeric(df[c], errors="coerce").fillna(0).astype(int)
    df["Total"] = df["Confirmados"] + df["Descartados"] + df["Pendientes por Ajuste"]
    return df

try:
    df_raw = load_data()
except Exception as e:
    st.error(f"Error al cargar datos: {e}")
    st.stop()

# ─────────────────────────────────────────────────────────────────────────────
# ESTADO DE SESIÓN
# ─────────────────────────────────────────────────────────────────────────────
if "year" not in st.session_state:
    st.session_state.year = 2026

# ─────────────────────────────────────────────────────────────────────────────
# SIDEBAR ── FILTROS (SIEMPRE PRIMERO para que Streamlit lo registre)
# ─────────────────────────────────────────────────────────────────────────────
# Necesitamos los datos del año antes de construir el sidebar
df_year_pre = df_raw[df_raw["Año"] == st.session_state.year].copy()

with st.sidebar:
    st.markdown(f"## 🔎 FILTROS  {st.session_state.year}")
    st.markdown("---")

    # ── Filtro por EVENTO ──
    st.markdown("### 📋 Evento Notificado")
    eventos_unicos = sorted(df_year_pre["Evento Notificado"].dropna().unique().tolist())
    sel_todo_ev = st.checkbox("☑ Seleccionar todos", value=True, key="ck_all_ev")
    if sel_todo_ev:
        eventos_sel = eventos_unicos
    else:
        eventos_sel = [ev for ev in eventos_unicos
                       if st.checkbox(ev, value=False, key=f"ck_ev_{ev}")]

    st.markdown("---")

    # ── Filtro por MUNICIPIO ──
    st.markdown("### 🏙️ Municipio")
    municipios_unicos = sorted(df_year_pre["Municipio"].dropna().unique().tolist())
    sel_todo_mu = st.checkbox("☑ Seleccionar todos", value=True, key="ck_all_mu")
    if sel_todo_mu:
        muni_sel = municipios_unicos
    else:
        muni_sel = [mu for mu in municipios_unicos
                    if st.checkbox(mu, value=False, key=f"ck_mu_{mu}")]

    st.markdown("---")

    # ── Filtro por SEMANA ──
    st.markdown("### 📅 Semana Epidemiológica")
    sem_min = int(df_year_pre["Semana"].min())
    sem_max = int(df_year_pre["Semana"].max())
    rango_sem = st.slider("Rango:", min_value=sem_min, max_value=sem_max,
                          value=(sem_min, sem_max), key="slider_sem")

# ─────────────────────────────────────────────────────────────────────────────
# CABECERA PRINCIPAL
# ─────────────────────────────────────────────────────────────────────────────
c_logo, c_b25, c_b26, c_titulo = st.columns([1.5, 1, 1, 5])
with c_logo:
    st.markdown(
        "<h2 style='margin:0; padding-top:14px; color:#2c3e70;'>FOMAG</h2>",
        unsafe_allow_html=True)
with c_b25:
    st.markdown("<div style='height:14px'></div>", unsafe_allow_html=True)
    if st.button("2025", key="btn2025",
                 type="primary" if st.session_state.year == 2025 else "secondary"):
        st.session_state.year = 2025
        st.rerun()
with c_b26:
    st.markdown("<div style='height:14px'></div>", unsafe_allow_html=True)
    if st.button("2026", key="btn2026",
                 type="primary" if st.session_state.year == 2026 else "secondary"):
        st.session_state.year = 2026
        st.rerun()
with c_titulo:
    st.markdown(
        f"<div style='text-align:right; padding-top:14px; font-size:1.7rem;"
        f" font-weight:900; color:#2c3e70;'>"
        f"EVENTOS NOTIFICADOS SIVIGILA — {st.session_state.year}</div>",
        unsafe_allow_html=True)

st.markdown("<hr style='border:2px solid #c3cbe8; margin-top:4px; margin-bottom:18px'>",
            unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────────────────────
# APLICAR FILTROS
# ─────────────────────────────────────────────────────────────────────────────
df_year = df_raw[df_raw["Año"] == st.session_state.year].copy()

if not eventos_sel:
    st.warning("Selecciona al menos un evento en el panel de filtros.")
    st.stop()

if not muni_sel:
    st.warning("Selecciona al menos un municipio en el panel de filtros.")
    st.stop()

df_f = df_year[
    df_year["Evento Notificado"].isin(eventos_sel) &
    df_year["Municipio"].isin(muni_sel) &
    df_year["Semana"].between(rango_sem[0], rango_sem[1])
]

if df_f.empty:
    st.info("No hay datos para la combinación de filtros seleccionada.")
    st.stop()

# ─────────────────────────────────────────────────────────────────────────────
# KPI CARDS
# ─────────────────────────────────────────────────────────────────────────────
conf  = int(df_f["Confirmados"].sum())
desc  = int(df_f["Descartados"].sum())
pend  = int(df_f["Pendientes por Ajuste"].sum())
total = int(df_f["Total"].sum())

k1, k2, k3, k4 = st.columns(4)
k1.markdown(f'<div class="kpi-card"><div class="kpi-label">Confirmados</div><div class="kpi-num">{conf}</div></div>', unsafe_allow_html=True)
k2.markdown(f'<div class="kpi-card green"><div class="kpi-label">Descartados</div><div class="kpi-num">{desc}</div></div>', unsafe_allow_html=True)
k3.markdown(f'<div class="kpi-card red"><div class="kpi-label">Pendientes</div><div class="kpi-num">{pend}</div></div>', unsafe_allow_html=True)
k4.markdown(f'<div class="kpi-card purple"><div class="kpi-label">Total General</div><div class="kpi-num">{total}</div></div>', unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────────────────────
# FILA 2: PIE + TABLA
# ─────────────────────────────────────────────────────────────────────────────
c_pie, c_tabla = st.columns([1, 1])

COLORES_MUNI = {
    "San José del Guaviare": "#1E88E5",
    "Calamar":               "#0D47A1",
    "El Retorno":            "#D81B60",
    "Miraflores":            "#8E24AA",
    "Puerto Concordia":      "#FFB300",
}

with c_pie:
    st.markdown('<div class="sec-title">TOTALES POR MUNICIPIO</div>', unsafe_allow_html=True)
    df_muni = df_f.groupby("Municipio")["Total"].sum().reset_index()
    fig_pie = px.pie(
        df_muni, values="Total", names="Municipio",
        color="Municipio", color_discrete_map=COLORES_MUNI,
    )
    fig_pie.update_traces(
        textposition="auto",
        textinfo="label+value+percent",
        textfont_size=14,
    )
    fig_pie.update_layout(
        height=420,
        margin=dict(t=10, b=10, l=10, r=10),
        showlegend=True,
        legend=dict(font=dict(size=13)),
        paper_bgcolor="rgba(0,0,0,0)",
    )
    st.plotly_chart(fig_pie, key="pie_chart", width="stretch")

with c_tabla:
    st.markdown('<div class="sec-title">RESUMEN POR MUNICIPIO</div>', unsafe_allow_html=True)
    df_t = (
        df_f.groupby("Municipio")[["Confirmados", "Descartados", "Pendientes por Ajuste", "Total"]]
        .sum()
        .reset_index()
        .sort_values("Total", ascending=False)
    )
    totales_row = pd.DataFrame([{
        "Municipio": "TOTAL",
        "Confirmados": conf, "Descartados": desc,
        "Pendientes por Ajuste": pend, "Total": total,
    }])
    df_t = pd.concat([df_t, totales_row], ignore_index=True)
    st.dataframe(
        df_t,
        hide_index=True,
        column_config={
            "Municipio":             st.column_config.TextColumn("Municipio", width="medium"),
            "Confirmados":           st.column_config.NumberColumn("Conf.",   format="%d"),
            "Descartados":           st.column_config.NumberColumn("Desc.",   format="%d"),
            "Pendientes por Ajuste": st.column_config.NumberColumn("Pend.",   format="%d"),
            "Total":                 st.column_config.NumberColumn("Total",   format="%d"),
        },
        width=700,
        height=420,
    )

st.markdown("<br>", unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────────────────────
# FILA 3: BARRAS APILADAS POR SEMANA
# ─────────────────────────────────────────────────────────────────────────────
st.markdown('<div class="sec-title">CASOS POR SEMANA EPIDEMIOLÓGICA</div>', unsafe_allow_html=True)

df_sem = (
    df_f.groupby("Semana")[["Confirmados", "Descartados", "Pendientes por Ajuste"]]
    .sum()
    .reset_index()
    .sort_values("Semana")
)
# Convertir a string para que el eje X trate cada semana como categoría independiente
df_sem["Semana"] = df_sem["Semana"].astype(str)

fig_bar = go.Figure()
fig_bar.add_trace(go.Bar(
    x=df_sem["Semana"], y=df_sem["Confirmados"],
    name="Confirmados", marker_color="#F57C00",
    text=df_sem["Confirmados"], textposition="inside",
    textfont=dict(size=12, color="white"),
))
fig_bar.add_trace(go.Bar(
    x=df_sem["Semana"], y=df_sem["Descartados"],
    name="Descartados", marker_color="#27AE60",
    text=df_sem["Descartados"], textposition="inside",
    textfont=dict(size=12, color="white"),
))
fig_bar.add_trace(go.Bar(
    x=df_sem["Semana"], y=df_sem["Pendientes por Ajuste"],
    name="Pendientes por Ajuste", marker_color="#C0392B",
    text=df_sem["Pendientes por Ajuste"], textposition="inside",
    textfont=dict(size=12, color="white"),
))
fig_bar.update_layout(
    barmode="stack",
    xaxis=dict(
        title="Semana Epidemiológica",
        type="category",
        tickmode="linear",
        tickangle=0,
        tickfont=dict(size=12),
        title_font=dict(size=14),
    ),
    yaxis=dict(
        title="Casos",
        tickfont=dict(size=13),
        title_font=dict(size=14),
        gridcolor="#ddd",
    ),
    legend=dict(orientation="h", y=1.08, x=0, font=dict(size=14)),
    margin=dict(t=50, b=30, l=20, r=20),
    plot_bgcolor="rgba(0,0,0,0)",
    paper_bgcolor="rgba(0,0,0,0)",
    height=480,
)
st.plotly_chart(fig_bar, key="bar_chart", width="stretch")

# ─────────────────────────────────────────────────────────────────────────────
# EXPANDER: TABLA DETALLADA
# ─────────────────────────────────────────────────────────────────────────────
with st.expander("📄 Ver registros detallados"):
    st.dataframe(
        df_f.sort_values(["Semana", "Evento Notificado"]),
        hide_index=True,
    )
    csv = df_f.to_csv(index=False).encode("utf-8")
    st.download_button(
        "⬇ Descargar CSV", csv,
        "eventos_filtrados.csv", "text/csv",
    )
