import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

# Configuração da página no Streamlit
st.set_page_config(
    page_title="Dashboard BI - CFEM Mineração",
    page_icon="⛏️",
    layout="wide"
)

# Carregamento e tratamento super robusto dos dados
@st.cache_data
def load_data():
    # Tenta carregar o CSV local
    df = pd.read_csv('Planilha_CFEM_consolidada.csv', sep=';', encoding='utf-8-sig')
    
    # Garantir conversão estrita de colunas numéricas
    num_cols = ['Total Operações', 'CFEM 100%', 'CFEM 60%']
    for col in num_cols:
        if col in df.columns:
            # Forçar conversão de texto formatado (ex: '96.565,22') para float
            s = df[col].astype(str).str.replace('R$', '', regex=False).str.strip()
            s = s.str.replace('.', '', regex=False).str.replace(',', '.', regex=False)
            df[col] = pd.to_numeric(s, errors='coerce').fillna(0.0)
            
    df['Ano'] = pd.to_numeric(df['Ano'], errors='coerce').fillna(0).astype(int)
    df['Mês Ref'] = pd.to_numeric(df['Mês Ref'], errors='coerce').fillna(0).astype(int)
    df['Mês Pagto'] = pd.to_numeric(df['Mês Pagto'], errors='coerce').fillna(0).astype(int)
    df['Possível Inconsistência'] = df['Possível Inconsistência'].fillna('Regular').astype(str)
    
    return df

try:
    df = load_data()
except Exception as e:
    st.error(f"Erro ao carregar o arquivo 'Planilha_CFEM_consolidada.csv': {e}")
    st.stop()

# --- BARRA LATERAL: FILTROS DINÂMICOS ---
st.sidebar.header("🎛️ Filtros do Dashboard")

# Unidades/Escala financeira
escala_opcao = st.sidebar.radio("Exibição dos Valores nos Gráficos:", ["Em Milhões (R$ Mi)", "Em Reais (R$)"])
divisor = 1_000_000.0 if escala_opcao == "Em Milhões (R$ Mi)" else 1.0
sufixo_escala = "Mi" if escala_opcao == "Em Milhões (R$ Mi)" else "R$"

st.sidebar.markdown("---")

# Filtro de Mineradora
empresas_disponiveis = sorted(df['Empresa'].dropna().unique().tolist())
empresas_selecionadas = st.sidebar.multiselect(
    "Selecione as Mineradoras:",
    options=empresas_disponiveis,
    default=empresas_disponiveis
)

# Filtro de Ano
anos_disponiveis = sorted(df['Ano'].dropna().unique().tolist())
anos_selecionados = st.sidebar.multiselect(
    "Selecione os Anos:",
    options=anos_disponiveis,
    default=anos_disponiveis
)

# Filtro de Substância / Material
substancias_disponiveis = sorted(df['Substância'].dropna().unique().tolist())
substancias_selecionadas = st.sidebar.multiselect(
    "Selecione os Materiais/Substâncias:",
    options=substancias_disponiveis,
    default=substancias_disponiveis
)

# Filtro de Inconsistência
status_inconsistencias = sorted(df['Possível Inconsistência'].dropna().unique().tolist())
status_selecionados = st.sidebar.multiselect(
    "Status de Pagamento:",
    options=status_inconsistencias,
    default=status_inconsistencias
)

# Aplicação dos filtros no DataFrame
df_filtrado = df[
    (df['Ano'].isin(anos_selecionados)) &
    (df['Empresa'].isin(empresas_selecionadas)) &
    (df['Substância'].isin(substancias_selecionadas)) &
    (df['Possível Inconsistência'].isin(status_selecionados))
].copy()

# --- TÍTULO E KPIS PRINCIPAIS ---
st.title("⛏️ Dashboard de Acompanhamento CFEM 60% (Repasse Municipal)")
st.markdown("Visão clara e interativa dos repasses municipais da CFEM correlacionados por empresa, material e período.")

col1, col2, col3, col4 = st.columns(4)

total_cfem_60 = float(df_filtrado['CFEM 60%'].sum())
total_operacoes = float(df_filtrado['Total Operações'].sum())
inconsistentes = df_filtrado[df_filtrado['Possível Inconsistência'].str.contains('SIM', case=False, na=False)]
val_inconsistente = float(inconsistentes['CFEM 60%'].sum())
qtd_registros = len(df_filtrado)

col1.metric("Repasse Municipal Total (CFEM 60%)", f"R$ {total_cfem_60:,.2f}")
col2.metric("Base de Operações Minerárias", f"R$ {total_operacoes:,.2f}")
col3.metric("Repasse Sob Inconsistência", f"R$ {val_inconsistente:,.2f}", f"{len(inconsistentes)} registros", delta_color="inverse")
col4.metric("Registros Filtrados", f"{qtd_registros} linhas")

st.markdown("---")

# --- GRÁFICOS INTERATIVOS ---
tab1, tab2, tab3, tab4 = st.tabs(["📊 Evolução Mensal (Linhas)", "🏢 Comparativo por Empresa & Material", "⚠️ Auditoria de Inconsistências", "📋 Tabela de Dados"])

with tab1:
    st.subheader("Comparativo Mês a Mês do Repasse Municipal (CFEM 60%)")
    
    modo_visao = st.radio("Modo de Visualização:", ["Comparar Empresas no Ano/Período", "Evolução Interanual (2024 vs 2025 vs 2026)"], horizontal=True)
    
    if modo_visao == "Comparar Empresas no Ano/Período":
        df_mensal = df_filtrado.groupby(['Mês Ref', 'Empresa'])['CFEM 60%'].sum().reset_index()
        df_mensal['CFEM_Escala'] = df_mensal['CFEM 60%'] / divisor
        
        fig_line = px.line(
            df_mensal,
            x='Mês Ref',
            y='CFEM_Escala',
            color='Empresa',
            markers=True,
            color_discrete_sequence=px.colors.qualitative.Bold,
            labels={'Mês Ref': 'Mês de Referência', 'CFEM_Escala': f'CFEM 60% ({sufixo_escala})'},
            title="Repasse Mensal por Mineradora (Linhas Distintas em Alto Contraste)"
        )
        fig_line.update_traces(line=dict(width=3), marker=dict(size=8))
        fig_line.update_xaxes(dtick=1, range=[0.5, 12.5])
        fig_line.update_layout(hovermode="x unified", height=520)
        st.plotly_chart(fig_line, use_container_width=True)
        
        st.markdown("**Valores Exatos do Repasse Mensal (R$) por Mineradora:**")
        if len(df_filtrado) > 0:
            pivot_mensal = df_filtrado.pivot_table(index='Empresa', columns='Mês Ref', values='CFEM 60%', aggfunc='sum', fill_value=0)
            st.dataframe(pivot_mensal.style.format("R$ {:,.2f}"), use_container_width=True)
        else:
            st.info("Nenhum dado selecionado.")
        
    else:
        df_interanual = df_filtrado.groupby(['Mês Ref', 'Ano'])['CFEM 60%'].sum().reset_index()
        df_interanual['Ano'] = df_interanual['Ano'].astype(str)
        df_interanual['CFEM_Escala'] = df_interanual['CFEM 60%'] / divisor
        
        fig_inter = px.line(
            df_interanual,
            x='Mês Ref',
            y='CFEM_Escala',
            color='Ano',
            markers=True,
            labels={'Mês Ref': 'Mês de Referência', 'CFEM_Escala': f'CFEM 60% ({sufixo_escala})'},
            title="Evolução do Repasse Municipal Mês a Mês Comparando Exercícios"
        )
        fig_inter.update_traces(line=dict(width=3), marker=dict(size=8))
        fig_inter.update_xaxes(dtick=1, range=[0.5, 12.5])
        fig_inter.update_layout(hovermode="x unified", height=500)
        st.plotly_chart(fig_inter, use_container_width=True)

with tab2:
    col_c1, col_c2 = st.columns(2)
    
    with col_c1:
        st.subheader("Ranking de Repasse por Mineradora")
        df_emp = df_filtrado.groupby('Empresa')['CFEM 60%'].sum().reset_index().sort_values('CFEM 60%', ascending=True)
        df_emp['CFEM_Escala'] = df_emp['CFEM 60%'] / divisor
        
        fig_bar_emp = px.bar(
            df_emp,
            x='CFEM_Escala',
            y='Empresa',
            orientation='h',
            text_auto='.2f',
            labels={'CFEM_Escala': f'CFEM 60% ({sufixo_escala})', 'Empresa': ''},
            color='CFEM 60%',
            color_continuous_scale='Viridis'
        )
        fig_bar_emp.update_layout(height=480, showlegend=False)
        st.plotly_chart(fig_bar_emp, use_container_width=True)
        
    with col_c2:
        st.subheader("Participação % por Mineradora (Market Share)")
        fig_pie = px.pie(
            df_emp,
            names='Empresa',
            values='CFEM 60%',
            hole=0.4,
            title="Distribuição da Cota Municipal"
        )
        fig_pie.update_traces(textposition='inside', textinfo='percent+label')
        fig_pie.update_layout(height=480)
        st.plotly_chart(fig_pie, use_container_width=True)

    st.markdown("---")
    
    st.subheader("Repasse por Material / Substância Mineral")
    df_mat = df_filtrado.groupby(['Substância', 'Empresa'])['CFEM 60%'].sum().reset_index()
    df_mat['CFEM_Escala'] = df_mat['CFEM 60%'] / divisor
    
    fig_mat = px.bar(
        df_mat,
        x='Substância',
        y='CFEM_Escala',
        color='Empresa',
        barmode='stack',
        labels={'CFEM_Escala': f'CFEM 60% ({sufixo_escala})', 'Substância': 'Material Mineral'},
        title="Distribuição por Material Extraído"
    )
    fig_mat.update_layout(height=450)
    st.plotly_chart(fig_mat, use_container_width=True)

with tab3:
    st.subheader("⚠️ Auditoria de Inconsistências Temporal de Pagamento")
    st.markdown("Registros em que o mês de pagamento difere do mês de referência regular (ex: pagamentos em lote ou antecipados).")
    
    if len(inconsistentes) > 0:
        st.warning(f"Atenção: Foram encontrados {len(inconsistentes)} registros com possível inconsistência, somando R$ {val_inconsistente:,.2f} de repasse municipal.")
        st.dataframe(inconsistentes[['Ano', 'Empresa', 'Substância', 'Mês Ref', 'Mês Pagto', 'CFEM 100%', 'CFEM 60%', 'Possível Inconsistência']], use_container_width=True)
    else:
        st.success("Nenhuma inconsistência nos filtros selecionados.")

with tab4:
    st.subheader("📋 Base de Dados Filtrada")
    st.dataframe(df_filtrado, use_container_width=True)
    
    csv_data = df_filtrado.to_csv(index=False, sep=';', encoding='utf-8-sig')
    st.download_button(
        label="📥 Exportar Seleção Atual para CSV",
        data=csv_data,
        file_name="CFEM_60_filtrado.csv",
        mime="text/csv"
    )
