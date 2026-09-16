import streamlit as st
import pandas as pd
import plotly.express as px

# Configuração da página no Streamlit
st.set_page_config(
    page_title="Dashboard BI - CFEM Mineração",
    page_icon="⛏️",
    layout="wide"
)

# Carregamento e tratamento dos dados com conversão numérica incondicional
@st.cache_data(ttl=3600)
def load_data():
    df = pd.read_csv('Planilha_CFEM_consolidada.csv', sep=';', encoding='utf-8-sig')
    
    # Converter colunas numéricas de forma incondicional e blindada
    num_cols = ['Total Operações', 'CFEM 100%', 'CFEM 60%']
    for col in num_cols:
        s = df[col].astype(str)
        s = s.str.replace('.', '', regex=False).str.replace(',', '.', regex=False)
        df[col] = pd.to_numeric(s, errors='coerce').fillna(0.0)
            
    df['Ano'] = pd.to_numeric(df['Ano'], errors='coerce').fillna(0).astype(int)
    df['Mês Ref'] = pd.to_numeric(df['Mês Ref'], errors='coerce').fillna(0).astype(int)
    df['Mês Pagto'] = pd.to_numeric(df['Mês Pagto'], errors='coerce').fillna(0).astype(int)
    df['Possível Inconsistência'] = df['Possível Inconsistência'].fillna('Regular')
    
    # Criar datas reais para a linha do tempo contínua
    df['Data_Ref'] = pd.to_datetime(df['Ano'].astype(str) + '-' + df['Mês Ref'].astype(str).str.zfill(2) + '-01')
    df['Data_Pagto'] = pd.to_datetime(df['Ano'].astype(str) + '-' + df['Mês Pagto'].astype(str).str.zfill(2) + '-01')
    
    # Mapeamento de rótulos dos meses em PT-BR (ex: Jan/24, Fev/25)
    meses_pt = {1: 'Jan', 2: 'Fev', 3: 'Mar', 4: 'Abr', 5: 'Mai', 6: 'Jun',
                7: 'Jul', 8: 'Ago', 9: 'Set', 10: 'Out', 11: 'Nov', 12: 'Dez'}
    
    df['Rotulo_Ref'] = df['Mês Ref'].map(meses_pt) + '/' + df['Ano'].astype(str).str[-2:]
    df['Rotulo_Pagto'] = df['Mês Pagto'].map(meses_pt) + '/' + df['Ano'].astype(str).str[-2:]
    
    return df

try:
    df = load_data()
except Exception as e:
    st.error(f"Erro ao carregar os dados. Verifique o arquivo CSV: {e}")
    st.stop()

# --- BARRA LATERAL: FILTROS DINÂMICOS ---
st.sidebar.header("🎛️ Filtros do Dashboard")

# Unidades/Escala financeira
escala_opcao = st.sidebar.radio("Exibição dos Valores nos Gráficos:", ["Em Milhões (R$ Mi)", "Em Reais (R$)"])
divisor = 1_000_000.0 if escala_opcao == "Em Milhões (R$ Mi)" else 1.0
sufixo_escala = "Mi" if escala_opcao == "Em Milhões (R$ Mi)" else "R$"

st.sidebar.markdown("---")

# Filtro de Ano
anos_disponiveis = sorted(df['Ano'].unique().tolist())
anos_selecionados = st.sidebar.multiselect(
    "Selecione os Anos:",
    options=anos_disponiveis,
    default=anos_disponiveis
)

# Filtro de Empresa
empresas_disponiveis = sorted(df['Empresa'].unique().tolist())
empresas_selecionadas = st.sidebar.multiselect(
    "Selecione as Mineradoras:",
    options=empresas_disponiveis,
    default=empresas_disponiveis
)

# Filtro de Substância
substancias_disponiveis = sorted(df['Substância'].unique().tolist())
substancias_selecionadas = st.sidebar.multiselect(
    "Selecione os Materiais/Substâncias:",
    options=substancias_disponiveis,
    default=substancias_disponiveis
)

# Filtro de Inconsistência
status_inconsistencias = sorted(df['Possível Inconsistência'].unique().tolist())
status_selecionados = st.sidebar.multiselect(
    "Status de Pagamento:",
    options=status_inconsistencias,
    default=status_inconsistencias
)

# Aplicação dos filtros
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

total_cfem_60 = float(pd.to_numeric(df_filtrado['CFEM 60%'], errors='coerce').fillna(0.0).sum())
total_operacoes = float(pd.to_numeric(df_filtrado['Total Operações'], errors='coerce').fillna(0.0).sum())
inconsistentes = df_filtrado[df_filtrado['Possível Inconsistência'] != 'Regular']
val_inconsistente = float(pd.to_numeric(inconsistentes['CFEM 60%'], errors='coerce').fillna(0.0).sum())
qtd_registros = len(df_filtrado)

col1.metric("Repasse Municipal Total (CFEM 60%)", f"R$ {total_cfem_60:,.2f}")
col2.metric("Base de Operações Minerárias", f"R$ {total_operacoes:,.2f}")
col3.metric("Repasse Sob Inconsistência", f"R$ {val_inconsistente:,.2f}", f"{len(inconsistentes)} registros", delta_color="inverse")
col4.metric("Registros Filtrados", f"{qtd_registros} linhas")

st.markdown("---")

# --- GRÁFICOS INTERATIVOS ---
tab1, tab2, tab3, tab4 = st.tabs(["📊 Evolução Mensal Contínua", "🏢 Comparativo por Empresa & Material", "⚠️ Auditoria de Inconsistências", "📋 Tabela de Dados"])

with tab1:
    st.subheader("📈 Linha do Tempo Contínua do Repasse Municipal (CFEM 60%)")
    st.markdown("Evolução temporal sequencial contínua (estilo mercado financeiro), sem sobreposição de anos.")
    
    criterio_mes = st.radio(
        "🗓️ Escolha a Referência Temporal do Gráfico:",
        ["Mês de Competência (Mês Ref)", "Mês de Pagamento (Mês Pagto)"],
        horizontal=True
    )
    
    if "Competência" in criterio_mes:
        col_dt = 'Data_Ref'
        col_rotulo = 'Rotulo_Ref'
        label_eixo_x = "Período de Competência (Mês/Ano)"
    else:
        col_dt = 'Data_Pagto'
        col_rotulo = 'Rotulo_Pagto'
        label_eixo_x = "Período de Pagamento (Mês/Ano)"

    # Agrupar por data contínua e empresa
    df_mensal = df_filtrado.groupby([col_dt, col_rotulo, 'Empresa'])['CFEM 60%'].sum().reset_index().sort_values(col_dt)
    df_mensal['CFEM_Escala'] = df_mensal['CFEM 60%'] / divisor
    
    # Gráfico de linha contínuo longo estilo bolsa de valores
    fig_line = px.line(
        df_mensal,
        x=col_dt,
        y='CFEM_Escala',
        color='Empresa',
        markers=True,
        color_discrete_sequence=px.colors.qualitative.Bold,
        labels={col_dt: label_eixo_x, 'CFEM_Escala': f'CFEM 60% ({sufixo_escala})', 'Empresa': 'Mineradora'},
        title=f"Histórico Contínuo de Repasse por Mineradora ({label_eixo_x})"
    )
    
    fig_line.update_traces(line=dict(width=3), marker=dict(size=7))
    fig_line.update_xaxes(
        dtick="M1",
        tickformat="%b/%y",
        hoverformat="%b/%Y",
        title_text=label_eixo_x
    )
    fig_line.update_layout(
        hovermode="x unified",
        height=560,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
    )
    st.plotly_chart(fig_line, use_container_width=True)
    
    st.markdown(f"**📋 Tabela de Valores Exatos (R$) por Período Sequencial ({label_eixo_x}):**")
    
    # Criar Tabela Pivot Cronológica
    pivot_df = df_filtrado.pivot_table(
        index='Empresa',
        columns=[col_dt, col_rotulo],
        values='CFEM 60%',
        aggfunc='sum',
        fill_value=0.0
    )
    
    if not pivot_df.empty:
        # Ordenar colunas pela Data real e usar o Rótulo (Jan/24, Fev/24...) como cabeçalho
        colunas_ordenadas = sorted(pivot_df.columns, key=lambda x: x)
        pivot_df = pivot_df[colunas_ordenadas]
        pivot_df.columns = [col[1] for col in pivot_df.columns]
        
        st.dataframe(pivot_df.style.format("R$ {:,.2f}"), use_container_width=True)
    else:
        st.info("Nenhum dado encontrado para os filtros selecionados.")

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
    st.markdown("Registros em que o mês de pagamento difere do mês de referência regular (ex: pagamentos em lote ou atrasados).")
    
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
