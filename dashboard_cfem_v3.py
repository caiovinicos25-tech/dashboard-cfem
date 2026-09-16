import streamlit as st
import pandas as pd
import plotly.express as px

# Configuração da página no Streamlit
st.set_page_config(
    page_title="Dashboard BI - CFEM Mineração",
    page_icon="⛏️",
    layout="wide"
)

# Função para formatação padrão em Moeda Brasileira (R$ 1.234.567,89)
def fmt_brl(valor):
    if pd.isna(valor):
        return "R$ 0,00"
    return f"R$ {valor:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')

# Carregamento e tratamento dos dados (Apenas Competência)
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
    
    # Criar datas reais para a linha do tempo contínua por Mês de Competência
    df['Data_Ref'] = pd.to_datetime(df['Ano'].astype(str) + '-' + df['Mês Ref'].astype(str).str.zfill(2) + '-01')
    
    # Mapeamento de rótulos dos meses em PT-BR (ex: Jan/24, Fev/25)
    meses_pt = {1: 'Jan', 2: 'Fev', 3: 'Mar', 4: 'Abr', 5: 'Mai', 6: 'Jun',
                7: 'Jul', 8: 'Ago', 9: 'Set', 10: 'Out', 11: 'Nov', 12: 'Dez'}
    
    df['Rotulo_Ref'] = df['Mês Ref'].map(meses_pt) + '/' + df['Ano'].astype(str).str[-2:]
    df['Nome_Mes'] = df['Mês Ref'].map(meses_pt)
    
    return df

try:
    df = load_data()
except Exception as e:
    st.error(f"Erro ao carregar os dados. Verifique o arquivo CSV: {e}")
    st.stop()

# --- BARRA LATERAL: FILTROS DINÂMICOS ---
st.sidebar.header("🎛️ Filtros do Dashboard")

# Unidades/Escala financeira
escala_opcao = st.sidebar.radio("Exibição dos Valores nos Gráficos:", ["Em Reais (R$)", "Em Milhões (R$ Mi)"])
divisor = 1_000_000.0 if escala_opcao == "Em Milhões (R$ Mi)" else 1.0
sufixo_escala = "Mi" if escala_opcao == "Em Milhões (R$ Mi)" else "R$"

st.sidebar.markdown("---")

# Opção de Escala Visual do Eixo Y no Gráfico de Linhas
escala_log = st.sidebar.checkbox("🔍 Ampliar visibilidade de pequenas empresas (Escala Logarítmica Y)", value=False)

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

# Aplicação dos filtros pré-estabelecidos
df_filtrado = df[
    (df['Ano'].isin(anos_selecionados)) &
    (df['Empresa'].isin(empresas_selecionadas)) &
    (df['Substância'].isin(substancias_selecionadas))
].copy()

# --- TÍTULO E KPIS PRINCIPAIS ---
st.title("⛏️ Dashboard de Acompanhamento CFEM 60% (Competência)")
st.markdown("Visão executiva dos repasses municipais da CFEM baseados no **Mês de Competência** (fato gerador operacional).")

col1, col2, col3 = st.columns(3)

total_cfem_60 = float(pd.to_numeric(df_filtrado['CFEM 60%'], errors='coerce').fillna(0.0).sum())
total_operacoes = float(pd.to_numeric(df_filtrado['Total Operações'], errors='coerce').fillna(0.0).sum())
qtd_registros = len(df_filtrado)

col1.metric("Repasse Municipal Total (CFEM 60%)", fmt_brl(total_cfem_60))
col2.metric("Base de Operações Minerárias", fmt_brl(total_operacoes))
col3.metric("Registros Filtrados", f"{qtd_registros} operações")

st.markdown("---")

# --- GRÁFICOS INTERATIVOS ---
tab1, tab2, tab3, tab4 = st.tabs([
    "📊 Evolução Mensal & Interanual",
    "🏆 Ranking por Empresas (Separação Anual)",
    "🧱 Distribuição por Material",
    "📋 Base de Dados Filtrada"
])

with tab1:
    st.subheader("📈 1. Linha do Tempo Contínua por Mineradora (Estilo Bolsa)")
    st.markdown("Evolução temporal sequencial contínua de repasse por empresa com padronização em Reais (R$) e ajuste de amplitude visual.")

    df_mensal = df_filtrado.groupby(['Data_Ref', 'Rotulo_Ref', 'Empresa'])['CFEM 60%'].sum().reset_index().sort_values('Data_Ref')
    df_mensal['CFEM_Escala'] = df_mensal['CFEM 60%'] / divisor
    df_mensal['CFEM_Formatado'] = df_mensal['CFEM 60%'].apply(fmt_brl)
    
    fig_line = px.line(
        df_mensal,
        x='Data_Ref',
        y='CFEM_Escala',
        color='Empresa',
        markers=True,
        color_discrete_sequence=px.colors.qualitative.Bold,
        custom_data=['Rotulo_Ref', 'CFEM_Formatado'],
        labels={'Data_Ref': 'Período (Mês/Ano)', 'CFEM_Escala': f'CFEM 60% ({sufixo_escala})', 'Empresa': 'Mineradora'},
        title="Histórico Contínuo de Repasse por Mineradora"
    )
    
    fig_line.update_traces(
        line=dict(width=3),
        marker=dict(size=7),
        hovertemplate="<b>%{customdata}</b><br>%{fullData.name}<br>Repasse: <b>%{customdata[1]}</b><extra></extra>"
    )
    
    y_type = "log" if escala_log else "linear"
    fig_line.update_yaxes(
        type=y_type,
        autorange=True,
        title_text=f"CFEM 60% ({sufixo_escala})",
        tickprefix="R$ " if escala_opcao == "Em Reais (R$)" else "",
        showgrid=True,
        gridcolor="#E2E8F0"
    )
    fig_line.update_xaxes(
        dtick="M1",
        tickformat="%b/%y",
        hoverformat="%b/%Y",
        title_text="Mês de Competência",
        showgrid=True,
        gridcolor="#E2E8F0"
    )
    fig_line.update_layout(
        hovermode="x unified",
        height=540,
        margin=dict(l=20, r=20, t=50, b=30),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
    )
    st.plotly_chart(fig_line, use_container_width=True)
    
    st.markdown("---")
    
    st.subheader("📅 2. Comparativo Interanual da Arrecadação Total (Mês a Mês 1 a 12)")
    st.markdown("Comparação direta do volume total arrecadado mês a mês entre os anos (2024 vs 2025 vs 2026).")
    
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
    fig_inter.update_yaxes(
        tickprefix="R$ " if escala_opcao == "Em Reais (R$)" else ""
    )
    fig_inter.update_layout(hovermode="x unified", height=480)
    st.plotly_chart(fig_inter, use_container_width=True)
    
    st.markdown("📋 **Valores Exatos do Repasse Mensal (R$) por Mineradora (Jan/24 a Mai/26):**")
    pivot_df = df_filtrado.pivot_table(
        index='Empresa',
        columns=['Data_Ref', 'Rotulo_Ref'],
        values='CFEM 60%',
        aggfunc='sum',
        fill_value=0.0
    )
    if not pivot_df.empty:
        colunas_ordenadas = sorted(pivot_df.columns, key=lambda x: x)
        pivot_df = pivot_df[colunas_ordenadas]
        pivot_df.columns = [col for col in pivot_df.columns]
        
        pivot_df_fmt = pivot_df.map(fmt_brl)
        st.dataframe(pivot_df_fmt, use_container_width=True)

with tab2:
    st.subheader("🏆 Ranking de Arrecadação por Empresas (Com Separação Anual)")
    st.markdown("Visualização separada por ano, garantindo que os valores dos exercícios não sejam somados indistintamente.")
    
    modo_rank = st.radio(
        "🗓️ Selecione a Forma de Visualização do Ranking:",
        ["Comparativo Anual Lado a Lado (Barras Agrupadas por Ano)", "Filtrar por Ano Específico (2024 / 2025 / 2026)"],
        horizontal=True
    )
    
    if modo_rank == "Comparativo Anual Lado a Lado (Barras Agrupadas por Ano)":
        st.markdown("#### 📊 Arrecadação Anual por Empresa (Sem Somar os Anos)")
        
        df_rank_ano = df_filtrado.groupby(['Empresa', 'Ano']).agg(
            CFEM_60_Total=('CFEM 60%', 'sum'),
            Total_Operacoes=('Total Operações', 'sum'),
            Qtd_Registros=('CFEM 60%', 'count')
        ).reset_index()
        
        if not df_rank_ano.empty:
            df_rank_ano['Ano_Str'] = df_rank_ano['Ano'].astype(str)
            df_rank_ano['CFEM_Escala'] = df_rank_ano['CFEM_60_Total'] / divisor
            df_rank_ano['CFEM_Formatado'] = df_rank_ano['CFEM_60_Total'].apply(fmt_brl)
            
            # Ordenar por total geral acumulado para consistência de exibição
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
                labels={'CFEM_Escala': f'CFEM 60% ({sufixo_escala})', 'Empresa': 'Mineradora', 'Ano_Str': 'Ano'},
                color_discrete_sequence=px.colors.qualitative.Set1,
                title="Comparativo de Arrecadação por Empresa Separado por Ano"
            )
            fig_bar_ano.update_traces(
                hovertemplate="Mineradora: %{y}<br>Ano: <b>%{customdata}</b><br>Repasse: <b>%{customdata[1]}</b><extra></extra>"
            )
            fig_bar_ano.update_layout(height=540, legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1))
            st.plotly_chart(fig_bar_ano, use_container_width=True)
            
            st.markdown("---")
            st.markdown("#### 📋 Tabela Comparativa de Arrecadação Anual por Mineradora (R$)")
            
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
                
                pivot_rank_fmt = pivot_rank_ano.map(fmt_brl)
                st.dataframe(pivot_rank_fmt, use_container_width=True)
        else:
            st.info("Nenhum dado encontrado para os filtros selecionados.")
            
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
                    st.markdown(f"#### 📊 Ranking Oficial - Ano {ano_sel}")
                    fig_bar_single = px.bar(
                        df_rank_sel.sort_values('CFEM_60_Total', ascending=True),
                        x='CFEM_Escala',
                        y='Empresa',
                        orientation='h',
                        custom_data=['CFEM_Formatado'],
                        labels={'CFEM_Escala': f'CFEM 60% ({sufixo_escala})', 'Empresa': 'Mineradora'},
                        color='CFEM_60_Total',
                        color_continuous_scale='Blues'
                    )
                    fig_bar_single.update_traces(
                        hovertemplate="Mineradora: %{y}<br>Repasse em " + str(ano_sel) + ": <b>%{customdata}</b><extra></extra>"
                    )
                    fig_bar_single.update_layout(height=480, showlegend=False)
                    st.plotly_chart(fig_bar_single, use_container_width=True)
                    
                with col_r2:
                    st.markdown(f"#### 🍕 Participação no Repasse (% Market Share) - {ano_sel}")
                    fig_pie_single = px.pie(
                        df_rank_sel,
                        names='Empresa',
                        values='CFEM_60_Total',
                        hole=0.4,
                        custom_data=['CFEM_Formatado'],
                        color_discrete_sequence=px.colors.qualitative.Set3
                    )
                    fig_pie_single.update_traces(
                        textposition='inside',
                        textinfo='percent+label',
                        hovertemplate="Mineradora: %{label}<br>Repasse: <b>%{customdata}</b><br>Participação: %{percent}<extra></extra>"
                    )
                    fig_pie_single.update_layout(height=480)
                    st.plotly_chart(fig_pie_single, use_container_width=True)
                    
                st.markdown("---")
                st.markdown(f"#### 📋 Tabela do Ranking de Mineradoras - Exercício {ano_sel}")
                
                df_show_single = pd.DataFrame({
                    'Posição': df_rank_sel['Posição'],
                    'Mineradora': df_rank_sel['Empresa'],
                    f'Repasse CFEM 60% ({ano_sel})': df_rank_sel['CFEM_Formatado'],
                    f'Faturamento Operacional ({ano_sel})': df_rank_sel['Operacoes_Formatado'],
                    'Participação (%)': df_rank_sel['Market_Share_%'].astype(str) + '%',
                    'Qtd Registros': df_rank_sel['Qtd_Registros']
                })
                
                st.dataframe(df_show_single, use_container_width=True)
        else:
            st.info("Nenhum ano disponível nos filtros selecionados.")

with tab3:
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
    fig_mat.update_traces(
        hovertemplate="Material: %{x}<br>Empresa: %{fullData.name}<br>Repasse: <b>%{customdata}</b><extra></extra>"
    )
    fig_mat.update_layout(height=500)
    st.plotly_chart(fig_mat, use_container_width=True)

with tab4:
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
