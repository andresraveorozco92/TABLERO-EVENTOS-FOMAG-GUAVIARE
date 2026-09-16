import streamlit as st
import pandas as pd
import sqlite3
import plotly.express as px
import plotly.graph_objects as go
import base64

with open("icono.png", "rb") as f:
    icono_b64 = base64.b64encode(f.read()).decode()

# ─────────────────────────────────────────────────────────────────────────────
# CONFIGURACIÓN DE PÁGINA — SIEMPRE PRIMERA
# ─────────────────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Tablero Epidemiológico FOMAG",
    page_icon="favicon.png",
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
    height: 65px !important;
    min-width: 140px !important;
    width: 100% !important;
    border-radius: 12px !important;
    letter-spacing: .08rem !important;
}
div.stButton > button p {
    font-size: 1.8rem !important;
    font-weight: 900 !important;
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
    # Columnas de sexo
    for c in ["Femenino", "Masculino"]:
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors="coerce").fillna(0).astype(int)
        else:
            df[c] = 0

    cursos = ["Primera Infancia", "Infancia", "Adolescencia", "Juventud", "Adultez", "Vejez"]
    for cv in cursos:
        for sx in ["Femenino", "Masculino"]:
            col_name = f"{cv} {sx}"
            if col_name in df.columns:
                df[col_name] = pd.to_numeric(df[col_name], errors="coerce").fillna(0).astype(int)
            else:
                df[col_name] = 0

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
c_logo, c_b25, c_b26, c_titulo = st.columns([1.5, 1.5, 1.5, 4.5])
with c_logo:
    st.markdown(
        f"<div style='display:flex; flex-direction:column; align-items:center; margin-top:-10px;'>"
        f"<img src='data:image/png;base64,{icono_b64}' width='120'/>"
        f"<div style='font-weight:900; color:#2c3e70; margin-top:5px; font-size:1.1rem; text-align:center;'>FOMAG GUAVIARE</div>"
        f"</div>",
        unsafe_allow_html=True
    )
with c_b25:
    st.markdown("<div style='height:28px'></div>", unsafe_allow_html=True)
    if st.button("2025", key="btn2025", use_container_width=True,
                 type="primary" if st.session_state.year == 2025 else "secondary"):
        st.session_state.year = 2025
        st.rerun()
with c_b26:
    st.markdown("<div style='height:28px'></div>", unsafe_allow_html=True)
    if st.button("2026", key="btn2026", use_container_width=True,
                 type="primary" if st.session_state.year == 2026 else "secondary"):
        st.session_state.year = 2026
        st.rerun()
with c_titulo:
    st.markdown(
        f"<div style='text-align:right; padding-top:35px; font-size:1.8rem;"
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
    st.warning("Selecciona al menos un evento notificado en el panel de filtros.")
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
fem   = int(df_f["Femenino"].sum())
masc  = int(df_f["Masculino"].sum())

k1, k2, k3, k4, k5, k6 = st.columns(6)
k1.markdown(f'<div class="kpi-card"><div class="kpi-label">Confirmados</div><div class="kpi-num">{conf}</div></div>', unsafe_allow_html=True)
k2.markdown(f'<div class="kpi-card green"><div class="kpi-label">Descartados</div><div class="kpi-num">{desc}</div></div>', unsafe_allow_html=True)
k3.markdown(f'<div class="kpi-card red"><div class="kpi-label">Pendientes</div><div class="kpi-num">{pend}</div></div>', unsafe_allow_html=True)
k4.markdown(f'<div class="kpi-card" style="border-top-color:#E91E8C"><div class="kpi-label">Femenino</div><div class="kpi-num" style="color:#E91E8C">{fem}</div></div>', unsafe_allow_html=True)
k5.markdown(f'<div class="kpi-card" style="border-top-color:#1976D2"><div class="kpi-label">Masculino</div><div class="kpi-num" style="color:#1976D2">{masc}</div></div>', unsafe_allow_html=True)
k6.markdown(f'<div class="kpi-card purple"><div class="kpi-label">Total General</div><div class="kpi-num">{total}</div></div>', unsafe_allow_html=True)

st.markdown("<div style='margin-top:12px'></div>", unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────────────────────
# FILA 2: PIE | TABLA RESUMEN | GRÁFICO SEXO (BARRAS APILADAS)
# ─────────────────────────────────────────────────────────────────────────────
c_pie, c_tabla, c_sexo = st.columns([1.15, 1, 1])

COLORES_MUNI = {
    "San José del Guaviare": "#1E88E5",
    "Calamar":               "#0D47A1",
    "El Retorno":            "#D81B60",
    "Miraflores":            "#8E24AA",
    "Puerto Concordia":      "#FFB300",
}

# ── PIE ──
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
        textfont_size=16,
    )
    fig_pie.update_layout(
        height=360,
        margin=dict(t=10, b=10, l=10, r=10),
        showlegend=True,
        legend=dict(font=dict(size=13)),
        paper_bgcolor="rgba(0,0,0,0)",
    )
    st.plotly_chart(fig_pie, key="pie_chart", width="stretch")

# ── TABLA RESUMEN ──
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
        width=520,
    )

# ── GRÁFICO SEXO POR MUNICIPIO (BARRAS APILADAS HORIZONTALES) ──
with c_sexo:
    st.markdown('<div class="sec-title">CASOS POR SEXO Y MUNICIPIO</div>', unsafe_allow_html=True)
    df_sexo = (
        df_f.groupby("Municipio")[["Femenino", "Masculino"]]
        .sum()
        .reset_index()
    )
    df_sexo["Total_Sexo"] = df_sexo["Femenino"] + df_sexo["Masculino"]
    df_sexo = df_sexo.sort_values("Total_Sexo", ascending=False)

    fig_sexo = go.Figure()
    fig_sexo.add_trace(go.Bar(
        y=df_sexo["Municipio"], x=df_sexo["Femenino"],
        name="Femenino", marker_color="#E91E8C",
        orientation="h",
        text=[str(v) if v > 0 else "" for v in df_sexo["Femenino"]],
        textposition="inside",
        insidetextanchor="middle",
        textfont=dict(size=16, color="white"),
    ))
    fig_sexo.add_trace(go.Bar(
        y=df_sexo["Municipio"], x=df_sexo["Masculino"],
        name="Masculino", marker_color="#1976D2",
        orientation="h",
        text=[str(v) if v > 0 else "" for v in df_sexo["Masculino"]],
        textposition="inside",
        insidetextanchor="middle",
        textfont=dict(size=16, color="white"),
    ))
    fig_sexo.update_layout(
        barmode="stack",
        bargap=0.18,
        xaxis=dict(
            title="Casos",
            tickfont=dict(size=13),
            title_font=dict(size=14, color="#2c3e70"),
            gridcolor="#ddd",
        ),
        yaxis=dict(
            autorange="reversed",
            tickfont=dict(size=13, color="#2c3e70"),
            title_font=dict(size=13),
        ),
        legend=dict(orientation="h", y=1.12, x=0, font=dict(size=14)),
        margin=dict(t=40, b=10, l=10, r=10),
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        height=370,
    )
    st.plotly_chart(fig_sexo, key="sexo_chart", width="stretch")

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
df_sem["Semana"] = df_sem["Semana"].astype(str)

fig_bar = go.Figure()
fig_bar.add_trace(go.Bar(
    x=df_sem["Semana"], y=df_sem["Confirmados"],
    name="Confirmados", marker_color="#F57C00",
    text=[str(v) if v > 0 else "" for v in df_sem["Confirmados"]],
    textposition="inside",
    textfont=dict(size=16, color="white"),
))
fig_bar.add_trace(go.Bar(
    x=df_sem["Semana"], y=df_sem["Descartados"],
    name="Descartados", marker_color="#27AE60",
    text=[str(v) if v > 0 else "" for v in df_sem["Descartados"]],
    textposition="inside",
    textfont=dict(size=16, color="white"),
))
fig_bar.add_trace(go.Bar(
    x=df_sem["Semana"], y=df_sem["Pendientes por Ajuste"],
    name="Pendientes por Ajuste", marker_color="#C0392B",
    text=[str(v) if v > 0 else "" for v in df_sem["Pendientes por Ajuste"]],
    textposition="inside",
    textfont=dict(size=16, color="white"),
))
fig_bar.update_layout(
    barmode="stack",
    xaxis=dict(
        title="Semana Epidemiológica",
        type="category",
        tickmode="linear",
        tickangle=0,
        tickfont=dict(size=14),
        title_font=dict(size=15),
    ),
    yaxis=dict(
        title="Casos",
        tickfont=dict(size=14),
        title_font=dict(size=15),
        gridcolor="#ddd",
    ),
    legend=dict(orientation="h", y=1.08, x=0, font=dict(size=14)),
    margin=dict(t=50, b=30, l=20, r=20),
    plot_bgcolor="rgba(0,0,0,0)",
    paper_bgcolor="rgba(0,0,0,0)",
    height=380,
)
st.plotly_chart(fig_bar, key="bar_chart", width="stretch")

# ─────────────────────────────────────────────────────────────────────────────
# FILA 4: CASOS POR MUNICIPIO, CURSO DE VIDA Y SEXO (BARRAS APILADAS)
# ─────────────────────────────────────────────────────────────────────────────
st.markdown('<div class="sec-title">CASOS POR MUNICIPIO, CURSO DE VIDA Y SEXO</div>', unsafe_allow_html=True)

cursos_lista = ["Primera Infancia", "Infancia", "Adolescencia", "Juventud", "Adultez", "Vejez"]

# Ordenar municipios de mayor a menor según el total de casos
muni_ordenados = (
    df_f.groupby("Municipio")["Total"]
    .sum()
    .sort_values(ascending=False)
    .index.tolist()
)

rows_cv = []
for muni in muni_ordenados:
    df_m = df_f[df_f["Municipio"] == muni]
    for c in cursos_lista:
        fem_c = f"{c} Femenino"
        masc_c = f"{c} Masculino"
        fem_v = int(df_m[fem_c].sum()) if fem_c in df_m.columns else 0
        masc_v = int(df_m[masc_c].sum()) if masc_c in df_m.columns else 0
        rows_cv.append({
            "Municipio": muni,
            "Curso de Vida": c,
            "Femenino": fem_v,
            "Masculino": masc_v,
            "Total": fem_v + masc_v,
        })

df_cv = pd.DataFrame(rows_cv)

fig_cv = go.Figure()
fig_cv.add_trace(go.Bar(
    x=[df_cv["Municipio"], df_cv["Curso de Vida"]],
    y=df_cv["Femenino"],
    name="Femenino",
    marker_color="#E91E8C",
    text=[str(v) if v > 0 else "" for v in df_cv["Femenino"]],
    textposition="inside",
    insidetextanchor="middle",
    textfont=dict(size=15, color="white"),
))
fig_cv.add_trace(go.Bar(
    x=[df_cv["Municipio"], df_cv["Curso de Vida"]],
    y=df_cv["Masculino"],
    name="Masculino",
    marker_color="#1976D2",
    text=[str(v) if v > 0 else "" for v in df_cv["Masculino"]],
    textposition="inside",
    insidetextanchor="middle",
    textfont=dict(size=15, color="white"),
))
fig_cv.update_layout(
    barmode="stack",
    bargap=0.15,
    xaxis=dict(
        title="",
        tickangle=-90,
        tickfont=dict(size=12, color="#2c3e70"),
    ),
    yaxis=dict(
        title="Casos",
        tickfont=dict(size=14),
        title_font=dict(size=15, color="#2c3e70"),
        gridcolor="#ddd",
    ),
    legend=dict(orientation="h", y=1.08, x=0, font=dict(size=14)),
    margin=dict(t=50, b=90, l=20, r=20),
    plot_bgcolor="rgba(0,0,0,0)",
    paper_bgcolor="rgba(0,0,0,0)",
    height=520,
)
st.plotly_chart(fig_cv, key="cv_chart", width="stretch")
