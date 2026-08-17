import streamlit as st
import pandas as pd
import numpy as np
import math
import os
import base64
from datetime import datetime
from snowflake.snowpark.context import get_active_session

session = get_active_session()

# Eleva o limite de células que o pandas Styler pode renderizar
pd.set_option("styler.render.max_elements", 10_000_000)

st.set_page_config(page_title="Análise Timesheet", layout="wide")


# ════════════════════════════════════════════════════════════════════════════
# CONFIGURAÇÃO GERAL
# Nomes genéricos de tabelas, cores do tema e metas dos indicadores.
# ════════════════════════════════════════════════════════════════════════════
T_KPI   = "SUA_BASE.SEMANTICS.RESUMO_TIMESHEET_KPI"
T_TS    = "SUA_BASE.SEMANTICS.OBT_TIMESHEETS"
T_UNID  = "SUA_BASE.MARTS.DIM_UNIDADE"
T_DATA  = "SUA_BASE.MARTS.DIM_DATA"
T_CTRL  = "SUA_BASE.SEMANTICS.CONTROLE_DATA_HORA"
T_COLAB = "SUA_BASE.SEMANTICS.RESUMO_COLABORADOR"
T_CAT   = "SUA_BASE.SEMANTICS.RESUMO_CATEGORIA"

AZUL_HEADER = "#1B2A4A"
VERDE, AMARELO = "#2e9e5b", "#e8c33d"
META_ADERENCIA, META_PRAZO = 90, 80


# ════════════════════════════════════════════════════════════════════════════
# CROSS-FILTER
# ════════════════════════════════════════════════════════════════════════════
if "xfilter" not in st.session_state:
    st.session_state.xfilter = {"dim": None, "val": None, "src": None}

def _set_xfilter(dim, val, src):
    cur = st.session_state.xfilter
    if cur.get("dim") == dim and cur.get("val") == val:
        return
    st.session_state.xfilter = {"dim": dim, "val": val, "src": src}
    st.rerun()

def _clear_xfilter():
    if st.session_state.xfilter.get("dim") is not None:
        st.session_state.xfilter = {"dim": None, "val": None, "src": None}
        st.rerun()

_XF_ALIASES = {
    "colaborador": ["colaborador", "Colaborador"],
    "hierarquia":  ["hierarquia", "Hierarquia"],
    "conta":       ["conta", "Conta"],
    "atividade":   ["atividade", "Atividade"],
    "area":        ["area", "Área"],
}

def _aplica_xfilter(d):
    xf = st.session_state.xfilter
    dim, val = xf.get("dim"), xf.get("val")
    if not dim or val is None or d is None or len(d) == 0:
        return d
    for col in _XF_ALIASES.get(dim, [dim]):
        if col in d.columns:
            return d[d[col] == val]
    return d


# ════════════════════════════════════════════════════════════════════════════
# ESTILO (CSS)
# ════════════════════════════════════════════════════════════════════════════
st.markdown("""<style>
.stApp {background-color:#eef1f5}
[data-testid="stMainBlockContainer"] {
    background-color:#eef1f5;
    padding-top:0.4rem;
    padding-bottom:0rem !important;
    padding-left:1.2rem;
    padding-right:1.2rem;
    max-width:100% !important;
    width:100% !important;
}
[data-testid="stHeader"] {background-color:#eef1f5}
h1,h2,h3,h4,h5,h6,p,span,label {color:#111111;}

[data-testid="stVerticalBlockBorderWrapper"] {
    background: transparent !important;
    border: none !important;
    box-shadow: none !important;
    padding: 0 !important;
}

div[data-testid="stSelectbox"] label p {font-size:0.82rem !important; color:#5b6473 !important; font-weight:600 !important;}
div[data-baseweb="select"] > div {background:#ffffff !important; border:1px solid #cfd6df !important; border-radius:6px !important; min-height:38px !important;}
div[data-baseweb="select"] span {color:#111111 !important;}
div[data-baseweb="select"] svg {color:#1a1a1a !important; fill:#1a1a1a !important;}
ul[role="listbox"] li, li[role="option"] {background:#ffffff !important; color:#111111 !important;}
li[role="option"]:hover, li[role="option"][aria-selected="true"] {background:#eef2f8 !important;}

.custom-card {
    background: #ffffff; border: 1px solid #e4e7ec; border-radius: 10px;
    box-shadow: 0 1px 3px rgba(16,24,40,0.06); padding: 20px; height: 225px;
    display: flex; flex-direction: column; justify-content: space-between;
    box-sizing: border-box; overflow: hidden;
}

.kpi-num {font-size:2.3rem; font-weight:300; color:#1a1a1a; line-height:1; text-align:center;}
.kpi-lbl {font-size:0.92rem; color:#3a4250; text-align:center; font-weight:600;}
.kpi-sub {font-size:0.8rem; color:#7a828f; text-align:center; margin-top:2px;}
.delta-up {color:#2e9e5b; font-weight:600; font-size:0.85rem;}
.delta-down {color:#e8c33d; font-weight:600; font-size:0.85rem;}
.gauge-title {font-size:0.95rem; color:#3a4250; margin:0; text-align:center; font-weight:600;}

.section-title {font-size:0.95rem; font-weight:700; color:#1B2A4A; margin:0 0 8px 0;}

[data-testid="stDataFrame"],
[data-testid="stDataFrame"] > div,
[data-testid="stDataFrame"] canvas {background-color:#ffffff !important;}
[data-testid="stDataFrameResizable"] {
    background-color:#ffffff !important;
    --gdg-bg-cell:#ffffff !important;
    --gdg-bg-cell-medium:#f5f7fa !important;
    --gdg-bg-header:#f4f6f9 !important;
    --gdg-bg-header-has-focus:#eef2f8 !important;
    --gdg-bg-header-hovered:#eef2f8 !important;
    --gdg-text-dark:#111111 !important;
    --gdg-text-header:#3a4250 !important;
    --gdg-text-light:#333333 !important;
    --gdg-border-color:#e4e7ec !important;
    --gdg-cell-horizontal-padding:8px !important;
    --gdg-text-align: center !important;
}
[data-testid="stDataFrame"] ::-webkit-scrollbar {width:11px; height:11px;}
[data-testid="stDataFrame"] ::-webkit-scrollbar-track {background:#ffffff !important;}
[data-testid="stDataFrame"] ::-webkit-scrollbar-thumb {background:#c3ccd8 !important; border-radius:6px; border:2px solid #ffffff;}
[data-testid="stDataFrame"] ::-webkit-scrollbar-thumb:hover {background:#aab3c0 !important;}

[data-testid="stDataFrame"] input[type="checkbox"] {display:none !important;}
[data-testid="stDataFrame"] [data-testid="stDataFrameSelectionColumn"] {display:none !important;}
[data-testid="stDataFrame"] .gdg-cell-marker,
[data-testid="stDataFrame"] .gdg-header-marker {display:none !important;}
</style>""", unsafe_allow_html=True)


# ════════════════════════════════════════════════════════════════════════════
# RLS — ROW-LEVEL SECURITY
# ════════════════════════════════════════════════════════════════════════════
def _detectar_usuario_snowflake():
    try:
        r = session.sql("SELECT CURRENT_USER() AS U").to_pandas()
        v = r.iloc[0]["U"]
        if v and str(v).strip().lower() not in ("none", "", "nan", "snowflake"):
            return str(v).strip()
    except Exception:
        pass
    return ""

@st.cache_data(ttl=600)
def _buscar_colaborador_rls(ident):
    if not ident:
        return (None, None, None)
    try:
        ident_ponto = ident.replace("_", ".")
        q = f"""
            SELECT COLABORADOR_NOME,
                   UNIDADECC_COD AS UNIDADE,
                   AREA_NOME
            FROM SUA_BASE.SEMANTICS.OBT_COLABORADORES
            WHERE ESTA_ATIVO = TRUE AND (
                LOWER(USUARIO_AD) = LOWER('{ident}')
                OR LOWER(EMAIL_AD) = LOWER('{ident}')
                OR LOWER(EMAIL)    = LOWER('{ident}')
                OR LOWER(ALIAS_USUARIO) = LOWER('{ident}')
                OR LOWER(SPLIT_PART(EMAIL, '@', 1)) = LOWER('{ident_ponto}')
                OR LOWER(SPLIT_PART(EMAIL_AD, '@', 1)) = LOWER('{ident_ponto}')
            )
            LIMIT 1
        """
        r = session.sql(q).to_pandas()
        if r.empty:
            return (None, None, None)
        return (r.iloc[0]["COLABORADOR_NOME"],
                str(r.iloc[0]["UNIDADE"] or "").strip(),
                str(r.iloc[0]["AREA_NOME"] or "").strip())
    except Exception:
        return (None, None, None)

_rls_ident = _detectar_usuario_snowflake()
_rls_nome, _rls_unidade, _rls_area = _buscar_colaborador_rls(_rls_ident)

_AREAS_ADMIN = {"ADMINISTRATIVO", "DIRETORIA"}
if not _rls_ident or not _rls_nome:
    _rls_is_admin = True
    _rls_liberado = False
    _rls_nome = None
else:
    _rls_is_admin = (_rls_area or "").upper() in _AREAS_ADMIN
    _rls_liberado = (_rls_area or "").upper() == "ADMINISTRATIVO"

def _rls_where(col_unidade="UNIDADE_COLABORADOR_CENTRO_DE_CUSTO_NOME",
               col_area="COLABORADOR_AREA_NOME"):
    if _rls_is_admin:
        return ""
    clauses = []
    if _rls_area:
        clauses.append(f"{col_area} = '{_rls_area}'")
    if not clauses:
        return ""
    return " AND " + " AND ".join(clauses)


def _sql_lit(v):
    return str(v).replace("'", "''")


# ════════════════════════════════════════════════════════════════════════════
# CARGA DE DADOS
# ════════════════════════════════════════════════════════════════════════════
@st.cache_data(ttl=600)
def load_kpi(_rls_u=None, _rls_a=None):
    return session.sql(f"""
        SELECT
            UNIDADE_COLABORADOR_LOCAL_DE_TRABALHO    AS unidade,
            UNIDADE_COLABORADOR_LOCAL_DE_TRABALHO    AS unidade_cod,
            COLABORADOR_AREA_NOME                   AS area,
            MES_REFERENCIA                          AS mes_ref,
            CARGA_HORARIA_POR_MES_MINUTOS           AS carga_min,
            MINUTOS_TRABALHADOS_NO_MES              AS min_trab,
            MINUTOS_LANCAMENTO_NO_PRAZO             AS min_prazo,
            MINUTOS_EM_CLIENTE_INTERNO              AS min_cli_int,
            MINUTOS_EM_CLIENTE_EXTERNO              AS min_cli_ext,
            MINUTOS_EM_CLIENTE_EXTERNO_A_FATURAR    AS min_cli_ext_fat,
            PCNT_PRODUTIVIDADE_MAXIMA               AS pct_prod,
            PCNT_PRODUTIVIDADE_MAXIMA_MES_ANTERIOR  AS pct_prod_ant,
            PCNT_LANCAMENTO_EM_ATRASO               AS pct_atraso,
            PCNT_LANCAMENTO_NO_PRAZO                AS pct_prazo,
            PCNT_LANCAMENTO_NO_PRAZO_MES_ANTERIOR   AS pct_prazo_ant,
            PCNT_CLIENTES_EXTERNOS                  AS pct_cli_ext,
            PCNT_CLIENTES_EXTERNOS_MES_ANTERIOR     AS pct_cli_ext_ant,
            PCNT_CLIENTE_EXTERNO_A_FATURAR          AS pct_cli_ext_fat,
            PCNT_CLIENTE_EXTERNO_A_FATURAR_MES_ANTERIOR AS pct_cli_ext_fat_ant
        FROM {T_KPI}
        WHERE 1=1
        {_rls_where()}
    """).to_pandas()

@st.cache_data(ttl=600)
def load_unidades():
    return ["UNIDADE_A", "UNIDADE_B", "UNIDADE_C"]

@st.cache_data(ttl=600)
def load_areas():
    return session.sql(f"SELECT DISTINCT COLABORADOR_AREA_NOME FROM {T_TS} WHERE COLABORADOR_AREA_NOME IS NOT NULL ORDER BY COLABORADOR_AREA_NOME").to_pandas()["COLABORADOR_AREA_NOME"].astype(str).tolist()

@st.cache_data(ttl=600)
def load_meses():
    try:
        df_m = session.sql(
            f"SELECT DISTINCT DATA_MES_REFERENCIA AS M FROM {T_DATA} "
            f"WHERE DATA_MES_REFERENCIA IS NOT NULL ORDER BY M DESC"
        ).to_pandas()
        return df_m["M"].astype(str).tolist()
    except Exception:
        return []

@st.cache_data(ttl=600)
def load_atualizacoes():
    try:
        df = session.sql(f"""
            SELECT FONTE_DADOS AS fonte, DATA_HORA_EXTRACAO_MAIS_ANTIGA AS dt_hora
            FROM {T_CTRL}
            WHERE FONTE_DADOS IN ('sistema_a', 'sistema_b')
            ORDER BY FONTE_DADOS
        """).to_pandas()
        df.columns = [c.lower() for c in df.columns]
        df["fonte"] = df["fonte"].astype(str).str.strip().str.lower()
        df["dt_hora"] = pd.to_datetime(df["dt_hora"], errors="coerce")
        return df
    except Exception:
        return pd.DataFrame(columns=["fonte", "dt_hora"])

kpi = load_kpi(_rls_unidade, _rls_area)
kpi.columns = [str(c).lower() for c in kpi.columns]
if "mes_ref" not in kpi.columns:
    st.error("A coluna 'mes_ref' não veio da consulta.")
    st.stop()
kpi["mes_ref"] = pd.to_datetime(kpi["mes_ref"], errors="coerce")
kpi["mes_txt"] = kpi["mes_ref"].dt.strftime("%Y-%m")

unidades_lst = load_unidades()
areas_lst    = load_areas()
meses_raw    = load_meses()
df_atu       = load_atualizacoes()
if not meses_raw:
    meses_raw = sorted(kpi["mes_txt"].dropna().unique().tolist(), reverse=True)

hoje = datetime.today()
meses_filtrados = []
for m in meses_raw:
    dt_parsed = pd.to_datetime(m, errors="coerce")
    if pd.notna(dt_parsed):
        if dt_parsed.year >= 2024 and dt_parsed <= datetime(hoje.year, hoje.month, 1):
            meses_filtrados.append(dt_parsed.strftime("%Y-%m-%d"))
meses_filtrados = sorted(list(set(meses_filtrados)), reverse=True)


# ════════════════════════════════════════════════════════════════════════════
# HEADER
# ════════════════════════════════════════════════════════════════════════════
def _atu_linha(fonte):
    row = df_atu[df_atu["fonte"] == fonte]
    if row.empty or pd.isna(row.iloc[0]["dt_hora"]):
        return "—"
    return row.iloc[0]["dt_hora"].strftime("%d/%m/%Y %H:%M:%S")

linhas_atu = "".join(
    f'<tr><td style="color:#dbe2ec;padding:2px 12px 2px 0;font-size:0.8rem;">{fonte}</td>'
    f'<td style="color:#a8bcd4;padding:2px 0;font-size:0.8rem;">{_atu_linha(fonte)}</td></tr>'
    for fonte in ["sistema_a", "sistema_b"]
)

st.markdown(f"""
<div style="background:linear-gradient(90deg,#132339 0%,{AZUL_HEADER} 45%,#294a7d 100%);
            padding:26px 28px; border-radius:8px; margin-bottom:14px;
            display:flex; justify-content:space-between; align-items:center;">
    <div>
        <h1 style="color:#ffffff; margin:0; font-size:1.75rem; font-weight:700;">Análise Timesheet</h1>
        <p style="color:#c7d0dc; margin:3px 0 0 0; font-size:0.9rem;">Visão Geral do Projeto</p>
    </div>
    <div style="text-align:right;">
        <div style="color:#ffffff; font-weight:600; font-size:0.85rem; margin-bottom:6px;">&#9432; Últimas atualizações</div>
        <table style="border-collapse:collapse; margin-left:auto;">{linhas_atu}</table>
    </div>
</div>
""", unsafe_allow_html=True)


# ════════════════════════════════════════════════════════════════════════════
# INDICADOR RLS
# ════════════════════════════════════════════════════════════════════════════
if not _rls_ident or not _rls_nome:
    _txt_rls = "**Dashboard liberado para visualização.**"
elif _rls_liberado:
    _txt_rls = f"Usuário: **{_rls_nome}** · **Dashboard Liberado**"
elif _rls_is_admin:
    _txt_rls = f"Usuário: **{_rls_nome}** · **ADMIN**"
elif _rls_area:
    _txt_rls = f"Usuário: **{_rls_nome}** · Área: **{_rls_area}**"
else:
    _txt_rls = f"Usuário: **{_rls_nome or _rls_ident or 'não identificado'}**"
st.caption(_txt_rls)

_xf = st.session_state.xfilter
if _xf.get("dim") and _xf.get("val") is not None:
    _lbl = {"colaborador": "Colaborador", "hierarquia": "Hierarquia",
            "conta": "Cliente/Conta", "atividade": "Atividade",
            "area": "Área"}.get(_xf["dim"], _xf["dim"])
    _cf1, _cf2 = st.columns([6, 1])
    with _cf1:
        st.info(f"🔗 Filtro por clique ativo — {_lbl}: **{_xf['val']}**  ·  clique na linha de novo para desmarcar")
    with _cf2:
        if st.button("Limpar filtro", use_container_width=True):
            _clear_xfilter()


# ════════════════════════════════════════════════════════════════════════════
# FILTROS DE TOPO
# ════════════════════════════════════════════════════════════════════════════
c_rep, c_a, c_m = st.columns([1.4, 1.6, 1.6])
with c_rep:
    st.markdown(f"<a href='#' target='_blank' style='text-decoration:none;'><div style='background:#2c4266;color:#e5ebf3;padding:9px 14px;border-radius:6px;text-align:center;font-size:0.85rem;font-weight:600;margin-top:28px;'>Reportar um problema</div></a>", unsafe_allow_html=True)
with c_a:
    sel_area = st.selectbox("Área", ["Todas"] + areas_lst, key="f_area")
sel_unidade = "Todas"
with c_m:
    def _fmt_mes(v):
        dt = pd.to_datetime(v, errors="coerce")
        return dt.strftime("%m/%Y") if pd.notna(dt) else str(v)
    sel_mes = st.selectbox("Ano/Mês", meses_filtrados if meses_filtrados else ["—"],
                           format_func=_fmt_mes, key="f_mes")

sel_dt = pd.to_datetime(sel_mes, errors="coerce")
sel_mes_txt = sel_dt.strftime("%Y-%m") if pd.notna(sel_dt) else str(sel_mes)[:7]

def filtra(d):
    d = d.copy()
    if sel_unidade != "Todas":
        d = d[d["unidade"].str.contains(sel_unidade, na=False)]
    if sel_area != "Todas":
        d = d[d["area"] == sel_area]
    return d

kpi_mes = filtra(kpi[kpi["mes_txt"] == sel_mes_txt])


# ════════════════════════════════════════════════════════════════════════════
# CÁLCULO DOS KPIs
# ════════════════════════════════════════════════════════════════════════════
def col_sum(d, c):
    return d[c].fillna(0).sum() if c in d.columns and len(d) else 0

def col_wavg(d, c, w):
    if c not in d.columns or w not in d.columns or len(d) == 0:
        return 0
    vals = pd.to_numeric(d[c], errors="coerce").fillna(0)
    pesos = pd.to_numeric(d[w], errors="coerce").fillna(0)
    total = pesos.sum()
    if total <= 0:
        return vals.mean() if len(vals) else 0
    return float((vals * pesos).sum() / total)

carga_min   = col_sum(kpi_mes, "carga_min")
min_trab    = col_sum(kpi_mes, "min_trab")
min_prazo   = col_sum(kpi_mes, "min_prazo")
min_cli_int = col_sum(kpi_mes, "min_cli_int")
min_cli_ext = col_sum(kpi_mes, "min_cli_ext")
min_cli_fat = col_sum(kpi_mes, "min_cli_ext_fat")

pct_prod       = col_wavg(kpi_mes, "pct_prod", "carga_min")
pct_prod_ant   = col_wavg(kpi_mes, "pct_prod_ant", "carga_min")
pct_atraso     = col_wavg(kpi_mes, "pct_atraso", "min_trab")
pct_prazo      = col_wavg(kpi_mes, "pct_prazo", "min_trab")
pct_prazo_ant  = col_wavg(kpi_mes, "pct_prazo_ant", "min_trab")
pct_cliext     = col_wavg(kpi_mes, "pct_cli_ext", "min_trab")
pct_cliext_ant = col_wavg(kpi_mes, "pct_cli_ext_ant", "min_trab")
pct_clifat     = col_wavg(kpi_mes, "pct_cli_ext_fat", "min_trab")
pct_clifat_ant = col_wavg(kpi_mes, "pct_cli_ext_fat_ant","min_trab")

def pct100(v):
    if v is None or (isinstance(v, float) and math.isnan(v)):
        return 0
    return int(round(v * 100)) if abs(v) <= 1.5 else int(round(v))

horas_disp  = carga_min/60 if carga_min else 0
horas_lanc  = min_trab/60
horas_prazo = min_prazo/60
horas_cli   = (min_cli_int + min_cli_ext)/60
horas_fat   = min_cli_fat/60

ader_i   = pct100(pct_prod)
prazo_i  = pct100(1 - pct_atraso) if abs(pct_atraso) <= 1.5 else pct100(100 - pct_atraso)
cliext_i = pct100(pct_cliext)
clifat_i = pct100(pct_clifat)

var_ader  = pct100(pct_prod) - pct100(pct_prod_ant)
var_prazo = pct100(pct_prazo) - pct100(pct_prazo_ant)
var_cli   = pct100(pct_cliext) - pct100(pct_cliext_ant)
var_fat   = pct100(pct_clifat) - pct100(pct_clifat_ant)

def delta_html(v):
    if v > 0: return f"<span class='delta-up'>▲ {v}%</span>"
    if v < 0: return f"<span class='delta-down'>▼ {v}%</span>"
    return f"<span style='color:#7a828f;font-size:0.85rem'>{v}%</span>"

def fmt(n):
    return f"{n:,.0f}".replace(",", ".")

def _safe_int(v):
    try:
        f = float(v)
    except (TypeError, ValueError):
        return 0
    if f != f or f in (float("inf"), float("-inf")):
        return 0
    return int(round(f))

def gauge_svg(value, meta, cor):
    value = max(0, min(100, _safe_int(value)))
    meta  = max(0, min(100, _safe_int(meta)))
    R, CX, CY = 65, 100, 90
    STROKE = 14
    def xy(pct, rr=R):
        a = math.pi * (1.0 - pct / 100.0)
        return CX + rr * math.cos(a), CY - rr * math.sin(a)
    xL, yL = xy(0); xR, yR = xy(100); xVal, yVal = xy(value)
    arco_valor = ""
    if value > 0:
        d_val = f"M {xL:.2f},{yL:.2f} A {R},{R} 0 0 1 {xVal:.2f},{yVal:.2f}"
        arco_valor = (f"<path d='{d_val}' fill='none' stroke='{cor}' "
                      f"stroke-width='{STROKE}' stroke-linecap='round'/>")
    mxi, myi = xy(meta, R - STROKE/2 - 2)
    mxo, myo = xy(meta, R + STROKE/2 + 2)
    lx, ly   = xy(meta, R + STROKE/2 + 14)
    return (
        '<svg viewBox="0 0 200 112" xmlns="http://www.w3.org/2000/svg" '
        'style="width:100%;max-width:180px;display:block;margin:0 auto;">'
        f'<path d="M {xL:.2f},{yL:.2f} A {R},{R} 0 0 1 {xR:.2f},{yR:.2f}" '
        f'fill="none" stroke="#e4e7ec" stroke-width="{STROKE}" stroke-linecap="round"/>'
        f'{arco_valor}'
        f'<line x1="{mxi:.2f}" y1="{myi:.2f}" x2="{mxo:.2f}" y2="{myo:.2f}" '
        'stroke="#2b2b2b" stroke-width="2"/>'
        f'<text x="{lx:.2f}" y="{ly:.2f}" font-size="9" fill="#2b2b2b" '
        f'text-anchor="middle" dominant-baseline="middle">{meta}%</text>'
        f'<text x="{CX}" y="{CY-8}" font-size="24" font-weight="700" fill="{cor}" '
        f'text-anchor="middle">{value}%</text>'
        '</svg>'
    )


# ════════════════════════════════════════════════════════════════════════════
# CARDS DE KPI
# ════════════════════════════════════════════════════════════════════════════
c1, c2, c3 = st.columns(3)
with c1:
    st.markdown(f"""
    <div class="custom-card">
        <div class="kpi-lbl" style="text-align:left; visibility:hidden;">&nbsp;</div>
        <div class="kpi-num">{fmt(horas_disp)}</div>
        <div><div class="kpi-lbl">horas úteis disponíveis</div></div>
    </div>""", unsafe_allow_html=True)
with c2:
    cor_ader = VERDE if ader_i >= META_ADERENCIA else AMARELO
    st.markdown(f"""
    <div class="custom-card">
        <div class="gauge-title">Aderência ao Lançamento</div>
        {gauge_svg(ader_i, META_ADERENCIA, cor_ader)}
        <div style="text-align:center; margin-top:2px;">
            {delta_html(var_ader)}
            <div class="kpi-sub">{fmt(horas_lanc)} horas lançadas</div>
        </div>
    </div>""", unsafe_allow_html=True)
with c3:
    cor_prazo = VERDE if prazo_i >= META_PRAZO else AMARELO
    st.markdown(f"""
    <div class="custom-card">
        <div class="gauge-title">Horas Lançadas no Prazo</div>
        {gauge_svg(prazo_i, META_PRAZO, cor_prazo)}
        <div style="text-align:center; margin-top:2px;">
            {delta_html(var_prazo)}
            <div class="kpi-sub">{fmt(horas_prazo)} horas no prazo</div>
        </div>
    </div>""", unsafe_allow_html=True)

st.markdown("<div style='margin-top: 15px;'></div>", unsafe_allow_html=True)


# ════════════════════════════════════════════════════════════════════════════
# ANÁLISE POR UNIDADES
# ════════════════════════════════════════════════════════════════════════════
def _dados_por_area(d):
    if d is None or len(d) == 0:
        return pd.DataFrame(columns=["area", "carga", "lanc", "prazo"])
    d = d.copy()
    d["_grp"] = d["unidade_cod"].astype(str).str.strip()
    g = d.groupby("_grp", dropna=True).agg(
        carga=("carga_min", "sum"),
        lanc=("min_trab", "sum"),
        prazo=("min_prazo", "sum"),
    ).reset_index().rename(columns={"_grp": "area"})
    g = g[(g["area"].astype(str).str.strip() != "") & (g["area"].str.lower() != "none")]
    return g.sort_values("area").reset_index(drop=True)

def _barra_html(pct, meta):
    pct = _safe_int(pct)
    cor = VERDE if pct >= meta else AMARELO
    pct_larg = max(0, min(100, pct))
    if pct_larg >= 88:
        txt = (f"<div style='position:absolute; right:8px; top:50%; transform:translateY(-50%); "
               f"font-size:0.8rem; font-weight:700; color:#111111; white-space:nowrap;'>{pct}%</div>")
    else:
        txt = (f"<div style='position:absolute; left:{pct_larg}%; top:50%; transform:translateY(-50%); "
               f"padding-left:6px; font-size:0.8rem; font-weight:700; color:#111111; "
               f"white-space:nowrap;'>{pct}%</div>")
    return (
        "<div style='position:relative; width:100%; height:30px; background:#e4e7ec; "
        "border-radius:3px; overflow:hidden;'>"
        f"<div style='position:absolute; left:0; top:0; width:{pct_larg}%; height:100%; "
        f"background:{cor};'></div>"
        f"{txt}"
        "</div>"
    )

def _html_escape(s):
    return (str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;"))

def _coluna_analise(titulo, df_area, tipo, meta):
    linhas = ""
    for _, r in df_area.iterrows():
        area = str(r["area"])
        carga = _safe_int(r["carga"] / 60)
        lanc  = _safe_int(r["lanc"] / 60)
        prazo = _safe_int(r["prazo"] / 60)
        if tipo == "aderencia":
            pct = round((r["lanc"] / r["carga"] * 100)) if r["carga"] else 0
            texto = f"{carga} horas úteis | {lanc} horas lançadas"
        else:
            pct = round((r["prazo"] / r["lanc"] * 100)) if r["lanc"] else 0
            texto = f"{lanc} horas lançadas | {prazo} horas no prazo"
        linhas += (
            "<div style='display:flex; align-items:center; gap:12px; margin-bottom:10px;'>"
            f"<div style='width:150px; font-size:0.8rem; color:#3a4250; text-align:right; "
            f"white-space:nowrap; overflow:hidden; text-overflow:ellipsis;' title='{_html_escape(area)}'>{_html_escape(area)}</div>"
            f"<div style='flex:1;'>{_barra_html(pct, meta)}</div>"
            f"<div style='width:230px; font-size:0.78rem; color:#7a828f;'>{texto}</div>"
            "</div>"
        )
    return (
        f"<div style='font-size:0.95rem; font-weight:600; color:#3a4250; "
        f"text-align:center; margin:0 0 14px 0;'>{titulo}</div>"
        f"{linhas}"
    )

_df_area = _dados_por_area(kpi_mes)
if not _df_area.empty:
    st.markdown(
        "<div class='custom-card' style='height:auto; padding:22px 26px;'>"
        "<div style='font-size:1.15rem; font-weight:700; color:#1B2A4A; margin:0 0 18px 0;'>Análise por Unidades</div>"
        "<div style='display:flex; gap:32px;'>"
        "<div style='flex:1;'>"
        + _coluna_analise("Aderência ao Lançamento", _df_area, "aderencia", META_ADERENCIA)
        + "</div>"
        "<div style='width:1px; background:#e4e7ec;'></div>"
        "<div style='flex:1;'>"
        + _coluna_analise("Horas Lançadas no Prazo", _df_area, "prazo", META_PRAZO)
        + "</div>"
        "</div>"
        "</div>",
        unsafe_allow_html=True
    )
