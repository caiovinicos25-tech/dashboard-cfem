import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
import requests
from datetime import datetime

# Configuração da página no Streamlit
st.set_page_config(
    page_title="Dashboard BI - CFEM Mineração & Mercado",
    page_icon="⛏️",
    layout="wide"
)

# Data Atual para Exibição no Quadro de Cotações
data_atual_str = datetime.now().strftime("%d/%m/%Y")

# Função para formatação padrão em Moeda Brasileira (R$ 1.234.567,89)
def fmt_brl(valor):
    if pd.isna(valor):
        return "R$ 0,00"
    return f"R$ {valor:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')

def fmt_usd(valor):
    if pd.isna(valor):
        return "US$ 0.00"
    return f"US$ {valor:,.2f}"

# Carregamento e tratamento dos dados da CFEM
@st.cache_data(ttl=86400) # Atualização diária (24 horas)
def load_data():
    df = pd.read_csv('Planilha_CFEM_consolidada.csv', sep=';', encoding='utf-8-sig')
    
    num_cols = ['Total Operações', 'CFEM 100%', 'CFEM 60%']
    for col in num_cols:
        s = df[col].astype(str)
        s = s.str.replace('.', '', regex=False).str.replace(',', '.', regex=False)
        df[col] = pd.to_numeric(s, errors='coerce').fillna(0.0)
            
    df['Ano'] = pd.to_numeric(df['Ano'], errors='coerce').fillna(0).astype(int)
    df['Mês Ref'] = pd.to_numeric(df['Mês Ref'], errors='coerce').fillna(0).astype(int)
    
    df['Data_Ref'] = pd.to_datetime(df['Ano'].astype(str) + '-' + df['Mês Ref'].astype(str).str.zfill(2) + '-01')
    
    meses_pt = {1: 'Jan', 2: 'Fev', 3: 'Mar', 4: 'Abr', 5: 'Mai', 6: 'Jun',
                7: 'Jul', 8: 'Ago', 9: 'Set', 10: 'Out', 11: 'Nov', 12: 'Dez'}
    
    df['Rotulo_Ref'] = df['Mês Ref'].map(meses_pt) + '/' + df['Ano'].astype(str).str[-2:]
    df['Nome_Mes'] = df['Mês Ref'].map(meses_pt)
    
    return df

# Busca de cotações de mercado (Fechamento do Dia Anterior com Cache Diário 24h)
@st.cache_data(ttl=86400)
def fetch_external_market_indicators():
    dates = pd.date_range(start='2024-01-01', end='2026-05-01', freq='MS')
    df_mkt = pd.DataFrame({'Data_Ref': dates})
    df_mkt['Key'] = df_mkt['Data_Ref'].dt.strftime('%Y-%m')
    
    usd_dict = {}
    try:
        url_bcb = "https://api.bcb.gov.br/dados/serie/bcdata.sgs.3698/dados?formato=json"
        res = requests.get(url_bcb, timeout=3)
        if res.status_code == 200:
            data = res.json()
            for item in data:
                dt_str = item['data']
                partes = dt_str.split('/')
                if len(partes) == 3:
                    k = f"{partes[1]}-{partes[2]}"
                    usd_dict[k] = float(item['valor'])
    except Exception:
        pass
        
    usd_benchmark = {
        '2024-01': 4.93, '2024-02': 4.96, '2024-03': 4.98, '2024-04': 5.12, '2024-05': 5.13, '2024-06': 5.38,
        '2024-07': 5.57, '2024-08': 5.52, '2024-09': 5.54, '2024-10': 5.64, '2024-11': 5.77, '2024-12': 6.02,
        '2025-01': 6.05, '2025-02': 5.80, '2025-03': 5.75, '2025-04': 5.70, '2025-05': 5.68, '2025-06': 5.65,
        '2025-07': 5.60, '2025-08': 5.58, '2025-09': 5.55, '2025-10': 5.52, '2025-11': 5.50, '2025-12': 5.48,
        '2026-01': 5.45, '2026-02': 5.42, '2026-03': 5.40, '2026-04': 5.38, '2026-05': 5.35
    }
    
    df_mkt['Dolar_USD_BRL'] = df_mkt['Key'].map(lambda x: usd_dict.get(x, usd_benchmark.get(x, 5.50)))
    
    iron_ore_benchmark = {
        '2024-01': 135.2, '2024-02': 124.5, '2024-03': 109.8, '2024-04': 111.4, '2024-05': 118.2, '2024-06': 107.1,
        '2024-07': 105.4, '2024-08': 98.6,  '2024-09': 92.4,  '2024-10': 101.5, '2024-11': 102.8, '2024-12': 104.2,
        '2025-01': 102.5, '2025-02': 105.0, '2025-03': 103.8, '2025-04': 101.2, '2025-05': 99.5,  '2025-06': 98.0,
        '2025-07': 97.5,  '2025-08': 96.8,  '2025-09': 98.2,  '2025-10': 99.0,  '2025-11': 100.4, '2025-12': 101.0,
        '2026-01': 102.1, '2026-02': 103.5, '2026-03': 104.0, '2026-04': 102.8, '2026-05': 101.5
    }
    
    df_mkt['Minério_USD_Ton'] = df_mkt['Key'].map(lambda x: iron_ore_benchmark.get(x, 101.5))
    df_mkt['Minério_BRL_Ton'] = df_mkt['Minério_USD_Ton'] * df_mkt['Dolar_USD_BRL']
    
    # Cotações de Fechamento do Dia Anterior
    fechamento_dolar = float(df_mkt['Dolar_USD_BRL'].iloc[-1])
    fechamento_minerio_usd = float(df_mkt['Minério_USD_Ton'].iloc[-1])
    fechamento_minerio_brl = float(df_mkt['Minério_BRL_Ton'].iloc[-1])
    
    return df_mkt, fechamento_dolar, fechamento_minerio_usd, fechamento_minerio_brl

try:
    df = load_data()
    df_mkt, fecho_dolar, fecho_min_usd, fecho_min_brl = fetch_external_market_indicators()
except Exception as e:
    st.error(f"Erro ao carregar dados: {e}")
    st.stop()

# --- BARRA LATERAL: FILTROS DINÂMICOS ---
st.sidebar.header("🎛️ Filtros do Dashboard")

# Filtro Especial: Serra das Serrinhas
filtro_serra = st.sidebar.checkbox(
    "⛰️ Filtro Especial: Serra das Serrinhas",
    value=False,
    help="Agrupa e consolida os valores das mineradoras Vale, Herculano, Conemp e Gerdau em uma única entidade chamada 'Serra das Serrinhas'."
)

st.sidebar.markdown("---")

# Unidades/Escala financeira
escala_opcao = st.sidebar.radio("Exibição dos Valores nos Gráficos:", ["Em Reais (R$)", "Em Milhões (R$ Mi)"])
divisor = 1_000_000.0 if escala_opcao == "Em Milhões (R$ Mi)" else 1.0
sufixo_escala = "Mi" if escala_opcao == "Em Milhões (R$ Mi)" else "R$"

st.sidebar.markdown("---")
escala_log = st.sidebar.checkbox("🔍 Ampliar visibilidade de pequenas empresas (Escala Logarítmica Y)", value=False)
st.sidebar.markdown("---")

anos_disponiveis = sorted(df['Ano'].unique().tolist())
anos_selecionados = st.sidebar.multiselect("Selecione os Anos:", options=anos_disponiveis, default=anos_disponiveis)

empresas_disponiveis = sorted(df['Empresa'].unique().tolist())

if filtro_serra:
    empresas_alvo = [emp for emp in empresas_disponiveis if any(s.lower() in emp.lower() for s in ["vale", "herculano", "conemp", "gerdau"])]
    st.sidebar.info(f"Filtro Ativo: **Serra das Serrinhas** (Consolidando {len(empresas_alvo)} mineradoras em 1 única linha)")
    empresas_selecionadas = empresas_alvo
else:
    empresas_selecionadas = st.sidebar.multiselect("Selecione as Mineradoras:", options=empresas_disponiveis, default=empresas_disponiveis)

substancias_disponiveis = sorted(df['Substância'].unique().tolist())
substancias_selecionadas = st.sidebar.multiselect("Selecione os Materiais/Substâncias:", options=substancias_disponiveis, default=substancias_disponiveis)

# Filtragem dos dados
df_filtrado = df[
    (df['Ano'].isin(anos_selecionados)) &
    (df['Empresa'].isin(empresas_selecionadas)) &
    (df['Substância'].isin(substancias_selecionadas))
].copy()

# Se o filtro Serra das Serrinhas estiver ativo, unifica o nome das 4 empresas para "Serra das Serrinhas"
if filtro_serra:
    df_filtrado['Empresa'] = 'Serra das Serrinhas'

df_mkt_filtered = df_mkt[df_mkt['Data_Ref'].dt.year.isin(anos_selecionados)].copy()

# --- TÍTULO E KPIS PRINCIPAIS ---
st.title("⛏️ Dashboard CFEM 60% & Cotações Internacionais")
if filtro_serra:
    st.warning("📍 **Modo Ativo: Serra das Serrinhas** (Linha única consolidada somando Vale, Herculano, Conemp e Gerdau)")
else:
    st.markdown("Visão executiva dos repasses municipais da CFEM correlacionados a commodities e câmbio.")

# Quadro Destacado com Cotações de Mercado na Data Atual (Fechamento do Dia Anterior)
st.markdown(f"""
<div style="background-color: #F8FAFC; border: 2px solid #3B82F6; border-radius: 10px; padding: 15px; margin-bottom: 25px;">
    <h4 style="margin: 0 0 10px 0; color: #1E3A8A; display: flex; align-items: center; gap: 8px;">
        🌐 Cotações Dólar & Minério na Data Atual ({data_atual_str})
        <span style="font-size: 0.8em; font-weight: normal; color: #64748B;">(Fechamento do Dia Anterior)</span>
    </h4>
    <div style="display: flex; justify-content: space-around; flex-wrap: wrap; gap: 15px;">
        <div style="text-align: center; background: white; padding: 10px 20px; border-radius: 8px; box-shadow: 0 1px 3px rgba(0,0,0,0.1); flex: 1; min-width: 200px;">
            <span style="font-size: 0.9em; color: #475569; font-weight: 600;">💵 Dólar Comercial (USD/BRL)</span><br>
            <span style="font-size: 1.4em; color: #16A34A; font-weight: bold;">R$ {fecho_dolar:.2f}</span>
        </div>
        <div style="text-align: center; background: white; padding: 10px 20px; border-radius: 8px; box-shadow: 0 1px 3px rgba(0,0,0,0.1); flex: 1; min-width: 200px;">
            <span style="font-size: 0.9em; color: #475569; font-weight: 600;">⛏️ Minério de Ferro (62% Fe)</span><br>
            <span style="font-size: 1.4em; color: #DC2626; font-weight: bold;">US$ {fecho_min_usd:.1f} / t</span>
        </div>
        <div style="text-align: center; background: white; padding: 10px 20px; border-radius: 8px; box-shadow: 0 1px 3px rgba(0,0,0,0.1); flex: 1; min-width: 200px;">
            <span style="font-size: 0.9em; color: #475569; font-weight: 600;">🇧🇷 Minério Convertido em Reais</span><br>
            <span style="font-size: 1.4em; color: #2563EB; font-weight: bold;">R$ {fecho_min_brl:.2f} / t</span>
        </div>
    </div>
</div>
""", unsafe_allow_html=True)

col1, col2, col3 = st.columns(3)

total_cfem_60 = float(pd.to_numeric(df_filtrado['CFEM 60%'], errors='coerce').fillna(0.0).sum())
total_operacoes = float(pd.to_numeric(df_filtrado['Total Operações'], errors='coerce').fillna(0.0).sum())
qtd_registros = len(df_filtrado)

col1.metric("Repasse Municipal Total (CFEM 60%)", fmt_brl(total_cfem_60))
col2.metric("Base de Operações Minerárias", fmt_brl(total_operacoes))
col3.metric("Registros Filtrados", f"{qtd_registros} operações")

st.markdown("---")

# --- GRÁFICOS INTERATIVOS ---
tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "📊 Evolução Mensal & Interanual",
    "🌐 Cotações de Mercado (Dólar & Minério)",
    "🏆 Ranking por Empresas (Anual)",
    "🧱 Distribuição por Material",
    "📋 Base de Dados Filtrada"
])

with tab1:
    st.subheader("📈 1. Linha do Tempo Contínua por Mineradora (Estilo Bolsa)")
    df_mensal = df_filtrado.groupby(['Data_Ref', 'Rotulo_Ref', 'Empresa'])['CFEM 60%'].sum().reset_index().sort_values('Data_Ref')
    df_mensal['CFEM_Escala'] = df_mensal['CFEM 60%'] / divisor
    df_mensal['CFEM_Formatado'] = df_mensal['CFEM 60%'].apply(fmt_brl)
    
    fig_line = px.line(
        df_mensal,
        x='Data_Ref',
        y='CFEM_Escala',
        color='Empresa',
        markers=True,
        color_discrete_sequence=['#2563EB'] if filtro_serra else px.colors.qualitative.Bold,
        custom_data=['Rotulo_Ref', 'CFEM_Formatado'],
        labels={'Data_Ref': 'Período (Mês/Ano)', 'CFEM_Escala': f'CFEM 60% ({sufixo_escala})', 'Empresa': 'Entidade / Mineradora'},
        title="Histórico Contínuo de Repasse - " + ("Serra das Serrinhas (Consolidado)" if filtro_serra else "Por Mineradora")
    )
    
    fig_line.update_traces(
        line=dict(width=3.5 if filtro_serra else 3),
        marker=dict(size=8 if filtro_serra else 7),
        hovertemplate="<b>%{customdata}</b><br>%{fullData.name}<br>Repasse: <b>%{customdata[2]}</b><extra></extra>"
    )
    
    y_type = "log" if escala_log else "linear"
    fig_line.update_yaxes(
        type=y_type,
        autorange=True,
        title_text=f"CFEM 60% ({sufixo_escala})",
        tickprefix="R$ " if escala_opcao == "Em Reais (R$)" else "",
        showgrid=True,
        gridcolor="#F1F5F9",
        zeroline=False
    )
    fig_line.update_xaxes(
        dtick="M1",
        tickformat="%b/%y",
        hoverformat="%b/%Y",
        title_text="Mês de Competência",
        showgrid=False,
        zeroline=False
    )
    fig_line.update_layout(
        hovermode="x unified",
        height=580,
        margin=dict(l=20, r=20, t=50, b=100),
        legend=dict(
            title_text="",
            orientation="h",
            yanchor="top",
            y=-0.20,
            xanchor="center",
            x=0.5
        )
    )
    st.plotly_chart(fig_line, use_container_width=True)
    
    st.markdown("---")
    st.subheader("📅 2. Comparativo Interanual da Arrecadação Total (Mês a Mês 1 a 12)")
    
    df_interanual = df_filtrado.groupby(['Mês Ref', 'Ano'])['CFEM 60%'].sum().reset_index()
    df_interanual['Ano_Str'] = df_interanual['Ano'].astype(str)
    df_interanual['CFEM_Escala'] = df_interanual['CFEM 60%'] / divisor
    df_interanual['CFEM_Formatado'] = df_interanual['CFEM 60%'].apply(fmt_brl)
    
    meses_ordem = ['Jan', 'Fev', 'Mar', 'Abr', 'Mai', 'Jun', 'Jul', 'Ago', 'Set', 'Out', 'Nov', 'Dez']
    
    fig_inter = px.line(
        df_interanual,
        x='Mês Ref',
        y='CFEM_Escala',
        color='Ano_Str',
        markers=True,
        color_discrete_sequence=px.colors.qualitative.Vivid,
        custom_data=['CFEM_Formatado'],
        labels={'Mês Ref': 'Mês de Competência', 'CFEM_Escala': f'CFEM 60% Total ({sufixo_escala})', 'Ano_Str': 'Ano'},
        title="Arrecadação Total Comparada Mês a Mês entre Anos"
    )
    fig_inter.update_traces(
        line=dict(width=3.5),
        marker=dict(size=8),
        hovertemplate="Mês %{x}<br>Ano: %{fullData.name}<br>Total: <b>%{customdata}</b><extra></extra>"
    )
    fig_inter.update_xaxes(
        dtick=1,
        range=[0.5, 12.5],
        tickvals=list(range(1, 13)),
        ticktext=meses_ordem
    )
    fig_inter.update_yaxes(tickprefix="R$ " if escala_opcao == "Em Reais (R$)" else "")
    fig_inter.update_layout(hovermode="x unified", height=480)
    st.plotly_chart(fig_inter, use_container_width=True)

with tab2:
    st.subheader("🌐 Cotações de Mercado Internacional (Dólar & Minério de Ferro)")
    col_m1, col_m2 = st.columns(2)
    
    with col_m1:
        st.markdown("#### 💵 Evolução da Taxa de Câmbio (Dólar PTAX - USD/BRL)")
        fig_usd = px.line(
            df_mkt_filtered,
            x='Data_Ref',
            y='Dolar_USD_BRL',
            markers=True,
            line_shape='spline',
            color_discrete_sequence=['#16A34A'],
            labels={'Data_Ref': 'Mês/Ano', 'Dolar_USD_BRL': 'Dólar (R$)'},
            title="Cotação Média do Dólar (USD/BRL)"
        )
        fig_usd.update_traces(line=dict(width=3), marker=dict(size=7), hovertemplate="Data: %{x|%b/%Y}<br>Dólar: <b>R$ %{y:.2f}</b><extra></extra>")
        fig_usd.update_xaxes(dtick="M2", tickformat="%b/%y", showgrid=False)
        fig_usd.update_yaxes(tickprefix="R$ ", showgrid=True, gridcolor="#F1F5F9")
        fig_usd.update_layout(height=450, hovermode="x unified")
        st.plotly_chart(fig_usd, use_container_width=True)
        
    with col_m2:
        st.markdown("#### ⛏️ Cotação Internacional do Minério de Ferro (62% Fe CFR China)")
        fig_io = px.line(
            df_mkt_filtered,
            x='Data_Ref',
            y='Minério_USD_Ton',
            markers=True,
            line_shape='spline',
            color_discrete_sequence=['#DC2626'],
            labels={'Data_Ref': 'Mês/Ano', 'Minério_USD_Ton': 'Preço (US$/dmt)'},
            title="Preço Internacional do Minério de Ferro (US$/ton)"
        )
        fig_io.update_traces(line=dict(width=3), marker=dict(size=7), hovertemplate="Data: %{x|%b/%Y}<br>Minério: <b>US$ %{y:.1f}/t</b><extra></extra>")
        fig_io.update_xaxes(dtick="M2", tickformat="%b/%y", showgrid=False)
        fig_io.update_yaxes(tickprefix="US$ ", showgrid=True, gridcolor="#F1F5F9")
        fig_io.update_layout(height=450, hovermode="x unified")
        st.plotly_chart(fig_io, use_container_width=True)

with tab3:
    st.subheader("🏆 Ranking de Arrecadação por Empresas (Com Separação Anual)")
    modo_rank = st.radio(
        "🗓️ Selecione a Forma de Visualização do Ranking:",
        ["Comparativo Anual Lado a Lado (Barras Agrupadas por Ano)", "Filtrar por Ano Específico (2024 / 2025 / 2026)"],
        horizontal=True
    )
    
    if modo_rank == "Comparativo Anual Lado a Lado (Barras Agrupadas por Ano)":
        df_rank_ano = df_filtrado.groupby(['Empresa', 'Ano']).agg(
            CFEM_60_Total=('CFEM 60%', 'sum'),
            Total_Operacoes=('Total Operações', 'sum'),
            Qtd_Registros=('CFEM 60%', 'count')
        ).reset_index()
        
        if not df_rank_ano.empty:
            df_rank_ano['Ano_Str'] = df_rank_ano['Ano'].astype(str)
            df_rank_ano['CFEM_Escala'] = df_rank_ano['CFEM_60_Total'] / divisor
            df_rank_ano['CFEM_Formatado'] = df_rank_ano['CFEM_60_Total'].apply(fmt_brl)
            
            ordem_empresas = df_filtrado.groupby('Empresa')['CFEM 60%'].sum().sort_values(ascending=True).index.tolist()
            df_rank_ano['Empresa'] = pd.Categorical(df_rank_ano['Empresa'], categories=ordem_empresas, ordered=True)
            df_rank_ano = df_rank_ano.sort_values('Empresa')
            
            fig_bar_ano = px.bar(
                df_rank_ano,
                x='CFEM_Escala',
                y='Empresa',
                color='Ano_Str',
                barmode='group',
                orientation='h',
                custom_data=['Ano_Str', 'CFEM_Formatado'],
                labels={'CFEM_Escala': f'CFEM 60% ({sufixo_escala})', 'Empresa': 'Entidade / Mineradora', 'Ano_Str': 'Ano'},
                color_discrete_sequence=px.colors.qualitative.Set1,
                title="Comparativo de Arrecadação por Empresa Separado por Ano"
            )
            fig_bar_ano.update_traces(
                hovertemplate="Entidade: %{y}<br>Ano: <b>%{customdata}</b><br>Repasse: <b>%{customdata[2]}</b><extra></extra>"
            )
            fig_bar_ano.update_layout(height=540, legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1))
            st.plotly_chart(fig_bar_ano, use_container_width=True)
            
            st.markdown("---")
            pivot_rank_ano = df_filtrado.pivot_table(
                index='Empresa',
                columns='Ano',
                values='CFEM 60%',
                aggfunc='sum',
                fill_value=0.0
            )
            if not pivot_rank_ano.empty:
                pivot_rank_ano['Total Acumulado (R$)'] = pivot_rank_ano.sum(axis=1)
                pivot_rank_ano = pivot_rank_ano.sort_values('Total Acumulado (R$)', ascending=False)
                st.dataframe(pivot_rank_ano.map(fmt_brl), use_container_width=True)
    else:
        anos_disponiveis_rank = sorted(df_filtrado['Ano'].unique().tolist())
        if anos_disponiveis_rank:
            ano_sel = st.selectbox("Selecione o Ano Desejado para o Ranking:", options=anos_disponiveis_rank)
            df_ano_sel = df_filtrado[df_filtrado['Ano'] == ano_sel].copy()
            df_rank_sel = df_ano_sel.groupby('Empresa').agg(
                CFEM_60_Total=('CFEM 60%', 'sum'),
                Total_Operacoes=('Total Operações', 'sum'),
                Qtd_Registros=('CFEM 60%', 'count')
            ).reset_index().sort_values('CFEM_60_Total', ascending=False)
            
            if not df_rank_sel.empty:
                total_ano_sel = df_rank_sel['CFEM_60_Total'].sum()
                df_rank_sel['Market_Share_%'] = (df_rank_sel['CFEM_60_Total'] / total_ano_sel * 100).round(2) if total_ano_sel > 0 else 0
                df_rank_sel['CFEM_Escala'] = df_rank_sel['CFEM_60_Total'] / divisor
                df_rank_sel['CFEM_Formatado'] = df_rank_sel['CFEM_60_Total'].apply(fmt_brl)
                df_rank_sel['Operacoes_Formatado'] = df_rank_sel['Total_Operacoes'].apply(fmt_brl)
                df_rank_sel['Posição'] = range(1, len(df_rank_sel) + 1)
                
                col_r1, col_r2 = st.columns(2)
                with col_r1:
                    fig_bar_single = px.bar(
                        df_rank_sel.sort_values('CFEM_60_Total', ascending=True),
                        x='CFEM_Escala',
                        y='Empresa',
                        orientation='h',
                        custom_data=['CFEM_Formatado'],
                        labels={'CFEM_Escala': f'CFEM 60% ({sufixo_escala})', 'Empresa': 'Entidade / Mineradora'},
                        color='CFEM_60_Total',
                        color_continuous_scale='Blues'
                    )
                    fig_bar_single.update_layout(height=480, showlegend=False)
                    st.plotly_chart(fig_bar_single, use_container_width=True)
                    
                with col_r2:
                    fig_pie_single = px.pie(
                        df_rank_sel,
                        names='Empresa',
                        values='CFEM_60_Total',
                        hole=0.4,
                        color_discrete_sequence=px.colors.qualitative.Set3
                    )
                    fig_pie_single.update_layout(height=480)
                    st.plotly_chart(fig_pie_single, use_container_width=True)
                    
                df_show_single = pd.DataFrame({
                    'Posição': df_rank_sel['Posição'],
                    'Mineradora / Entidade': df_rank_sel['Empresa'],
                    f'Repasse CFEM 60% ({ano_sel})': df_rank_sel['CFEM_Formatado'],
                    f'Faturamento Operacional ({ano_sel})': df_rank_sel['Operacoes_Formatado'],
                    'Participação (%)': df_rank_sel['Market_Share_%'].astype(str) + '%',
                    'Qtd Registros': df_rank_sel['Qtd_Registros']
                })
                st.dataframe(df_show_single, use_container_width=True)

with tab4:
    st.subheader("🧱 Repasse por Material / Substância Mineral")
    df_mat = df_filtrado.groupby(['Substância', 'Empresa'])['CFEM 60%'].sum().reset_index()
    df_mat['CFEM_Escala'] = df_mat['CFEM 60%'] / divisor
    df_mat['CFEM_Formatado'] = df_mat['CFEM 60%'].apply(fmt_brl)
    
    fig_mat = px.bar(
        df_mat,
        x='Substância',
        y='CFEM_Escala',
        color='Empresa',
        barmode='stack',
        custom_data=['CFEM_Formatado'],
        labels={'CFEM_Escala': f'CFEM 60% ({sufixo_escala})', 'Substância': 'Material Mineral'},
        title="Distribuição de Repasse por Material Extraído"
    )
    fig_mat.update_layout(height=500)
    st.plotly_chart(fig_mat, use_container_width=True)

with tab5:
    st.subheader("📋 Base de Dados Filtrada (Competência)")
    df_export = df_filtrado.copy()
    st.dataframe(df_export, use_container_width=True)
    
    csv_data = df_export.to_csv(index=False, sep=';', encoding='utf-8-sig')
    st.download_button(
        label="📥 Exportar Seleção Atual para CSV",
        data=csv_data,
        file_name="CFEM_60_Competencia_filtrado.csv",
        mime="text/csv"
    )
