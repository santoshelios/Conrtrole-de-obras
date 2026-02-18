import streamlit as st
import pandas as pd
import time
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
from io import BytesIO
import pytz
import requests


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
    
    /* Botão de Download Excel Estilizado */
    .download-excel-btn {
        display: inline-block;
        padding: 10px 20px;
        background: linear-gradient(135deg, #1e7e34 0%, #28a745 100%);
        color: white;
        text-decoration: none;
        border-radius: 8px;
        font-weight: bold;
        font-size: 14px;
        box-shadow: 0 4px 12px rgba(40, 167, 69, 0.3);
        transition: all 0.3s ease;
        border: 2px solid #1e7e34;
        text-align: center;
        cursor: pointer;
    }
    .download-excel-btn:hover {
        background: linear-gradient(135deg, #155724 0%, #1e7e34 100%);
        box-shadow: 0 6px 16px rgba(40, 167, 69, 0.5);
        transform: translateY(-2px);
    }
    .download-excel-btn:active {
        transform: translateY(0px);
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
if 'user_name' not in st.session_state:
    st.session_state.user_name = "Visitante"
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
        time.sleep(3.5)
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

def converter_df_para_excel(df):
    """Converte um DataFrame para formato Excel em memória"""
    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Consulta_Efetivo')
    output.seek(0)
    return output


# --- PLUVIOMETRIA CEMADEN + INMET ---


def get_cemaden_barueri(data_ref):
    try:
        import socket
        debug_info = {}

        # 🔎 Teste DNS
        try:
            ip = socket.gethostbyname("dadosabertos.cemaden.gov.br")
            debug_info["DNS_RESOLVIDO_IP"] = ip
        except Exception as dns_err:
            debug_info["DNS_ERRO"] = str(dns_err)
            st.error(f"❌ ERRO DNS: {dns_err}")
            return {h: 0.0 for h in range(24)}

        url = "https://dadosabertos.cemaden.gov.br/api/3/action/datastore_search"
        params = {
            "resource_id": "c6f4b9b6-3c77-4c6d-bd36-5e3b1a0f2f94",
            "limit": 5000
        }

        r = requests.get(url, params=params, timeout=20)
        debug_info["STATUS_CODE"] = r.status_code

        if r.status_code != 200:
            st.error(f"❌ ERRO HTTP CEMADEN: {r.status_code}")
            return {h: 0.0 for h in range(24)}

        data_json = r.json()
        records = data_json["result"]["records"]

        if not records:
            st.warning("⚠️ CEMADEN respondeu mas não retornou registros.")
            return {h: 0.0 for h in range(24)}

        df = pd.DataFrame(records)

        st.info(f"🔍 DEBUG: {len(df)} registros recebidos da API.")
        st.write("Colunas disponíveis:", list(df.columns))

        # 🔥 Filtrar pela estação 7033 se existir coluna
        possible_cols = [c for c in df.columns if "estacao" in c.lower()]
        if possible_cols:
            col_est = possible_cols[0]
            df = df[df[col_est].astype(str) == "7033"]

        if df.empty:
            st.warning("⚠️ Nenhum registro da estação 7033 encontrado no lote retornado.")
            return {h: 0.0 for h in range(24)}

        df["datahora"] = pd.to_datetime(df["datahora"], errors="coerce")
        df = df[df["datahora"].dt.date == data_ref]

        if df.empty:
            st.warning("⚠️ A estação respondeu, mas não há dados para a data selecionada.")
            return {h: 0.0 for h in range(24)}

        horas = {h: 0.0 for h in range(24)}

        col_acum = next((c for c in df.columns if "acumul" in c.lower()), None)

        if col_acum:
            df = df.sort_values("datahora")
            df["hora"] = df["datahora"].dt.hour
            df["chuva"] = df[col_acum].diff().fillna(df[col_acum])

            for _, row in df.iterrows():
                hora = int(row["hora"])
                valor = max(float(row["chuva"]), 0)
                horas[hora] += valor

        return horas

    except Exception as e:
        st.error(f"❌ ERRO CEMADEN: {e}")
        return {h: 0.0 for h in range(24)}
def get_pluviometria_cruzada(data_ref):
    # 🔥 Agora usa apenas CEMADEN estação 7033
    horas = get_cemaden_barueri(data_ref)

    # Se não houver dados, retorna zeros
    if not horas:
        return {h: 0.0 for h in range(24)}

    return horas





# --- RELÓGIO COM FUSO BRASÍLIA ---
now_br = get_now_br()
st.markdown(f"<div class='clock-style'>🕒 {now_br.strftime('%d/%m/%Y - %H:%M')} (Brasília)</div>", unsafe_allow_html=True)

# --- BARRA LATERAL ---
with st.sidebar:
    st.markdown("<h2 style='text-align: center;'>🔐 ACESSO</h2>", unsafe_allow_html=True)
    
    if not st.session_state.logged_in:
        user = st.text_input("Usuário", placeholder="Digite seu usuário")
        password = st.text_input("Senha", type="password", placeholder="Digite sua senha")
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("ENTRAR NO SISTEMA"):
            try:
                admin_user = st.secrets["credentials"]["admin_user"]
                admin_password = st.secrets["credentials"]["admin_password"]
                if user == admin_user and password == admin_password:
                    st.session_state.logged_in = True
                    st.session_state.user_name = user
                    st.success("Bem-vindo!")
                    time.sleep(1); st.rerun()
                else:
                    if db.check_login(user, password):
                        st.session_state.logged_in = True
                        st.session_state.user_name = user
                        st.success("Bem-vindo!")
                        time.sleep(1); st.rerun()
                    else:
                        st.error("Acesso negado")
            except:
                if db.check_login(user, password):
                    st.session_state.logged_in = True
                    st.session_state.user_name = user
                    st.success("Bem-vindo!")
                    time.sleep(1); st.rerun()
                else:
                    st.error("Acesso negado")
    else:
        st.markdown(f"<div style='text-align: center; padding: 10px; background: #f0f2f6; border-radius: 10px;'>Usuário Ativo:<br><b>{st.session_state.user_name}</b></div>", unsafe_allow_html=True)
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("SAIR DO SISTEMA"):
            st.session_state.logged_in = False
            st.session_state.user_name = "Visitante"
            st.rerun()

    st.markdown("---")
    st.info("Sistema de Gestão de Obras v2.0")

# --- CORPO PRINCIPAL ---
st.markdown("<h1 class='header-style'>🏗️ GRUPO SANTIN - Controle de Obras</h1>", unsafe_allow_html=True)

# Definição das Abas (ORDEM CORRETA)
if st.session_state.logged_in:
    tabs_list = ["📅 Efetivo Diário", "➕ Novo Colaborador", "✍️ Apontar Horas", "📊 Dash Efetivo", "📈 Dash Produtividade", "📖 Consulta Geral", "⏱️ Registros de Horas", "⚙️ Gestão de Funções", "🚜 Gestão de Equipamentos", "✏️ Atualizar Dados", "🗑️ Remover Registro", "👥 Gestão de Usuários", "🔍 Auditoria", "🌧️ Pluviometria"]
else:
    tabs_list = ["📅 Efetivo Diário", "📊 Dash Efetivo", "📈 Dash Produtividade", "📖 Consulta Geral", "⏱️ Registros de Horas", "🌧️ Pluviometria"]

aba_view = st.tabs(tabs_list)

# --- ABA 0: EFETIVO DIÁRIO ---
with aba_view[0]:
    st.subheader("📅 Controle de Efetivo Diário")
    
    if st.session_state.logged_in:
        with st.expander("📤 Upload de Efetivo (Excel - Aba 'Efetivo')"):
            u_file = st.file_uploader("Selecione o arquivo Excel", type=['xlsx'])
            if u_file and st.button("Processar Arquivo"):
                try:
                    df_u = pd.read_excel(u_file, sheet_name='Efetivo')
                    cols_required = ['Data', 'Matricula', 'Nome', 'Funcao', 'Status', 'Situacao']
                    if all(c in df_u.columns for c in cols_required):
                        datas_no_arquivo = df_u['Data'].unique()
                        for d in datas_no_arquivo:
                            db.delete_efetivo_por_data(d, st.session_state.user_name)
                        if db.add_efetivo_diario_batch(df_u, st.session_state.user_name):
                            st.success("Efetivo carregado com sucesso!")
                            time.sleep(1); st.rerun()
                    else:
                        st.error(f"Colunas necessárias: {', '.join(cols_required)}")
                except Exception as e:
                    st.error(f"Erro: {e}")

    dados_efetivo = db.get_efetivo_diario()
    if dados_efetivo and len(dados_efetivo) > 0:
        # Colunas do Supabase: data, matricula, nome, funcao, status_val, situacao
        df_ef = pd.DataFrame(dados_efetivo, columns=["Data", "Matricula", "Nome", "Funcao", "Status_Val", "Situacao"])
        df_ef['Data'] = pd.to_datetime(df_ef['Data']).dt.date
        
        st.markdown("#### 🔍 Filtros de Visualização")
        f1, f2, f3 = st.columns(3)
        hoje = get_now_br().date()
        primeiro_dia_mes = hoje.replace(day=1)
        
        with f1: d_ini = st.date_input("Data Início", value=primeiro_dia_mes)
        with f2: d_fim = st.date_input("Data Fim", value=hoje)
        with f3: 
            situacoes_disp = ["TODAS"] + sorted(df_ef['Situacao'].unique().tolist())
            sit_filtro = st.selectbox("Filtrar Situação", situacoes_disp)
        
        # Gráfico de Histórico (Status_Val == 1)
        df_hist = df_ef[(df_ef['Data'] >= d_ini) & (df_ef['Data'] <= d_fim) & (df_ef['Status_Val'] == 1)]
        if not df_hist.empty:
            df_hist_count = df_hist.groupby('Data').size().reset_index(name='Quantidade')

            # Criar intervalo completo de datas
            intervalo_datas = pd.date_range(start=d_ini, end=d_fim)
            df_full = pd.DataFrame({'Data': intervalo_datas})
            df_hist_count['Data'] = pd.to_datetime(df_hist_count['Data'])
            df_full = df_full.merge(df_hist_count, on='Data', how='left').fillna(0)
            df_full['Quantidade'] = df_full['Quantidade'].astype(int)

            fig_hist = px.line(
                df_full,
                x='Data',
                y='Quantidade',
                title="Evolução do Efetivo Presente",
                markers=True,
                line_shape='linear',
                text='Quantidade'
            )

            fig_hist.update_traces(
                marker=dict(size=7, color='black'),
                line=dict(width=3),
                textposition="top center"
            )

            fig_hist.update_layout(
                template="plotly_white",
                xaxis=dict(tickformat="%d/%m/%Y"),
                hovermode="x unified",
                yaxis=dict(range=[0, df_full['Quantidade'].max() + 2])
            )

            st.plotly_chart(fig_hist, width='stretch')
        
        st.markdown("---")
        st.markdown("### 📋 Status do Dia")
        
        data_recente = df_ef['Data'].max()
        df_recente = df_ef[df_ef['Data'] == data_recente]
        
        if sit_filtro != "TODAS":
            df_recente = df_recente[df_recente['Situacao'] == sit_filtro]
        
        if not df_recente.empty:
            df_status_dia = df_recente.groupby('Situacao').size().reset_index(name='Total')
            col_graf, col_tab = st.columns([1, 1])
            with col_graf:
                fig_status = px.bar(df_status_dia, y='Situacao', x='Total', orientation='h', 
                                   title=f"Distribuição Status - {data_recente.strftime('%d/%m/%Y')}", 
                                   color_discrete_sequence=['#000000'], text_auto=True)
                fig_status.update_layout(yaxis={'categoryorder':'total ascending'}, template="plotly_white")
                sel_status = st.plotly_chart(fig_status, width='stretch', on_select="rerun")
            with col_tab:
                if sel_status and "selection" in sel_status and "points" in sel_status["selection"] and sel_status["selection"]["points"]:
                    sit_filtrada = sel_status["selection"]["points"][0]["y"]
                    st.markdown(f"#### Detalhes: {sit_filtrada}")
                    df_detalhe = df_recente[df_recente['Situacao'] == sit_filtrada]
                    
                    # Busca abreviações do cadastro de funcionários
                    dados_func = db.get_funcionarios()
                    dict_abrev = {str(f[0]): (f[3].upper() if f[3] else f[2].upper()) for f in dados_func}
                    
                    df_detalhe['Abrev'] = df_detalhe['Matricula'].astype(str).map(dict_abrev).fillna(df_detalhe['Funcao'])
                    
                    for a in sorted(df_detalhe['Abrev'].unique()):
                        with st.expander(f"🔸 {a}"):
                            for n in df_detalhe[df_detalhe['Abrev'] == a]['Nome'].tolist():
                                st.write(f"- {n}")
                else:
                    st.info("Clique sobre o status para visualizar o efetivo.")
        else:
            st.warning(f"Nenhum dado encontrado para a data {data_recente.strftime('%d/%m/%Y')} com o filtro selecionado.")
    else:
        st.info("Nenhum dado de efetivo diário carregado no banco de dados.")

# --- ABA 1: DASH EFETIVO (PÚBLICO) / NOVO COLABORADOR (LOGADO) ---
if st.session_state.logged_in:
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
            if st.form_submit_button("CADASTRAR COLABORADOR"):
                if mat.isdigit() and nome:
                    success, msg = db.add_funcionario(mat, nome, func, abrev, adm, mo, status, st.session_state.user_name)
                    if success: st.success("Cadastrado!"); reset_form(); time.sleep(1); st.rerun()
                    else: st.error(f"Erro: {msg}")
                else: st.error("Preencha os campos obrigatórios.")
else:
    with aba_view[1]:
        st.subheader("📊 Dashboard de Efetivo")
        dados = db.get_funcionarios()
        if dados:
            df = pd.DataFrame(dados, columns=["Matrícula", "Nome", "Função", "Abrev.", "Admissão", "MO", "Status"])
            m1, m2, m3 = st.columns(3)
            with m1: st.markdown(f"<div class='metric-card'><h3>Total Efetivo</h3><h2>{len(df)}</h2></div>", unsafe_allow_html=True)
            with m2: st.markdown(f"<div class='metric-card'><h3>Ativos na Obra</h3><h2 style='color: green;'>{len(df[df['Status'] == 'Ativo'])}</h2></div>", unsafe_allow_html=True)
            with m3: st.markdown(f"<div class='metric-card'><h3>Inativos</h3><h2 style='color: red;'>{len(df[df['Status'] == 'Inativo'])}</h2></div>", unsafe_allow_html=True)
            # FILTRA APENAS COLABORADORES ATIVOS PARA O GRÁFICO
            df_ativos = df[df['Status'] == 'Ativo'].copy()
            df_ativos['Abrev_Upper'] = df_ativos['Abrev.'].str.upper()

            counts = df_ativos['Abrev_Upper'].value_counts().reset_index()
            counts.columns = ['Função', 'Quantidade']

            fig = px.bar(
                counts,
                x='Função',
                y='Quantidade',
                title="Efetivo por Função (Somente Ativos)",
                color_discrete_sequence=['#FFD700'],
                text_auto=True
            )

            fig.update_layout(
                xaxis=dict(tickangle=-45, automargin=True),
                margin=dict(b=120),
                template="plotly_white"
            )

            st.plotly_chart(fig, width='stretch')

# --- ABA 2: APONTAR HORAS (LOGADO) / DASH PRODUTIVIDADE (PÚBLICO) ---
if st.session_state.logged_in:
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
                data_ap = st.date_input("Data do Apontamento", value=get_now_br().date())
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
            if st.form_submit_button("REGISTRAR EM OBRA"):
                if sel_mat and equip and ativ:
                    db.add_apontamento(sel_mat, nome_auto, funcao_auto, equip, ativ, ent, s_alm, r_alm, s_fin, total_h, data_ap, st.session_state.user_name)
                    st.success("Registrado!"); reset_form(); time.sleep(1); st.rerun()
                else: st.warning("Preencha os campos obrigatórios.")
else:
    with aba_view[2]:
        st.subheader("📈 Dashboard de Produtividade")
        aponts = db.get_apontamentos()
        if aponts:
            df_ap = pd.DataFrame(aponts, columns=["Matrícula", "Nome", "Função", "Equipamento", "Atividade", "Entrada", "S. Almoço", "R. Almoço", "Saída", "Total", "Data"])
            df_ap['Data'] = pd.to_datetime(df_ap['Data'])
            df_ap['Horas_Dec'] = df_ap['Total'].apply(horas_para_decimal)
            df_ap['Mes_Ano'] = df_ap['Data'].dt.strftime('%m/%Y')
            meses_disp = sorted(df_ap['Mes_Ano'].unique(), reverse=True)
            mes_sel = st.selectbox("Mês de Referência", meses_disp)
            df_filtrado = df_ap[df_ap['Mes_Ano'] == mes_sel].sort_values('Data')
            if not df_filtrado.empty:
                df_dia = df_filtrado.groupby('Data')['Horas_Dec'].sum().reset_index()
                fig_dia = go.Figure()
                fig_dia.add_trace(go.Scatter(x=df_dia['Data'], y=df_dia['Horas_Dec'], mode='lines+markers+text', text=[f"{h:.1f}h" for h in df_dia['Horas_Dec']], textposition="top center", textfont=dict(color="black"), marker=dict(size=10, color='#000000'), line=dict(width=3, color='#FFD700')))
                fig_dia.update_layout(title=f"Horas por Dia - {mes_sel}", xaxis=dict(type='date', tickformat="%d/%m/%Y", dtick="D1", tickangle=-45), template="plotly_white")
                st.plotly_chart(fig_dia, width='stretch')
                st.markdown("---")
                dados_func = db.get_funcionarios()
                dict_abrev = {f[0]: f[3].upper() if f[3] else f[2].upper() for f in dados_func}
                df_filtrado['Abrev'] = df_filtrado['Matrícula'].map(dict_abrev).fillna(df_filtrado['Função'])
                df_f = df_filtrado.groupby('Abrev')['Horas_Dec'].sum().reset_index()
                fig_func = px.bar(df_f, x='Abrev', y='Horas_Dec', title="Horas por Função (Clique para filtrar)", color_discrete_sequence=['#FFD700'], text_auto='.1f')
                fig_func.update_layout(xaxis=dict(tickangle=-45, automargin=True), margin=dict(b=120), template="plotly_white")
                selected_points = st.plotly_chart(fig_func, width='stretch', on_select="rerun")
                filtro_func = selected_points["selection"]["points"][0]["x"] if selected_points and "selection" in selected_points and selected_points["selection"]["points"] else None
                df_e_data = df_filtrado[df_filtrado['Abrev'] == filtro_func] if filtro_func else df_filtrado
                df_e = df_e_data.groupby('Equipamento')['Horas_Dec'].sum().reset_index()
                fig_equip = px.bar(df_e, x='Equipamento', y='Horas_Dec', title=f"Horas por Equipamento {'- '+filtro_func if filtro_func else ''}", color_discrete_sequence=['#000000'], text_auto='.1f')
                fig_equip.update_layout(xaxis=dict(tickangle=-45, automargin=True), margin=dict(b=120), template="plotly_white")
                st.plotly_chart(fig_equip, width='stretch')
                if filtro_func and st.button("Limpar Filtro"): st.rerun()

# --- ABA 3: DASH EFETIVO (LOGADO) / CONSULTA GERAL (PÚBLICO) ---
if st.session_state.logged_in:
    with aba_view[3]:
        st.subheader("📊 Dashboard de Efetivo")
        dados = db.get_funcionarios()
        if dados:
            df = pd.DataFrame(dados, columns=["Matrícula", "Nome", "Função", "Abrev.", "Admissão", "MO", "Status"])
            m1, m2, m3 = st.columns(3)
            with m1: st.markdown(f"<div class='metric-card'><h3>Total Efetivo</h3><h2>{len(df)}</h2></div>", unsafe_allow_html=True)
            with m2: st.markdown(f"<div class='metric-card'><h3>Ativos na Obra</h3><h2 style='color: green;'>{len(df[df['Status'] == 'Ativo'])}</h2></div>", unsafe_allow_html=True)
            with m3: st.markdown(f"<div class='metric-card'><h3>Inativos</h3><h2 style='color: red;'>{len(df[df['Status'] == 'Inativo'])}</h2></div>", unsafe_allow_html=True)
            # FILTRA APENAS COLABORADORES ATIVOS PARA O GRÁFICO
            df_ativos = df[df['Status'] == 'Ativo'].copy()
            df_ativos['Abrev_Upper'] = df_ativos['Abrev.'].str.upper()

            counts = df_ativos['Abrev_Upper'].value_counts().reset_index()
            counts.columns = ['Função', 'Quantidade']

            fig = px.bar(
                counts,
                x='Função',
                y='Quantidade',
                title="Efetivo por Função (Somente Ativos)",
                color_discrete_sequence=['#FFD700'],
                text_auto=True
            )

            fig.update_layout(
                xaxis=dict(tickangle=-45, automargin=True),
                margin=dict(b=120),
                template="plotly_white"
            )

            st.plotly_chart(fig, width='stretch')
else:
    with aba_view[3]:
        st.subheader("📖 Consulta de Efetivo")
        dados = db.get_funcionarios()
        if dados:
            df = pd.DataFrame(dados, columns=["Matrícula", "Nome", "Função", "Abrev.", "Admissão", "MO", "Status"])

            # 🔎 Filtros de Busca
            st.markdown("### 🔎 Filtros de Busca")

            col_f1, col_f2, col_f3 = st.columns(3)

            with col_f1:
                filtro_nome = st.text_input("Buscar por Nome")

            with col_f2:
                filtro_matricula = st.text_input("Buscar por Matrícula")

            with col_f3:
                filtro_funcao = st.text_input("Buscar por Função")

            df_filtrado = df.copy()

            if filtro_nome:
                df_filtrado = df_filtrado[df_filtrado["Nome"].str.contains(filtro_nome, case=False, na=False)]

            if filtro_matricula:
                df_filtrado = df_filtrado[df_filtrado["Matrícula"].astype(str).str.contains(filtro_matricula, case=False, na=False)]

            if filtro_funcao:
                df_filtrado = df_filtrado[df_filtrado["Função"].str.contains(filtro_funcao, case=False, na=False)]

            st.markdown("---")

            st.dataframe(
                df_filtrado.map(lambda x: str(x).upper() if pd.notnull(x) else x),
                width='stretch'
            )

# --- ABA 4: DASH PRODUTIVIDADE (LOGADO) / REGISTROS DE HORAS (PÚBLICO) ---
if st.session_state.logged_in:
    with aba_view[4]:
        st.subheader("📈 Dashboard de Produtividade")
        aponts = db.get_apontamentos()
        if aponts:
            df_ap = pd.DataFrame(aponts, columns=["Matrícula", "Nome", "Função", "Equipamento", "Atividade", "Entrada", "S. Almoço", "R. Almoço", "Saída", "Total", "Data"])
            df_ap['Data'] = pd.to_datetime(df_ap['Data'])
            df_ap['Horas_Dec'] = df_ap['Total'].apply(horas_para_decimal)
            df_ap['Mes_Ano'] = df_ap['Data'].dt.strftime('%m/%Y')
            meses_disp = sorted(df_ap['Mes_Ano'].unique(), reverse=True)
            mes_sel = st.selectbox("Mês de Referência", meses_disp)
            df_filtrado = df_ap[df_ap['Mes_Ano'] == mes_sel].sort_values('Data')
            if not df_filtrado.empty:
                df_dia = df_filtrado.groupby('Data')['Horas_Dec'].sum().reset_index()
                fig_dia = go.Figure()
                fig_dia.add_trace(go.Scatter(x=df_dia['Data'], y=df_dia['Horas_Dec'], mode='lines+markers+text', text=[f"{h:.1f}h" for h in df_dia['Horas_Dec']], textposition="top center", textfont=dict(color="black"), marker=dict(size=10, color='#000000'), line=dict(width=3, color='#FFD700')))
                fig_dia.update_layout(title=f"Horas por Dia - {mes_sel}", xaxis=dict(type='date', tickformat="%d/%m/%Y", dtick="D1", tickangle=-45), template="plotly_white")
                st.plotly_chart(fig_dia, width='stretch')
                st.markdown("---")
                dados_func = db.get_funcionarios()
                dict_abrev = {f[0]: f[3].upper() if f[3] else f[2].upper() for f in dados_func}
                df_filtrado['Abrev'] = df_filtrado['Matrícula'].map(dict_abrev).fillna(df_filtrado['Função'])
                df_f = df_filtrado.groupby('Abrev')['Horas_Dec'].sum().reset_index()
                fig_func = px.bar(df_f, x='Abrev', y='Horas_Dec', title="Horas por Função (Clique para filtrar)", color_discrete_sequence=['#FFD700'], text_auto='.1f')
                fig_func.update_layout(xaxis=dict(tickangle=-45, automargin=True), margin=dict(b=120), template="plotly_white")
                selected_points = st.plotly_chart(fig_func, width='stretch', on_select="rerun")
                filtro_func = selected_points["selection"]["points"][0]["x"] if selected_points and "selection" in selected_points and selected_points["selection"]["points"] else None
                df_e_data = df_filtrado[df_filtrado['Abrev'] == filtro_func] if filtro_func else df_filtrado
                df_e = df_e_data.groupby('Equipamento')['Horas_Dec'].sum().reset_index()
                fig_equip = px.bar(df_e, x='Equipamento', y='Horas_Dec', title=f"Horas por Equipamento {'- '+filtro_func if filtro_func else ''}", color_discrete_sequence=['#000000'], text_auto='.1f')
                fig_equip.update_layout(xaxis=dict(tickangle=-45, automargin=True), margin=dict(b=120), template="plotly_white")
                st.plotly_chart(fig_equip, width='stretch')
                if filtro_func and st.button("Limpar Filtro"): st.rerun()
else:
    with aba_view[4]:
        st.subheader("⏱️ Registros de Horas")
        aponts_raw = db.get_apontamentos_com_id()
        if aponts_raw:
            df_ap_full = pd.DataFrame(aponts_raw, columns=["ID", "Matrícula", "Nome", "Função", "Equipamento", "Atividade", "Entrada", "S. Almoço", "R. Almoço", "Saída", "Total", "Data"])
            st.dataframe(df_ap_full.tail(50), width='stretch')
            st.info("Apenas administradores podem excluir registros.")

# --- ABAS EXCLUSIVAS DE GESTÃO (LOGADO) ---
if st.session_state.logged_in:
    # CONSULTA GERAL
    with aba_view[5]:
        st.subheader("📖 Consulta de Efetivo")
        
        # Botão de Download Excel no topo (discreto e estilizado)
        dados = db.get_funcionarios()
        if dados:
            df = pd.DataFrame(dados, columns=["Matrícula", "Nome", "Função", "Abrev.", "Admissão", "MO", "Status"])
            
            # Preparar arquivo Excel
            excel_data = converter_df_para_excel(df)
            
            # Botão de download estilizado
            st.markdown("""
                <div style='text-align: right; margin-bottom: 15px;'>
            """, unsafe_allow_html=True)
            
            st.download_button(
                label="📥 Exportar para Excel",
                data=excel_data,
                file_name=f"consulta_efetivo_{now_br.strftime('%Y%m%d_%H%M')}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                help="Baixar dados em formato Excel"
            )
            
            st.markdown("</div>", unsafe_allow_html=True)
            
            # 🔎 Filtros de Busca
            st.markdown("### 🔎 Filtros de Busca")

            col_f1, col_f2, col_f3 = st.columns(3)

            with col_f1:
                filtro_nome = st.text_input("Buscar por Nome")

            with col_f2:
                filtro_matricula = st.text_input("Buscar por Matrícula")

            with col_f3:
                filtro_funcao = st.text_input("Buscar por Função")

            df_filtrado = df.copy()

            if filtro_nome:
                df_filtrado = df_filtrado[df_filtrado["Nome"].str.contains(filtro_nome, case=False, na=False)]

            if filtro_matricula:
                df_filtrado = df_filtrado[df_filtrado["Matrícula"].astype(str).str.contains(filtro_matricula, case=False, na=False)]

            if filtro_funcao:
                df_filtrado = df_filtrado[df_filtrado["Função"].str.contains(filtro_funcao, case=False, na=False)]

            st.markdown("---")

            st.dataframe(
                df_filtrado.map(lambda x: str(x).upper() if pd.notnull(x) else x),
                width='stretch'
            )

    # REGISTROS DE HORAS
    with aba_view[6]:
        st.subheader("⏱️ Registros de Horas Detalhados")
        aponts_raw = db.get_apontamentos_com_id()
        if aponts_raw:
            df_ap_full = pd.DataFrame(aponts_raw, columns=["ID", "Matrícula", "Nome", "Função", "Equipamento", "Atividade", "Entrada", "S. Almoço", "R. Almoço", "Saída", "Total", "Data"])
            st.dataframe(df_ap_full.tail(50), width='stretch')
            with st.expander("🗑️ Excluir Registros (Acesso Admin)"):
                sel_excluir = st.multiselect("Selecione os IDs para remover", df_ap_full['ID'].tolist())
                if st.button("EXCLUIR SELECIONADOS"):
                    for s in sel_excluir: db.delete_apontamento_por_id(s, st.session_state.user_name)
                    st.success("Excluído!"); time.sleep(1); st.rerun()

    # GESTÃO FUNÇÕES
    with aba_view[7]:
        st.subheader("⚙️ Gestão de Funções")
        c1, c2 = st.columns([2, 1])
        funcoes = db.get_funcoes()
        with c1:
            st.markdown("### Funções Cadastradas")
            st.table(pd.DataFrame([f.upper() for f in funcoes], columns=["Função"]))
        with c2:
            st.markdown("### Ações")
            n_f = st.text_input("Nova Função")
            if st.button("SALVAR FUNÇÃO"):
                if db.add_funcao(n_f, st.session_state.user_name): st.success("Salvo!"); st.rerun()
            st.markdown("---")
            f_del = st.selectbox("Remover Função", [""] + funcoes)
            if st.button("EXCLUIR FUNÇÃO"):
                if f_del: db.delete_funcao(f_del, st.session_state.user_name); st.success("Removido!"); st.rerun()

    # GESTÃO EQUIPAMENTOS
    with aba_view[8]:
        st.subheader("🚜 Gestão de Equipamentos")
        c1, c2 = st.columns([2, 1])
        equips = db.get_equipamentos()
        with c1:
            st.markdown("### Equipamentos Cadastrados")
            st.table(pd.DataFrame([e.upper() for e in equips], columns=["Equipamento"]))
        with c2:
            st.markdown("### Ações")
            n_e = st.text_input("Novo Equipamento")
            if st.button("SALVAR EQUIPAMENTO"):
                if db.add_equipamento(n_e, st.session_state.user_name): st.success("Salvo!"); st.rerun()
            st.markdown("---")
            e_del = st.selectbox("Remover Equipamento", [""] + equips)
            if st.button("EXCLUIR EQUIPAMENTO"):
                if e_del: db.delete_equipamento(e_del, st.session_state.user_name); st.success("Removido!"); st.rerun()

    # ATUALIZAR DADOS
    with aba_view[9]:
        st.subheader("✏️ Atualizar Cadastro")
        dados = db.get_funcionarios()
        mats = [d[0] for d in dados]
        if mats:
            s_m = st.selectbox("Selecione a Matrícula", mats)
            f_d = next((f for f in dados if f[0] == s_m), None)
            if f_d:
                with st.form(key=f"form_upd_{st.session_state.form_key}"):
                    u_n = st.text_input("Nome", value=f_d[1])
                    u_f = st.selectbox("Função", db.get_funcoes(), index=db.get_funcoes().index(f_d[2]) if f_d[2] in db.get_funcoes() else 0)
                    u_a = st.text_input("Abreviação", value=f_d[3])
                    u_d = st.date_input("Admissão", value=datetime.strptime(str(f_d[4]), '%Y-%m-%d').date() if f_d[4] else get_now_br().date())
                    u_mo = st.selectbox("MO", ["MOD", "MOI"], index=0 if f_d[5] == "MOD" else 1)
                    u_st = st.selectbox("Status", ["Ativo", "Inativo"], index=0 if f_d[6] == "Ativo" else 1)
                    if st.form_submit_button("SALVAR ALTERAÇÕES"):
                        if db.update_funcionario(s_m, u_n, u_f, u_a, u_d, u_mo, u_st, st.session_state.user_name):
                            st.success("Atualizado!"); reset_form(); time.sleep(1); st.rerun()

    # REMOVER REGISTRO
    with aba_view[10]:
        st.subheader("🗑️ Remover Colaborador")
        mats = [d[0] for d in db.get_funcionarios()]
        if mats:
            d_m = st.selectbox("Excluir Matrícula Definitivamente", mats)
            if st.button("CONFIRMAR EXCLUSÃO"):
                if db.delete_funcionario(d_m, st.session_state.user_name): st.success("Removido!"); time.sleep(1); st.rerun()

    # GESTÃO DE USUÁRIOS
    with aba_view[11]:
        st.subheader("👥 Gestão de Usuários do Sistema")
        with st.form("novo_usuario"):
            n_u = st.text_input("Novo Usuário")
            n_p = st.text_input("Senha", type="password")
            if st.form_submit_button("CRIAR USUÁRIO"):
                if n_u and n_p:
                    if db.add_usuario(n_u, n_p, st.session_state.user_name): st.success("Usuário criado!"); st.rerun()
                    else: st.error("Erro ao criar.")
        st.markdown("---")
        usuarios = db.get_usuarios()
        u_del = st.selectbox("Remover Usuário", [u for u in usuarios if u != 'admin'])
        if st.button("EXCLUIR USUÁRIO"):
            if db.delete_usuario(u_del, st.session_state.user_name): st.success("Removido!"); st.rerun()

    # ABA DE AUDITORIA (NOVA)
    with aba_view[12]:
        st.subheader("🔍 Auditoria e Rastreabilidade")
        st.info("Log das últimas 500 ações realizadas no sistema.")
        logs = db.get_logs()
        if logs:
            df_logs = pd.DataFrame(logs, columns=["Data/Hora", "Usuário", "Ação", "Tabela", "Detalhes"])
            st.dataframe(df_logs, use_container_width=True)
        else:
            st.warning("Nenhum log registrado ainda.")


# --- ABA PLUVIOMETRIA ---
pluv_index = tabs_list.index("🌧️ Pluviometria")

with aba_view[pluv_index]:
    st.subheader("🌧️ Pluviometria – CEMADEN + INMET | Barueri")

    c1, c2, c3 = st.columns([2,2,1])
    with c1:
        st.text_input("Origem / Fonte", "CEMADEN + INMET", disabled=True)
    with c2:
        data_ref = st.date_input("Data", value=get_now_br().date())
    with c3:
        if st.button("🔄 Capturar dados"):
            st.session_state["pluv_refresh"] = True

    horas = get_pluviometria_cruzada(data_ref)
    total_mm = sum(horas.values())
    st.caption(f"Total no dia: {total_mm:.2f} mm")

    if total_mm == 0:
        st.warning("⚠️ Nenhum dado retornado da estação CEMADEN 7033 para esta data.")

    def bloco(nome, hs):
        st.markdown(f"**{nome}**")
        cols = st.columns(len(hs))
        for i, h in enumerate(hs):
            cols[i].text_input(f"{h}h", f"{horas[h]:.2f}", disabled=True)

    bloco("Manhã", [6,7,8,9,10,11])
    bloco("Tarde", [12,13,14,15,16,17])
    bloco("Noite", [18,19,20,21,22,23])
    bloco("Madrugada", [0,1,2,3,4,5])


# --- FOOTER PROFISSIONAL ---
st.markdown(f"""
    <div class='footer'>
        <b>Hélio Silvestre dos Santos</b> - Analista de Dados e Business Intelligence
        <br>
        <a href='https://github.com/santoshelios' target='_blank'>📁 GitHub</a>
        <a href='https://www.linkedin.com/in/heliossantos' target='_blank'>💼 LinkedIn</a>
        <a href='https://wa.me/5534998375673' target='_blank'>💬 WhatsApp</a>
        <a href='https://app.xperiun.com//in/heliossantos' target='_blank'>🌐 Portfólio</a>
    </div>
""", unsafe_allow_html=True)
