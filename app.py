import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import io

# ─────────────────────────────────────────────
# CONFIG
# ─────────────────────────────────────────────
st.set_page_config(
    page_title="Dashboard Comercial — Grifos",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

# CSS
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
    html, body, [class*="css"] { font-family: 'Inter', sans-serif; }
    .stApp { background-color: #0f172a; }
    section[data-testid="stSidebar"] { background-color: #1e293b; }
    .block-container { padding: 1.5rem 2rem; }

    /* KPI cards */
    .kpi-card {
        background: #1e293b;
        border: 1px solid #334155;
        border-radius: 12px;
        padding: 18px 20px;
        margin-bottom: 4px;
    }
    .kpi-label { font-size: 11px; color: #64748b; text-transform: uppercase; letter-spacing: 1px; margin-bottom: 6px; }
    .kpi-value { font-size: 26px; font-weight: 700; color: #f1f5f9; line-height: 1; margin-bottom: 4px; }
    .kpi-sub   { font-size: 12px; color: #94a3b8; margin-bottom: 6px; }
    .kpi-ok    { color: #22c55e; font-size: 12px; font-weight: 600; }
    .kpi-warn  { color: #f59e0b; font-size: 12px; font-weight: 600; }
    .kpi-danger{ color: #ef4444; font-size: 12px; font-weight: 600; }

    /* Progress */
    .prog-wrap { background: #0f172a; border-radius: 4px; height: 6px; margin-top: 8px; }
    .prog-fill-ok     { height: 6px; border-radius: 4px; background: #22c55e; }
    .prog-fill-warn   { height: 6px; border-radius: 4px; background: #f59e0b; }
    .prog-fill-danger { height: 6px; border-radius: 4px; background: #ef4444; }
    .prog-fill-blue   { height: 6px; border-radius: 4px; background: #00d4ff; }

    /* Section title */
    .section-head { font-size: 20px; font-weight: 700; color: #f1f5f9; margin-bottom: 4px; }
    .section-sub  { font-size: 12px; color: #64748b; margin-bottom: 20px; }

    /* Upload boxes */
    [data-testid="stFileUploader"] { background: #1e293b; border-radius: 10px; padding: 8px; }

    /* Tabs */
    .stTabs [role="tab"] { color: #64748b; font-weight: 600; font-size: 13px; }
    .stTabs [role="tab"][aria-selected="true"] { color: #00d4ff; border-bottom-color: #00d4ff; }

    /* Alert */
    .alert-info { background: rgba(0,212,255,0.08); border: 1px solid rgba(0,212,255,0.3);
                  border-radius: 8px; padding: 12px 16px; font-size: 13px; color: #e2e8f0; margin-bottom: 16px; }
    .alert-warn { background: rgba(245,158,11,0.08); border: 1px solid rgba(245,158,11,0.3);
                  border-radius: 8px; padding: 12px 16px; font-size: 13px; color: #e2e8f0; margin-bottom: 16px; }

    /* DataFrames */
    .dataframe { font-size: 12px !important; }
    [data-testid="stMetricValue"] { font-size: 24px !important; }
</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────
BPC_FORNEC_NAMES = [
    'UNILEVER BRASIL LTDA - 555',
    'UNILEVER BRASIL LTDA - 250',
    'UNILEVER BRASIL LTDA - 253',
    'UNILEVER BRASIL LTDA. - 638',
    'UNILEVER BRASIL LTDA - 553',
]

COLS_1464 = [
    'COD_GER','SUPERVISOR','COD_SUPERV','VENDEDOR','COD_CL','RAZAO_SOCIAL',
    'ITEM','COD_PROD','DESCR_PROD','EMBALAGEM','UNID','QT_CX','QT_UN',
    'VALOR','PERC_FAT','ST','OUTRO'
]

def fmt_brl(v):
    if pd.isna(v): return "—"
    if abs(v) >= 1_000_000: return f"R$ {v/1e6:.2f}M"
    if abs(v) >= 1_000:     return f"R$ {v/1e3:.1f}k"
    return f"R$ {v:,.2f}"

def pct_class(p):
    if p >= 0.6: return "kpi-ok"
    if p >= 0.4: return "kpi-warn"
    return "kpi-danger"

def bar_class(p):
    if p >= 0.6: return "prog-fill-ok"
    if p >= 0.4: return "prog-fill-warn"
    return "prog-fill-danger"

def kpi_card(label, value, sub="", pct=None):
    pct_html = ""
    bar_html = ""
    if pct is not None:
        cls = pct_class(pct)
        bcls = bar_class(pct)
        w = min(int(pct * 100), 100)
        pct_html = f'<div class="{cls}">{pct*100:.1f}% atingido</div>'
        bar_html = f'<div class="prog-wrap"><div class="{bcls}" style="width:{w}%"></div></div>'
    return f"""
    <div class="kpi-card">
        <div class="kpi-label">{label}</div>
        <div class="kpi-value">{value}</div>
        <div class="kpi-sub">{sub}</div>
        {pct_html}{bar_html}
    </div>"""


@st.cache_data(show_spinner=False)
def read_8025(f):
    """Lê CSV da rotina 8025 — Mapa de Vendas"""
    try:
        df = pd.read_csv(f, sep=';', decimal=',', encoding='utf-8')
    except Exception:
        df = pd.read_csv(f, sep=',', decimal='.', encoding='utf-8')
    # limpar espaços
    for c in df.select_dtypes('object').columns:
        df[c] = df[c].str.strip()
    return df


@st.cache_data(show_spinner=False)
def read_1464(f):
    """Lê Excel da rotina 1464 (sem cabeçalho) — suporta xls, xlsx e formatos legados do Winthor"""
    fname = getattr(f, 'name', str(f)).lower()
    errors = []

    # Estratégia 1: openpyxl (xlsx padrão)
    try:
        df = pd.read_excel(f, header=None, engine='openpyxl')
        if df.shape[0] > 0:
            return _fix_1464_cols(df)
    except Exception as e:
        errors.append(f"openpyxl: {e}")

    # Estratégia 2: xlrd (xls antigo e alguns xlsx do Winthor)
    try:
        if hasattr(f, 'seek'): f.seek(0)
        df = pd.read_excel(f, header=None, engine='xlrd')
        if df.shape[0] > 0:
            return _fix_1464_cols(df)
    except Exception as e:
        errors.append(f"xlrd: {e}")

    # Estratégia 3: calamine (lida com formatos corrompidos/legados)
    try:
        if hasattr(f, 'seek'): f.seek(0)
        df = pd.read_excel(f, header=None, engine='calamine')
        if df.shape[0] > 0:
            return _fix_1464_cols(df)
    except Exception as e:
        errors.append(f"calamine: {e}")

    # Estratégia 4: CSV como fallback (Winthor às vezes exporta .xlsx que são CSV renomeados)
    try:
        if hasattr(f, 'seek'): f.seek(0)
        raw = f.read()
        if hasattr(f, 'seek'): f.seek(0)
        text = raw.decode('utf-8', errors='replace')
        import io as _io
        df = pd.read_csv(_io.StringIO(text), sep=';', decimal=',', header=None)
        if df.shape[0] > 0:
            return _fix_1464_cols(df)
    except Exception as e:
        errors.append(f"csv-fallback: {e}")

    raise ValueError(f"Não foi possível ler o arquivo 1464. Tentativas: {'; '.join(errors)}")


def _fix_1464_cols(df):
    """Aplica nomes de colunas e limpeza ao DataFrame da 1464"""
    if df.shape[1] >= 14:
        cols = COLS_1464[:df.shape[1]]
        if df.shape[1] > len(cols):
            cols += [f'_col{i}' for i in range(df.shape[1] - len(cols))]
        df.columns = cols
    for c in df.select_dtypes('object').columns:
        df[c] = df[c].astype(str).str.strip()
    # Garantir que VALOR seja numérico
    if 'VALOR' in df.columns:
        df['VALOR'] = pd.to_numeric(df['VALOR'].astype(str).str.replace(',', '.'), errors='coerce').fillna(0)
    return df


@st.cache_data(show_spinner=False)
def read_8066(f):
    """Lê CSV da rotina 8066 — Estoque Valorizado"""
    try:
        df = pd.read_csv(f, sep=';', decimal=',', encoding='utf-8')
    except Exception:
        df = pd.read_csv(f, sep=',', decimal='.', encoding='utf-8')
    for c in df.select_dtypes('object').columns:
        df[c] = df[c].str.strip()
    return df


@st.cache_data(show_spinner=False)
def read_105(f):
    """Lê XLS da rotina 105 — Posição de Estoque"""
    try:
        df = pd.read_excel(f, engine='xlrd')
    except Exception:
        df = pd.read_excel(f, engine='openpyxl')
    for c in df.select_dtypes('object').columns:
        df[c] = df[c].astype(str).str.strip()
    return df


def calcular_meta_diaria(df_8025):
    """Consolida meta diária por RCA a partir da 8025"""
    dias_realizar  = int(df_8025['DIAS_REALIZAR'].iloc[0])   # dias restantes no mês
    dias_realizado = int(df_8025['DIAS_REALIZADO'].iloc[0])  # dias úteis já realizados
    dias_uteis_mes = dias_realizar + dias_realizado            # total de dias úteis do mês
    periodo = df_8025['PERIODOCAB'].iloc[0] if 'PERIODOCAB' in df_8025.columns else "—"
    ref = df_8025['DTREFERATIVOCAB'].iloc[0] if 'DTREFERATIVOCAB' in df_8025.columns else "—"

    # Por RCA — first() pois os campos de RCA se repetem por fornecedor
    rca = df_8025.groupby('NOMERCA').agg(
        SUPERVISOR       = ('NOMESUPERVISOR', 'first'),
        VLLIQ_RCA        = ('VLLIQ_RCA',       'first'),
        META_FAT_RCA     = ('META_FAT_RCA',    'first'),
        POS_RCA          = ('POS_RCA',          'first'),
        CART_RCA         = ('CART_RCA',         'first'),
        META_POS_RCA     = ('META_POS_RCA',     'first'),
        TENDFATVAL_RCA   = ('TENDFATVAL_RCA',  'first'),
        TENDFATPERC_RCA  = ('TENDFATPERC_RCA', 'first'),
    ).reset_index()

    # Filtrar apenas vendedores com meta > 0
    rca = rca[rca['META_FAT_RCA'] > 0].copy()

    rca['PCT_FAT']    = rca['VLLIQ_RCA'] / rca['META_FAT_RCA']
    rca['SALDO']      = rca['META_FAT_RCA'] - rca['VLLIQ_RCA']
    rca['MEDIA_REALIZADA'] = rca['VLLIQ_RCA'] / dias_realizado if dias_realizado > 0 else 0
    rca['MEDIA_NECESSARIA'] = rca['SALDO'] / dias_realizar if dias_realizar > 0 else 0

    return rca, dias_uteis_mes, dias_realizado, dias_realizar, periodo, ref


def calcular_positivacao_bpc(df_com, df_sem=None):
    """Calcula positivação BPC unindo com e sem ST, removendo duplicatas"""
    frames = [df_com[['VENDEDOR','COD_CL','RAZAO_SOCIAL']]]
    if df_sem is not None:
        frames.append(df_sem[['VENDEDOR','COD_CL','RAZAO_SOCIAL']])
    pos = pd.concat(frames).drop_duplicates()
    por_vendedor = pos.groupby('VENDEDOR').size().reset_index(name='POSITIVACOES')
    return pos, por_vendedor


def plotly_theme():
    return dict(
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        font=dict(color='#94a3b8', family='Inter', size=11),
        xaxis=dict(gridcolor='#1e293b', linecolor='#334155', tickfont=dict(size=10)),
        yaxis=dict(gridcolor='#1e293b', linecolor='#334155', tickfont=dict(size=10)),
        legend=dict(bgcolor='rgba(0,0,0,0)', font=dict(size=11)),
        margin=dict(l=10, r=10, t=30, b=10),
    )


# ─────────────────────────────────────────────
# SIDEBAR — UPLOAD DE ARQUIVOS
# ─────────────────────────────────────────────
with st.sidebar:
    st.markdown("### 📂 Carregar Bases")
    st.caption("Suba as bases exportadas do Winthor")

    st.markdown("**Rotina 8025 — Mapa de Vendas**")
    f_8025 = st.file_uploader("8025 (CSV)", type=["csv"], key="f8025", label_visibility="collapsed")

    st.markdown("**Rotina 1464 — BPC com ST**")
    f_1464_com = st.file_uploader("1464 BPC com ST (XLSX)", type=["xlsx","xls"], key="f1464com", label_visibility="collapsed")

    st.markdown("**Rotina 1464 — BPC sem ST**")
    f_1464_sem = st.file_uploader("1464 BPC sem ST (XLSX)", type=["xlsx","xls"], key="f1464sem", label_visibility="collapsed")

    st.markdown("**Rotina 8066 — Estoque Valorizado**")
    f_8066 = st.file_uploader("8066 (CSV)", type=["csv"], key="f8066", label_visibility="collapsed")

    st.markdown("**Rotina 105 — Posição de Estoque**")
    f_105 = st.file_uploader("105 (XLS/XLSX)", type=["xls","xlsx"], key="f105", label_visibility="collapsed")

    st.markdown("**Rotina 1464 — Compliance (todos BUs)**")
    f_compliance = st.file_uploader("1464 Compliance (XLSX)", type=["xlsx","xls"], key="fcomp", label_visibility="collapsed")

    st.divider()
    st.caption("💡 **Dica:** Exporte do Winthor, arraste o arquivo e o dashboard atualiza automaticamente.")


# ─────────────────────────────────────────────
# MAIN — SEM DADOS
# ─────────────────────────────────────────────
has_8025 = f_8025 is not None

if not has_8025:
    st.markdown('<div class="section-head">Dashboard Comercial — Grifos</div>', unsafe_allow_html=True)
    st.markdown('<div class="section-sub">Carregue a base 8025 (Mapa de Vendas) na barra lateral para começar.</div>', unsafe_allow_html=True)

    st.markdown("""
    <div class="alert-info">
    📌 <strong>Como usar:</strong><br>
    1. Exporte a <strong>Rotina 8025</strong> do Winthor em CSV e faça upload → indicadores de Meta Diária ficam prontos.<br>
    2. Exporte a <strong>Rotina 1464</strong> filtrada por BPC (Fornecedor 19 — Beauty + PC) em dois relatórios: com ST e sem ST.<br>
    3. Faça upload dos dois arquivos 1464 → positivação BPC é calculada automaticamente (deduplicando clientes).<br>
    4. Opcionalmente suba o <strong>8066 + 105</strong> para ver o painel de estoque.<br>
    5. Suba o <strong>1464 Compliance</strong> (todos BUs) para acompanhar faturamento acumulado.
    </div>
    """, unsafe_allow_html=True)

    col1, col2, col3 = st.columns(3)
    with col1:
        st.markdown("""<div class="kpi-card">
            <div class="kpi-label">Aguardando</div>
            <div class="kpi-value">8025</div>
            <div class="kpi-sub">Mapa de Vendas CSV</div>
        </div>""", unsafe_allow_html=True)
    with col2:
        st.markdown("""<div class="kpi-card">
            <div class="kpi-label">Aguardando</div>
            <div class="kpi-value">1464 BPC</div>
            <div class="kpi-sub">Com ST + Sem ST XLSX</div>
        </div>""", unsafe_allow_html=True)
    with col3:
        st.markdown("""<div class="kpi-card">
            <div class="kpi-label">Aguardando</div>
            <div class="kpi-value">8066 / 105</div>
            <div class="kpi-sub">Estoque CSV / XLS</div>
        </div>""", unsafe_allow_html=True)
    st.stop()


# ─────────────────────────────────────────────
# CARREGAR DADOS
# ─────────────────────────────────────────────
with st.spinner("Processando bases..."):
    df_8025 = read_8025(f_8025)
    rca_df, dias_uteis_mes, dias_realizado, dias_restantes, periodo, ref = calcular_meta_diaria(df_8025)

    df_com = read_1464(f_1464_com) if f_1464_com else None
    df_sem = read_1464(f_1464_sem) if f_1464_sem else None
    df_8066 = read_8066(f_8066) if f_8066 else None
    df_105  = read_105(f_105) if f_105 else None
    df_comp = read_1464(f_compliance) if f_compliance else None

    # Positivação BPC
    pos_df, pos_por_vend = (None, None)
    if df_com is not None:
        pos_df, pos_por_vend = calcular_positivacao_bpc(df_com, df_sem)


# ─────────────────────────────────────────────
# HEADER GERAL
# ─────────────────────────────────────────────
st.markdown(f"""
<div style="display:flex; align-items:center; justify-content:space-between; margin-bottom:24px;">
    <div>
        <div class="section-head">Dashboard Comercial — Grifos</div>
        <div class="section-sub">Período: {periodo} &nbsp;|&nbsp; Referência: {ref} &nbsp;|&nbsp; Dias úteis: {dias_uteis_mes} &nbsp;|&nbsp; Realizados: {dias_realizado} &nbsp;|&nbsp; Restantes: {dias_restantes}</div>
    </div>
    <div style="text-align:right;">
        <div style="font-size:11px; color:#64748b; text-transform:uppercase; letter-spacing:1px;">Dias Restantes</div>
        <div style="font-size:36px; font-weight:800; color:#f59e0b; line-height:1;">{dias_restantes}</div>
        <div style="font-size:10px; color:#64748b;">de {dias_uteis_mes} dias úteis</div>
    </div>
</div>
""", unsafe_allow_html=True)


# ─────────────────────────────────────────────
# ABAS
# ─────────────────────────────────────────────
tab_meta, tab_bpc, tab_estoque, tab_compliance, tab_dados = st.tabs([
    "📈 Meta Diária",
    "🧴 BPC — Positivação",
    "📦 Estoque",
    "✅ Compliance / Faturamento",
    "🗂️ Dados Brutos",
])


# ═══════════════════════════════════════════════
# ABA 1 — META DIÁRIA (8025)
# ═══════════════════════════════════════════════
with tab_meta:
    st.markdown('<div class="section-head">Meta Diária por Vendedor</div>', unsafe_allow_html=True)
    st.markdown('<div class="section-sub">Base: Rotina 8025 — Mapa de Vendas · BPC consolidado por RCA</div>', unsafe_allow_html=True)

    # KPIs gerais
    total_meta   = rca_df['META_FAT_RCA'].sum()
    total_real   = rca_df['VLLIQ_RCA'].sum()
    total_saldo  = rca_df['SALDO'].sum()
    total_tend   = rca_df['TENDFATVAL_RCA'].sum()
    pct_geral    = total_real / total_meta if total_meta > 0 else 0
    media_nec    = total_saldo / dias_restantes if dias_restantes > 0 else 0

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.markdown(kpi_card("Meta Faturamento", fmt_brl(total_meta), "Todos os vendedores"), unsafe_allow_html=True)
    with c2:
        st.markdown(kpi_card("Realizado", fmt_brl(total_real), f"Em {dias_realizado} dias úteis", pct_geral), unsafe_allow_html=True)
    with c3:
        st.markdown(kpi_card("Tendência Projetada", fmt_brl(total_tend), "Projeção linear ao fechamento"), unsafe_allow_html=True)
    with c4:
        st.markdown(kpi_card("Média/Dia Necessária", fmt_brl(media_nec), f"Para bater meta em {dias_restantes} dias"), unsafe_allow_html=True)

    st.divider()

    # Filtros
    col_f1, col_f2, col_f3 = st.columns([2,2,1])
    with col_f1:
        supervisores = ["Todos"] + sorted(rca_df['SUPERVISOR'].dropna().unique().tolist())
        sup_sel = st.selectbox("Supervisor", supervisores, key="sup_meta")
    with col_f2:
        search = st.text_input("Buscar vendedor", "", key="search_meta")
    with col_f3:
        mostrar_zerados = st.checkbox("Mostrar zerados", False)

    df_view = rca_df.copy()
    if sup_sel != "Todos":
        df_view = df_view[df_view['SUPERVISOR'] == sup_sel]
    if search:
        df_view = df_view[df_view['NOMERCA'].str.upper().str.contains(search.upper())]
    if not mostrar_zerados:
        df_view = df_view[df_view['VLLIQ_RCA'] > 0]

    # Tabela principal
    tabela = df_view[['NOMERCA','SUPERVISOR','VLLIQ_RCA','META_FAT_RCA','PCT_FAT',
                       'SALDO','MEDIA_NECESSARIA','MEDIA_REALIZADA',
                       'TENDFATVAL_RCA','TENDFATPERC_RCA',
                       'POS_RCA','CART_RCA']].copy()

    tabela.columns = ['Vendedor','Supervisor','Realizado','Meta','% Atingido',
                      'Saldo','Média/Dia Necessária','Média/Dia Realizada',
                      'Tendência Val.','Tendência %',
                      'Pos. Real','Carteira']

    # Formatar para exibição
    def color_pct(val):
        if isinstance(val, float):
            if val >= 0.6:  return 'color: #22c55e'
            if val >= 0.4:  return 'color: #f59e0b'
            return 'color: #ef4444'
        return ''

    styled = (
        tabela.style
        .format({
            'Realizado':          'R$ {:,.0f}',
            'Meta':               'R$ {:,.0f}',
            '% Atingido':         '{:.1%}',
            'Saldo':              'R$ {:,.0f}',
            'Média/Dia Necessária':'R$ {:,.0f}',
            'Média/Dia Realizada': 'R$ {:,.0f}',
            'Tendência Val.':     'R$ {:,.0f}',
            'Tendência %':        '{:.1f}%',
        })
        .applymap(color_pct, subset=['% Atingido'])
        .set_properties(**{'font-size':'12px'})
    )
    st.dataframe(styled, use_container_width=True, height=420)

    # ── Gráficos ──
    col_g1, col_g2 = st.columns(2)

    with col_g1:
        st.markdown("**Meta × Realizado por Vendedor**")
        top = df_view.nlargest(15, 'META_FAT_RCA')
        fig = go.Figure()
        fig.add_bar(x=top['NOMERCA'].str.split().str[0], y=top['META_FAT_RCA'],
                    name='Meta', marker_color='#334155')
        fig.add_bar(x=top['NOMERCA'].str.split().str[0], y=top['VLLIQ_RCA'],
                    name='Realizado', marker_color='#00d4ff')
        fig.update_layout(**plotly_theme(), barmode='group', height=340)
        st.plotly_chart(fig, use_container_width=True)

    with col_g2:
        st.markdown("**% Atingimento × Tendência**")
        df_scatter = df_view[df_view['META_FAT_RCA'] > 0].copy()
        df_scatter['NOME_CURTO'] = df_scatter['NOMERCA'].str.split().str[0]
        fig2 = px.scatter(
            df_scatter, x='PCT_FAT', y='TENDFATPERC_RCA',
            text='NOME_CURTO', color='SUPERVISOR',
            labels={'PCT_FAT':'% Atingido (Meta Fat)','TENDFATPERC_RCA':'Tend. %'},
            hover_data={'NOMERCA': True, 'VLLIQ_RCA': True, 'META_FAT_RCA': True},
        )
        fig2.add_vline(x=0.68, line_dash='dot', line_color='#f59e0b',
                       annotation_text=f'{dias_realizado}/{dias_uteis_mes} dias', annotation_font_color='#f59e0b')
        fig2.update_traces(textposition='top center', textfont_size=9)
        fig2.update_layout(**plotly_theme(), height=340)
        fig2.update_xaxes(tickformat='.0%')
        st.plotly_chart(fig2, use_container_width=True)

    # ── Ranking % atingimento ──
    st.markdown("**Ranking de Atingimento**")
    rank = df_view[df_view['META_FAT_RCA'] > 0].nlargest(20, 'PCT_FAT').copy()
    fig3 = go.Figure()
    colors = ['#22c55e' if p >= 0.6 else '#f59e0b' if p >= 0.4 else '#ef4444' for p in rank['PCT_FAT']]
    fig3.add_bar(
        x=rank['PCT_FAT'], y=rank['NOMERCA'].str.split().str[0],
        orientation='h', marker_color=colors,
        text=[f'{p:.1%}' for p in rank['PCT_FAT']],
        textposition='outside'
    )
    fig3.add_vline(x=0.68, line_dash='dot', line_color='#f59e0b')
    fig3.update_layout(**plotly_theme(), xaxis_tickformat='.0%', height=420)
    st.plotly_chart(fig3, use_container_width=True)


# ═══════════════════════════════════════════════
# ABA 2 — BPC POSITIVAÇÃO (1464)
# ═══════════════════════════════════════════════
with tab_bpc:
    if df_com is None:
        st.markdown('<div class="alert-warn">⚠️ Faça upload da base 1464 BPC (com ST) na barra lateral.</div>', unsafe_allow_html=True)
        st.stop()

    st.markdown('<div class="section-head">BPC — Beauty & Personal Care</div>', unsafe_allow_html=True)
    st.markdown('<div class="section-sub">Base: Rotina 1464 · Fornecedor 19 (Beauty + PC) · Com ST + Sem ST</div>', unsafe_allow_html=True)

    # KPIs BPC
    fat_com = df_com['VALOR'].sum() if 'VALOR' in df_com.columns else 0
    fat_sem = df_sem['VALOR'].sum() if df_sem is not None and 'VALOR' in df_sem.columns else 0
    fat_total = fat_com + fat_sem
    total_pdvs = len(pos_df) if pos_df is not None else 0
    total_vend = pos_por_vend['VENDEDOR'].nunique() if pos_por_vend is not None else 0

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.markdown(kpi_card("Faturamento BPC (com ST)", fmt_brl(fat_com), "1464 com substituição tributária"), unsafe_allow_html=True)
    with c2:
        st.markdown(kpi_card("Faturamento BPC (sem ST)", fmt_brl(fat_sem), "1464 sem substituição tributária"), unsafe_allow_html=True)
    with c3:
        st.markdown(kpi_card("PDVs Positivados (BPC)", f"{total_pdvs:,}", f"Clientes únicos com pedido"), unsafe_allow_html=True)
    with c4:
        st.markdown(kpi_card("Vendedores Ativos", str(total_vend), "Com ao menos 1 PDV BPC"), unsafe_allow_html=True)

    st.divider()

    # Filtro supervisor
    if 'SUPERVISOR' in df_com.columns:
        sups_bpc = ['Todos'] + sorted(df_com['SUPERVISOR'].dropna().unique().tolist())
        sup_bpc = st.selectbox("Filtrar Supervisor", sups_bpc, key="sup_bpc")
        df_com_f = df_com[df_com['SUPERVISOR'] == sup_bpc] if sup_bpc != 'Todos' else df_com
        df_sem_f = (df_sem[df_sem['SUPERVISOR'] == sup_bpc] if df_sem is not None and sup_bpc != 'Todos' else df_sem) if df_sem is not None else None
    else:
        df_com_f, df_sem_f = df_com, df_sem

    # Recalcular positivação para filtro
    pos_f, ppv_f = calcular_positivacao_bpc(df_com_f, df_sem_f)

    col_p1, col_p2 = st.columns([1,1])

    with col_p1:
        st.markdown("**Positivação por Vendedor (PDVs únicos)**")
        ppv_sorted = ppv_f.sort_values('POSITIVACOES', ascending=True).tail(20)
        fig_pos = go.Figure()
        fig_pos.add_bar(
            x=ppv_sorted['POSITIVACOES'],
            y=ppv_sorted['VENDEDOR'].str.split().str[0],
            orientation='h',
            marker_color='#c084fc',
            text=ppv_sorted['POSITIVACOES'],
            textposition='outside'
        )
        fig_pos.update_layout(**plotly_theme(), height=480)
        st.plotly_chart(fig_pos, use_container_width=True)

    with col_p2:
        st.markdown("**Faturamento BPC por Vendedor**")
        fat_vend_com = df_com_f.groupby('VENDEDOR')['VALOR'].sum().reset_index() if 'VALOR' in df_com_f.columns else pd.DataFrame()
        fat_vend_sem = df_sem_f.groupby('VENDEDOR')['VALOR'].sum().reset_index() if df_sem_f is not None and 'VALOR' in df_sem_f.columns else pd.DataFrame()

        if not fat_vend_com.empty:
            fat_vend_com.columns = ['Vendedor','Com ST']
            if not fat_vend_sem.empty:
                fat_vend_sem.columns = ['Vendedor','Sem ST']
                fat_merge = fat_vend_com.merge(fat_vend_sem, on='Vendedor', how='outer').fillna(0)
                fat_merge['Total'] = fat_merge['Com ST'] + fat_merge['Sem ST']
            else:
                fat_merge = fat_vend_com.rename(columns={'Com ST':'Total'})
            fat_merge = fat_merge.sort_values('Total', ascending=True).tail(20)

            fig_fat = go.Figure()
            if 'Com ST' in fat_merge.columns:
                fig_fat.add_bar(y=fat_merge['Vendedor'].str.split().str[0], x=fat_merge['Com ST'],
                                name='Com ST', orientation='h', marker_color='#00d4ff')
                fig_fat.add_bar(y=fat_merge['Vendedor'].str.split().str[0], x=fat_merge.get('Sem ST', 0),
                                name='Sem ST', orientation='h', marker_color='#ff6b35')
                fig_fat.update_layout(**plotly_theme(), barmode='stack', height=480)
            else:
                fig_fat.add_bar(y=fat_merge['Vendedor'].str.split().str[0], x=fat_merge['Total'],
                                orientation='h', marker_color='#00d4ff')
                fig_fat.update_layout(**plotly_theme(), height=480)
            st.plotly_chart(fig_fat, use_container_width=True)

    # Tabela de positivação detalhada
    st.markdown("**Detalhamento — Clientes Positivados BPC**")
    st.caption(f"Total de {len(pos_f)} PDVs únicos após deduplicação")

    col_s1, col_s2 = st.columns(2)
    with col_s1:
        vend_sel = st.selectbox("Filtrar Vendedor", ["Todos"] + sorted(pos_f['VENDEDOR'].unique().tolist()), key="vend_bpc")
    with col_s2:
        busca_cl = st.text_input("Buscar cliente", "", key="busca_cl_bpc")

    pos_show = pos_f.copy()
    if vend_sel != "Todos":
        pos_show = pos_show[pos_show['VENDEDOR'] == vend_sel]
    if busca_cl:
        pos_show = pos_show[pos_show['RAZAO_SOCIAL'].str.upper().str.contains(busca_cl.upper())]

    st.dataframe(pos_show.reset_index(drop=True), use_container_width=True, height=320)

    # Produtos mais vendidos
    if 'DESCR_PROD' in df_com_f.columns and 'VALOR' in df_com_f.columns:
        st.markdown("**Top 20 Produtos BPC por Faturamento**")
        top_prod = df_com_f.groupby('DESCR_PROD')['VALOR'].sum().nlargest(20).reset_index()
        top_prod.columns = ['Produto','Faturamento']
        fig_prod = px.bar(top_prod, x='Faturamento', y='Produto', orientation='h',
                          color='Faturamento', color_continuous_scale=['#1e293b','#00d4ff'])
        fig_prod.update_layout(**plotly_theme(), height=480, coloraxis_showscale=False)
        st.plotly_chart(fig_prod, use_container_width=True)


# ═══════════════════════════════════════════════
# ABA 3 — ESTOQUE (8066 + 105)
# ═══════════════════════════════════════════════
with tab_estoque:
    if df_8066 is None and df_105 is None:
        st.markdown('<div class="alert-warn">⚠️ Faça upload das bases 8066 e/ou 105 na barra lateral.</div>', unsafe_allow_html=True)
        st.stop()

    st.markdown('<div class="section-head">Estoque</div>', unsafe_allow_html=True)
    st.markdown('<div class="section-sub">8066 — Estoque Valorizado &nbsp;|&nbsp; 105 — Posição de Estoque</div>', unsafe_allow_html=True)

    if df_8066 is not None:
        st.markdown("**8066 — Estoque Valorizado por Fornecedor**")

        num_cols = df_8066.select_dtypes(include='number').columns.tolist()
        str_cols = df_8066.select_dtypes(include='object').columns.tolist()

        # KPIs se tiver colunas conhecidas
        if 'CUSTO' in df_8066.columns and 'PRECO' in df_8066.columns:
            total_custo = pd.to_numeric(df_8066['CUSTO'].astype(str).str.replace(',','.'), errors='coerce').sum()
            total_preco = pd.to_numeric(df_8066['PRECO'].astype(str).str.replace(',','.'), errors='coerce').sum()
            c1, c2, c3 = st.columns(3)
            with c1: st.markdown(kpi_card("Total Custo Estoque", fmt_brl(total_custo), "Valorização ao custo"), unsafe_allow_html=True)
            with c2: st.markdown(kpi_card("Total Preço Venda", fmt_brl(total_preco), "Valorização ao preço"), unsafe_allow_html=True)
            with c3:
                if total_custo > 0:
                    margem = (total_preco - total_custo) / total_custo
                    st.markdown(kpi_card("Margem Bruta Estoque", f"{margem:.1%}", "Preço vs Custo"), unsafe_allow_html=True)

        if 'FORNECEDOR' in df_8066.columns:
            grp_forn = df_8066.groupby('FORNECEDOR')
            if 'CUSTO' in df_8066.columns:
                agg = grp_forn.apply(lambda g: pd.to_numeric(
                    g['CUSTO'].astype(str).str.replace(',','.'), errors='coerce').sum()
                ).reset_index()
                agg.columns = ['Fornecedor','Custo Total']
                agg = agg.sort_values('Custo Total', ascending=False)
                fig_est = px.bar(agg, x='Custo Total', y='Fornecedor', orientation='h',
                                 color='Custo Total', color_continuous_scale=['#1e293b','#a8ff3e'])
                fig_est.update_layout(**plotly_theme(), height=400, coloraxis_showscale=False)
                st.plotly_chart(fig_est, use_container_width=True)

        st.markdown("**Dados brutos 8066**")
        st.dataframe(df_8066, use_container_width=True, height=300)

    if df_105 is not None:
        st.divider()
        st.markdown("**105 — Posição de Estoque**")
        st.dataframe(df_105, use_container_width=True, height=300)


# ═══════════════════════════════════════════════
# ABA 4 — COMPLIANCE / FATURAMENTO GERAL
# ═══════════════════════════════════════════════
with tab_compliance:
    if df_comp is None:
        st.markdown('<div class="alert-warn">⚠️ Faça upload da base 1464 Compliance (todos BUs) na barra lateral.</div>', unsafe_allow_html=True)
        st.stop()

    st.markdown('<div class="section-head">Compliance — Faturamento Acumulado</div>', unsafe_allow_html=True)
    st.markdown('<div class="section-sub">Base: Rotina 1464 · Todos os BUs · Do dia 1 até hoje</div>', unsafe_allow_html=True)

    if 'VALOR' in df_comp.columns and 'VENDEDOR' in df_comp.columns:
        fat_total_comp = df_comp['VALOR'].sum()
        vend_ativos = df_comp['VENDEDOR'].nunique()
        c1, c2, c3 = st.columns(3)
        with c1:
            st.markdown(kpi_card("Fat. Total Acumulado", fmt_brl(fat_total_comp), "Todos os BUs"), unsafe_allow_html=True)
        with c2:
            st.markdown(kpi_card("Vendedores Ativos", str(vend_ativos), "Com ao menos 1 pedido"), unsafe_allow_html=True)
        with c3:
            media_fat = fat_total_comp / dias_realizado if dias_realizado > 0 else 0
            st.markdown(kpi_card("Média Diária Realizada", fmt_brl(media_fat), f"Em {dias_realizado} dias úteis"), unsafe_allow_html=True)

        st.divider()

        col_c1, col_c2 = st.columns([1,1])
        with col_c1:
            st.markdown("**Faturamento por Vendedor**")
            fat_vend = df_comp.groupby('VENDEDOR')['VALOR'].sum().sort_values(ascending=False).reset_index()
            fat_vend.columns = ['Vendedor','Faturamento']
            st.dataframe(fat_vend.style.format({'Faturamento': 'R$ {:,.2f}'}), use_container_width=True, height=360)

        with col_c2:
            st.markdown("**Top 15 — Faturamento por Vendedor**")
            top15 = fat_vend.nlargest(15, 'Faturamento')
            fig_c = px.bar(top15, x='Faturamento', y='Vendedor', orientation='h',
                           color='Faturamento', color_continuous_scale=['#1e293b','#ff6b35'])
            fig_c.update_layout(**plotly_theme(), height=360, coloraxis_showscale=False)
            st.plotly_chart(fig_c, use_container_width=True)

        if 'DESCR_PROD' in df_comp.columns:
            st.markdown("**Top Produtos — Todos BUs**")
            top_p = df_comp.groupby('DESCR_PROD')['VALOR'].sum().nlargest(20).reset_index()
            top_p.columns = ['Produto','Faturamento']
            fig_p = px.bar(top_p, x='Faturamento', y='Produto', orientation='h',
                           color='Faturamento', color_continuous_scale=['#1e293b','#c084fc'])
            fig_p.update_layout(**plotly_theme(), height=500, coloraxis_showscale=False)
            st.plotly_chart(fig_p, use_container_width=True)
    else:
        st.dataframe(df_comp, use_container_width=True, height=400)


# ═══════════════════════════════════════════════
# ABA 5 — DADOS BRUTOS
# ═══════════════════════════════════════════════
with tab_dados:
    st.markdown('<div class="section-head">Dados Brutos</div>', unsafe_allow_html=True)
    st.markdown('<div class="section-sub">Inspecione os dados carregados para validação</div>', unsafe_allow_html=True)

    bases = {
        "8025 — Mapa de Vendas": df_8025,
        "1464 — BPC com ST": df_com,
        "1464 — BPC sem ST": df_sem,
        "8066 — Estoque Valorizado": df_8066,
        "105 — Posição Estoque": df_105,
        "1464 — Compliance": df_comp,
    }

    base_sel = st.selectbox("Selecionar base", [k for k,v in bases.items() if v is not None])
    df_show = bases[base_sel]

    if df_show is not None:
        st.caption(f"**{len(df_show):,} linhas × {df_show.shape[1]} colunas**")
        n = st.slider("Linhas para exibir", 10, min(500, len(df_show)), 50)
        st.dataframe(df_show.head(n), use_container_width=True, height=440)

        # Download
        buffer = io.BytesIO()
        df_show.to_excel(buffer, index=False)
        buffer.seek(0)
        st.download_button(
            label="⬇️ Baixar como Excel",
            data=buffer,
            file_name=f"{base_sel.replace(' ','_')}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
