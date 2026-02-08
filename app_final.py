import streamlit as st
import pandas as pd
import time
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
from io import BytesIO
import pytz

# Tenta importar o módulo db_rh
try:
    import db_rh as db
except Exception as e:
    st.error(f"Erro ao carregar o módulo 'db_rh.py'. Erro: {e}")

# Configuração da Página
st.set_page_config(
    page_title="GRUPO SANTIN - Controle de Obras",
    page_icon="🏗️",
    layout="wide"
)

# --- ESTILIZAÇÃO CUSTOMIZADA (Padrão Corporativo) ---
st.markdown("""
    <style>
    .main { background-color: #FFFFFF; }
    
    /* Botões Grandes e Centralizados */
    .stButton>button { 
        border-radius: 8px; 
        height: 3.5em; 
        width: 100%; 
        background-color: #FFD700;
        color: #000000;
        font-weight: bold;
        border: 2px solid #000000;
        font-size: 16px;
        transition: 0.3s;
    }
    .stButton>button:hover {
        background-color: #000000;
        color: #FFD700;
        border: 2px solid #FFD700;
    }
    
    /* Cards de Métricas */
    .metric-card {
        background-color: #F8F9FA;
        padding: 20px;
        border-radius: 12px;
        box-shadow: 0 4px 12px rgba(0,0,0,0.08);
        text-align: center;
        border-top: 6px solid #FFD700;
        border-left: 1px solid #DEE2E6;
        margin-bottom: 20px;
    }
    
    /* Cabeçalhos */
    .header-style {
        color: #000000;
        font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
        border-bottom: 4px solid #FFD700;
        padding-bottom: 12px;
        margin-bottom: 25px;
        font-weight: 800;
        text-transform: uppercase;
        letter-spacing: 1px;
    }
    
    /* Relógio */
    .clock-style {
        text-align: right;
        font-size: 15px;
        color: #333;
        font-weight: 600;
        margin-bottom: -45px;
        padding-right: 10px;
    }
    
    /* Footer */
    .footer {
        position: fixed;
        left: 0;
        bottom: 0;
        width: 100%;
        background-color: #f1f1f1;
        color: #333;
        text-align: center;
        padding: 10px;
        font-size: 14px;
        border-top: 2px solid #FFD700;
        z-index: 999;
    }
    .footer a {
        margin: 0 15px;
        text-decoration: none;
        color: #000;
        font-weight: bold;
    }
    
    /* Splash Screen Animado */
    @keyframes fadeIn { from { opacity: 0; } to { opacity: 1; } }
    @keyframes pulse { 0% { transform: scale(1); } 50% { transform: scale(1.05); } 100% { transform: scale(1); } }
    
    #splash-screen {
        position: fixed;
        top: 0;
        left: 0;
        width: 100%;
        height: 100%;
        background-color: #000;
        display: flex;
        justify-content: center;
        align-items: center;
        z-index: 9999;
        color: #FFD700;
        flex-direction: column;
        animation: fadeIn 1s ease-in;
    }
    .splash-logo {
        font-size: 60px;
        font-weight: 900;
        animation: pulse 2s infinite;
        text-shadow: 0 0 20px rgba(255, 215, 0, 0.5);
    }
    </style>
    """, unsafe_allow_html=True)

# --- CORREÇÃO DE HORÁRIO (Brasília) ---
def get_now_br():
    tz_br = pytz.timezone('America/Sao_Paulo')
    return datetime.now(tz_br)

# --- INICIALIZAÇÃO DE ESTADO ---
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False
if 'form_key' not in st.session_state:
    st.session_state.form_key = 0
if 'splash_done' not in st.session_state:
    st.session_state.splash_done = False

# --- TELA DE ABERTURA (SPLASH) ---
if not st.session_state.splash_done:
    splash = st.empty()
    with splash.container():
        st.markdown("""
            <div id="splash-screen">
                <div class="splash-logo">🏗️ GRUPO SANTIN</div>
                <p style='font-size: 22px; letter-spacing: 8px; margin-top: 10px;'>CONTROLE DE OBRAS & BI</p>
                <div style='margin-top: 30px; font-family: monospace; opacity: 0.8;'>Iniciando ambiente seguro...</div>
            </div>
        """, unsafe_allow_html=True)
        time.sleep(3.0)
    splash.empty()
    st.session_state.splash_done = True

# --- FUNÇÕES DE AUXÍLIO ---
def reset_form():
    st.session_state.form_key += 1

def calcular_horas(e, s_a, r_a, s_f):
    try:
        fmt = '%H:%M:%S'
        t1 = datetime.strptime(str(e), fmt)
        t2 = datetime.strptime(str(s_a), fmt)
        t3 = datetime.strptime(str(r_a), fmt)
        t4 = datetime.strptime(str(s_f), fmt)
        p1 = t2 - t1
        p2 = t4 - t3
        total = p1 + p2
        total_segundos = total.total_seconds()
        horas = int(total_segundos // 3600)
        minutos = int((total_segundos % 3600) // 60)
        return f"{horas:02d}:{minutos:02d}"
    except:
        return "00:00"

def horas_para_decimal(h_m):
    try:
        h, m = map(int, h_m.split(':'))
        return h + m / 60.0
    except:
        return 0.0

# --- RELÓGIO COM FUSO BRASÍLIA ---
now_br = get_now_br()
st.markdown(f"<div class='clock-style'>🕒 {now_br.strftime('%d/%m/%Y - %H:%M')} (Brasília)</div>", unsafe_allow_html=True)



# --- BARRA LATERAL (LOGIN COM SECRETS) ---
with st.sidebar:
    st.markdown("<h2 class='header-style'>🔐 Acesso Restrito</h2>", unsafe_allow_html=True)
    
    if not st.session_state.logged_in:
        with st.container():
            user = st.text_input("Usuário")
            password = st.text_input("Senha", type="password")
            if st.button("Entrar"):
                try:
                    admin_user = st.secrets["credentials"]["admin_user"]
                    admin_password = st.secrets["credentials"]["admin_password"]
                    if user == admin_user and password == admin_password:
                        st.session_state.logged_in = True
                        st.success("Acesso Autorizado!")
                        time.sleep(1); st.rerun()
                    else:
                        st.error("Credenciais inválidas")
                except:
                    if hasattr(db, 'check_login'):
                        if db.check_login(user, password):
                            st.session_state.logged_in = True
                            st.success("Acesso Autorizado!")
                            time.sleep(1); st.rerun()
                        else:
                            st.error("Credenciais inválidas")
    else:
        st.write(f"Conectado como: **Gestor de Projeto**")
        if st.button("Sair"):
            st.session_state.logged_in = False
            st.rerun()

    st.markdown("---")
    st.info("Apenas gestores podem registrar apontamentos e gerenciar o efetivo.")

# --- CORPO PRINCIPAL ---
st.markdown("<h1 class='header-style'>🏗️ GRUPO SANTIN - Controle de Obras</h1>", unsafe_allow_html=True)

# Definição das Abas
if st.session_state.logged_in:
    tabs_list = ["📅 Efetivo Diário", "➕ Novo Colaborador", "✍️ Apontar Horas", "📊 Dash Efetivo", "📈 Dash Produtividade", "📖 Consulta Geral", "⏱️ Registros de Horas", "⚙️ Gestão de Funções", "🚜 Gestão de Equipamentos", "✏️ Atualizar Dados", "🗑️ Remover Registro"]
else:
    tabs_list = ["📅 Efetivo Diário", "📊 Dash Efetivo", "📈 Dash Produtividade", "📖 Consulta Geral", "⏱️ Registros de Horas"]

aba_view = st.tabs(tabs_list)

# --- LÓGICA DE EXIBIÇÃO ---

# ABA 0: EFETIVO DIÁRIO
with aba_view[0]:
    st.subheader("📅 Controle de Efetivo Diário")
    
    if st.session_state.logged_in:
        with st.expander("📤 Upload de Efetivo (Excel - Aba 'Efetivo')"):
            u_file = st.file_uploader("Selecione o arquivo Excel", type=['xlsx'])
            if u_file and st.button("Processar Arquivo"):
                try:
                    # Lê especificamente a aba 'Efetivo'
                    df_u = pd.read_excel(u_file, sheet_name='Efetivo')
                    
                    # Verifica se as colunas necessárias existem (sem acentos conforme solicitado)
                    cols_required = ['Data', 'Matricula', 'Nome', 'Funcao', 'Status', 'Situacao']
                    if all(c in df_u.columns for c in cols_required):
                        # Limpa dados das datas que estão sendo subidas para evitar duplicidade
                        datas_no_arquivo = df_u['Data'].unique()
                        for d in datas_no_arquivo:
                            db.delete_efetivo_por_data(d)
                        
                        if db.add_efetivo_diario_batch(df_u):
                            st.success("Efetivo carregado com sucesso!")
                            time.sleep(1); st.rerun()
                    else:
                        st.error(f"O arquivo deve conter as colunas: {', '.join(cols_required)}")
                except Exception as e:
                    st.error(f"Erro ao processar: {e}")

    # Visualização dos Dados
    dados_efetivo = db.get_efetivo_diario()
    if dados_efetivo:
        df_ef = pd.DataFrame(dados_efetivo, columns=["Data", "Matrícula", "Nome", "Função", "Status", "Situação"])
        df_ef['Data'] = pd.to_datetime(df_ef['Data'])
        
        # 1. Gráfico de Linhas (Histórico Status 1 - Presente)
        st.markdown("### 📈 Histórico de Efetivo (Presentes)")
        c1, c2 = st.columns(2)
        with c1: d_ini = st.date_input("Data Início", value=df_ef['Data'].min())
        with c2: d_fim = st.date_input("Data Fim", value=df_ef['Data'].max())
        
        df_hist = df_ef[(df_ef['Data'] >= pd.Timestamp(d_ini)) & (df_ef['Data'] <= pd.Timestamp(d_fim)) & (df_ef['Status'] == 1)]
        df_hist_count = df_hist.groupby('Data').size().reset_index(name='Quantidade')
        
        fig_hist = px.line(df_hist_count, x='Data', y='Quantidade', markers=True, 
                          title="Efetivo Presente ao Longo do Tempo", color_discrete_sequence=['#FFD700'],
                          text='Quantidade')
        fig_hist.update_traces(textposition="top center", textfont=dict(color="black", size=12))
        fig_hist.update_xaxes(
            type='date',
            tickformat='%d/%m/%Y',
            dtick="D1", # Força intervalo de 1 dia
            tickangle=-45
        )
        fig_hist.update_layout(margin=dict(b=100))
        st.plotly_chart(fig_hist, use_container_width=True)
        
        st.markdown("---")
        
        # 2. Gráfico de Barras Horizontais (Status do Dia - Outras Situações)
        st.markdown("### 📊 Status do Efetivo (Último Registro)")
        data_recente = df_ef['Data'].max()
        df_recente = df_ef[df_ef['Data'] == data_recente]
        
        # Filtrar apenas status que NÃO são 1 para o gráfico de barras horizontais
        df_status_dia = df_recente[df_recente['Status'] != 1].groupby('Situação').size().reset_index(name='Total')
        
        col_graf, col_tab = st.columns([1, 1])
        
        with col_graf:
            fig_status = px.bar(df_status_dia, y='Situação', x='Total', orientation='h', 
                               title=f"Distribuição de Situações - {data_recente.strftime('%d/%m/%Y')}",
                               color_discrete_sequence=['#000000'], text_auto=True)
            fig_status.update_layout(yaxis={'categoryorder':'total ascending'})
            sel_status = st.plotly_chart(fig_status, use_container_width=True, on_select="rerun")
        
        with col_tab:
            sit_filtrada = None
            if sel_status and "selection" in sel_status and "points" in sel_status["selection"] and sel_status["selection"]["points"]:
                sit_filtrada = sel_status["selection"]["points"][0]["y"]
                st.markdown(f"#### Detalhes: {sit_filtrada}")
                
                df_detalhe = df_recente[df_recente['Situação'] == sit_filtrada]
                
                # Para a hierarquia, precisamos da Abreviação do cadastro original
                dados_func = db.get_funcionarios()
                dict_abrev = {f[0]: f[3].upper() if f[3] else f[2].upper() for f in dados_func}
                df_detalhe['Abrev'] = df_detalhe['Matrícula'].map(dict_abrev).fillna(df_detalhe['Função'])
                
                abrevs = sorted(df_detalhe['Abrev'].unique())
                for a in abrevs:
                    with st.expander(f"🔸 {a}"):
                        nomes = df_detalhe[df_detalhe['Abrev'] == a]['Nome'].tolist()
                        for n in nomes:
                            st.write(f"- {n}")
            else:
                st.info("Clique em uma barra do gráfico ao lado para ver os nomes.")
    else:
        st.info("Nenhum dado de efetivo diário carregado.")
        

if st.session_state.logged_in:
    # 1: NOVO COLABORADOR
    with aba_view[1]:
        st.subheader("➕ Cadastro de Novo Colaborador")
        funcoes_disponiveis = db.get_funcoes()
        with st.form(key=f"form_novo_colab_{st.session_state.form_key}"):
            c1, c2 = st.columns(2)
            with c1:
                mat = st.text_input("Matrícula *")
                nome = st.text_input("Nome Completo *")
                func = st.selectbox("Função/Cargo *", funcoes_disponiveis)
            with c2:
                abrev = st.text_input("Abreviação")
                adm = st.date_input("Data de Admissão")
                mo = st.selectbox("Tipo de MO", ["MOD", "MOI"])
                status = st.selectbox("Status", ["Ativo", "Inativo"])
            if st.form_submit_button("Cadastrar Colaborador"):
                if mat.isdigit() and nome:
                    success, msg = db.add_funcionario(mat, nome, func, abrev, adm, mo, status)
                    if success:
                        st.success("Cadastrado!"); reset_form(); time.sleep(1); st.rerun()
                    else: st.error(f"Erro: {msg}")
                else: st.error("Verifique os campos obrigatórios (Matrícula deve ser numérica).")

    # 2: APONTAR HORAS
    with aba_view[2]:
        st.subheader("✍️ Novo Apontamento Diário")
        dados_func = db.get_funcionarios()
        mats = [d[0] for d in dados_func]
        equipamentos_disp = db.get_equipamentos()
        
        with st.form(key=f"form_apont_horas_{st.session_state.form_key}"):
            c1, c2, c3 = st.columns(3)
            with c1:
                sel_mat = st.selectbox("Matrícula Colaborador *", [""] + mats)
                func_info = next((f for f in dados_func if f[0] == sel_mat), None)
                nome_auto = func_info[1] if func_info else ""
                funcao_auto = func_info[2] if func_info else ""
                st.text_input("Nome", value=nome_auto, disabled=True)
                st.text_input("Função", value=funcao_auto, disabled=True)
                data_ap = st.date_input("Data do Apontamento", value=datetime.now().date())
            
            with c2:
                equip = st.selectbox("Equipamento Utilizado *", [""] + equipamentos_disp)
                ativ = st.text_area("Descrição da Atividade")
            
            with c3:
                ent = st.time_input("Início Jornada", value=datetime.strptime("07:00", "%H:%M").time())
                s_alm = st.time_input("Saída Intervalo", value=datetime.strptime("12:00", "%H:%M").time())
                r_alm = st.time_input("Retorno Intervalo", value=datetime.strptime("13:00", "%H:%M").time())
                s_fin = st.time_input("Fim Jornada", value=datetime.strptime("17:00", "%H:%M").time())
                total_h = calcular_horas(ent, s_alm, r_alm, s_fin)
                st.info(f"Horas Trabalhadas: **{total_h}**")

            if st.form_submit_button("Registrar em Obra"):
                if sel_mat and equip and ativ:
                    db.add_apontamento(sel_mat, nome_auto, funcao_auto, equip, ativ, ent, s_alm, r_alm, s_fin, total_h, data_ap)
                    st.success("Registrado com sucesso!")
                    reset_form(); time.sleep(1); st.rerun()
                else: st.warning("Preencha os campos obrigatórios.")
    
    idx_offset = 3
else:
    idx_offset = 1

# DASHBOARD EFETIVO
with aba_view[0 + idx_offset]:
    dados = db.get_funcionarios()
    if dados:
        df = pd.DataFrame(dados, columns=["Matrícula", "Nome", "Função", "Abrev.", "Admissão", "MO", "Status"])
        m1, m2, m3 = st.columns(3)
        with m1: st.markdown(f"<div class='metric-card'><h3>Total Efetivo</h3><h2>{len(df)}</h2></div>", unsafe_allow_html=True)
        with m2: st.markdown(f"<div class='metric-card'><h3>Ativos na Obra</h3><h2 style='color: green;'>{len(df[df['Status'] == 'Ativo'])}</h2></div>", unsafe_allow_html=True)
        with m3: st.markdown(f"<div class='metric-card'><h3>Inativos/Desligados</h3><h2 style='color: red;'>{len(df[df['Status'] == 'Inativo'])}</h2></div>", unsafe_allow_html=True)
        
        df['Abrev_Upper'] = df['Abrev.'].str.upper()
        counts = df['Abrev_Upper'].value_counts().reset_index()
        counts.columns = ['Função', 'Quantidade']
        fig = px.bar(counts, x='Função', y='Quantidade', title="Efetivo por Função (Agrupado por Abreviação)", color_discrete_sequence=['#FFD700'], text_auto=True)
        fig.update_layout(
            plot_bgcolor='white',
            xaxis=dict(tickangle=-45, automargin=True, tickfont=dict(size=12)),
            margin=dict(l=50, r=50, b=120, t=50)
        )
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("Nenhum colaborador cadastrado ainda.")

# DASHBOARD PRODUTIVIDADE
with aba_view[1 + idx_offset]:
    st.subheader("📈 Análise de Produtividade (Horas)")
    aponts = db.get_apontamentos()
    if aponts:
        df_ap = pd.DataFrame(aponts, columns=["Matrícula", "Nome", "Função", "Equipamento", "Atividade", "Entrada", "S. Almoço", "R. Almoço", "Saída", "Total", "Data"])
        df_ap['Data'] = pd.to_datetime(df_ap['Data'])
        df_ap['Horas_Dec'] = df_ap['Total'].apply(horas_para_decimal)
        df_ap['Mes_Ano'] = df_ap['Data'].dt.strftime('%m/%Y')
        
        meses_disp = sorted(df_ap['Mes_Ano'].unique(), reverse=True)
        mes_sel = st.selectbox("Filtrar Mês de Referência", meses_disp)
        
        df_filtrado = df_ap[df_ap['Mes_Ano'] == mes_sel].sort_values('Data')
        
        df_dia = df_filtrado.groupby('Data')['Horas_Dec'].sum().reset_index()
        fig_dia = go.Figure()
        fig_dia.add_trace(go.Scatter(
            x=df_dia['Data'], y=df_dia['Horas_Dec'], mode='lines+markers+text',
            line_shape='spline', text=[f"{h:.1f}h" for h in df_dia['Horas_Dec']],
            textposition="top center", 
            textfont=dict(color="black", size=12),
            marker=dict(size=10, color='#000000'),
            line=dict(width=3, color='#FFD700'), name="Horas"
        ))
        fig_dia.update_layout(
            title=f"Horas por Dia - {mes_sel}", 
            xaxis=dict(
                type='date',
                tickformat="%d/%m/%Y",
                dtick="D1" # Força intervalo de 1 dia para não mostrar horas
            ), 
            template="plotly_white"
        )
        st.plotly_chart(fig_dia, use_container_width=True)
        
        st.markdown("---")
        st.markdown("### 🔍 Detalhamento Interativo")
        
        dados_func = db.get_funcionarios()
        dict_abrev = {f[0]: f[3].upper() if f[3] else f[2].upper() for f in dados_func}
        df_filtrado['Abrev'] = df_filtrado['Matrícula'].map(dict_abrev)
        
        df_f = df_filtrado.groupby('Abrev')['Horas_Dec'].sum().reset_index()
        df_f.columns = ['Função', 'Horas_Dec']
        fig_func = px.bar(df_f, x='Função', y='Horas_Dec', title="Horas por Função (Agrupado por Abreviação - Clique para filtrar)", 
                         color_discrete_sequence=['#FFD700'], text_auto='.1f')
        fig_func.update_layout(
            clickmode='event+select',
            xaxis=dict(tickangle=-45, automargin=True, tickfont=dict(size=12)),
            margin=dict(l=50, r=50, b=120, t=50)
        )
        
        selected_points = st.plotly_chart(fig_func, use_container_width=True, on_select="rerun")
        
        filtro_func = None
        if selected_points and "selection" in selected_points and "points" in selected_points["selection"] and selected_points["selection"]["points"]:
            filtro_func = selected_points["selection"]["points"][0]["x"]
            st.info(f"Filtrando por Função: **{filtro_func}**")
        
        if filtro_func:
            df_e_data = df_filtrado[df_filtrado['Abrev'] == filtro_func]
            titulo_e = f"Horas por Equipamento - Função: {filtro_func}"
        else:
            df_e_data = df_filtrado
            titulo_e = "Horas por Equipamento (Geral)"
            
        df_e = df_e_data.groupby('Equipamento')['Horas_Dec'].sum().reset_index()
        fig_equip = px.bar(df_e, x='Equipamento', y='Horas_Dec', title=titulo_e, 
                          color_discrete_sequence=['#000000'], text_auto='.1f')
        fig_equip.update_layout(
            xaxis=dict(tickangle=-45, automargin=True, tickfont=dict(size=12)),
            margin=dict(l=50, r=50, b=120, t=50)
        )
        st.plotly_chart(fig_equip, use_container_width=True)
        
        if filtro_func:
            if st.button("Limpar Filtro"): st.rerun()
    else:
        st.info("Sem dados de produtividade registrados.")

# CONSULTA GERAL
with aba_view[2 + idx_offset]:
    st.subheader("📖 Consulta de Efetivo")
    dados = db.get_funcionarios()
    if dados:
        df = pd.DataFrame(dados, columns=["Matrícula", "Nome", "Função", "Abrev.", "Admissão", "MO", "Status"])
        df_up = df.applymap(lambda x: str(x).upper() if pd.notnull(x) else x)
        buffer = BytesIO()
        with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
            df_up.to_excel(writer, index=False)
        st.download_button("⬇️ Exportar Excel", data=buffer.getvalue(), file_name="Efetivo_Santin.xlsx")
        st.dataframe(df_up, use_container_width=True)

# REGISTROS DE HORAS
with aba_view[3 + idx_offset]:
    st.subheader("⏱️ Histórico de Apontamentos")
    aponts_raw = db.get_apontamentos_com_id()
    if aponts_raw:
        df_ap_full = pd.DataFrame(aponts_raw, columns=["ID", "Matrícula", "Nome", "Função", "Equipamento", "Atividade", "Entrada", "S. Almoço", "R. Almoço", "Saída", "Total", "Data"])
        d_f = st.date_input("Filtrar Data", value=None, key="filtro_data_hist")
        df_display = df_ap_full.copy()
        if d_f: df_display = df_display[df_display['Data'] == str(d_f)]
        st.dataframe(df_display.tail(20).applymap(lambda x: str(x).upper() if pd.notnull(x) else x), use_container_width=True)
        
        if st.session_state.logged_in:
            with st.expander("🗑️ Excluir Apontamentos"):
                opcoes_excluir = [f"ID: {row['ID']} | {row['Data']} | {row['Nome']} | {row['Total']}h" for _, row in df_display.iterrows()]
                sel_excluir = st.multiselect("Selecione os registros", opcoes_excluir)
                if st.button("Excluir Selecionados"):
                    if sel_excluir:
                        for s in sel_excluir:
                            db.delete_apontamento_por_id(int(s.split('|')[0].replace('ID: ', '').strip()))
                        st.success("Excluído!"); time.sleep(1); st.rerun()
    else:
        st.info("Nenhum apontamento registrado.")

# ABAS EXCLUSIVAS ADMIN
if st.session_state.logged_in:
    with aba_view[7]: # GESTÃO FUNÇÕES
        st.subheader("⚙️ Gestão de Funções")
        c1, c2 = st.columns([2, 1])
        funcoes = db.get_funcoes()
        with c1: st.table(pd.DataFrame([f.upper() for f in funcoes], columns=["Função"]))
        with c2:
            n_f = st.text_input("Nova Função")
            if st.button("Salvar Função"):
                if db.add_funcao(n_f): st.success("Salvo!"); st.rerun()
            f_del = st.selectbox("Remover", [""] + funcoes)
            if st.button("Excluir Função"):
                if f_del: db.delete_funcao(f_del); st.success("Removido!"); time.sleep(1); st.rerun()

    with aba_view[8]: # GESTÃO EQUIPAMENTOS
        st.subheader("🚜 Gestão de Equipamentos")
        c1, c2 = st.columns([2, 1])
        equips = db.get_equipamentos()
        with c1: st.table(pd.DataFrame([e.upper() for e in equips], columns=["Equipamento"]))
        with c2:
            n_e = st.text_input("Novo Equipamento")
            if st.button("Salvar Equipamento"):
                if db.add_equipamento(n_e): st.success("Salvo!"); st.rerun()
            e_del = st.selectbox("Remover", [""] + equips)
            if st.button("Excluir Equipamento"):
                if e_del: db.delete_equipamento(e_del); st.success("Removido!"); time.sleep(1); st.rerun()

    with aba_view[9]: # ATUALIZAR
        st.subheader("✏️ Atualizar Cadastro")
        dados = db.get_funcionarios()
        mats = [d[0] for d in dados]
        if mats:
            s_m = st.selectbox("Matrícula", mats)
            f_d = next((f for f in dados if f[0] == s_m), None)
            if f_d:
                with st.form(key=f"form_upd_{st.session_state.form_key}"):
                    u_n = st.text_input("Nome", value=f_d[1])
                    u_f = st.selectbox("Função", db.get_funcoes(), index=db.get_funcoes().index(f_d[2]) if f_d[2] in db.get_funcoes() else 0)
                    u_a = st.text_input("Abreviação", value=f_d[3])
                    u_d = st.date_input("Admissão", value=datetime.strptime(f_d[4], '%Y-%m-%d').date() if f_d[4] else datetime.now().date())
                    u_mo = st.selectbox("MO", ["MOD", "MOI"], index=0 if f_d[5] == "MOD" else 1)
                    u_st = st.selectbox("Status", ["Ativo", "Inativo"], index=0 if f_d[6] == "Ativo" else 1)
                    if st.form_submit_button("Salvar"):
                        if db.update_funcionario(s_m, u_n, u_f, u_a, u_d, u_mo, u_st):
                            st.success("Atualizado!"); time.sleep(1); st.rerun()

    with aba_view[10]: # REMOVER
        st.subheader("🗑️ Remover Colaborador")
        mats = [d[0] for d in db.get_funcionarios()]
        if mats:
            d_m = st.selectbox("Excluir Matrícula", mats)
            if st.button("Confirmar Exclusão"):
                if db.delete_funcionario(d_m): st.success("Removido!"); time.sleep(1); st.rerun()
