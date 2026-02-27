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

import base64

def get_base64_logo(path):
    with open(path, "rb") as img_file:
        return base64.b64encode(img_file.read()).decode()

logo_base64 = get_base64_logo("logo_Santin.png")

st.markdown(f"""
<style>
.logo-top-right {{
    position: fixed;
    top: 15px;
    right: 25px;
    z-index: 9999;
}}
.logo-top-right img {{
    width: 110px;
}}
</style>

<div class="logo-top-right">
    <img src="data:image/png;base64,{logo_base64}">
</div>
""", unsafe_allow_html=True)





# --- ESTILIZAÇÃO CUSTOMIZADA (Padrão Corporativo) ---

st.markdown("""
<style>

.main { background-color: #F4F6F9; }

[data-testid="stSidebar"] { background-color: #0F172A; }
[data-testid="stSidebar"] * { color: #E2E8F0 !important; }

.header-style {
    color: #111827;
    font-weight: 800;
    font-size: 30px;
    margin-bottom: 35px;
}

.stButton>button {
    border-radius: 12px;
    height: 3.2em;
    background: linear-gradient(135deg, #1E3A8A 0%, #2563EB 100%);
    color: white;
    font-weight: 600;
    border: none;
    transition: 0.2s ease-in-out;
    box-shadow: 0 4px 14px rgba(37, 99, 235, 0.3);
}
.stButton>button:hover {
    transform: translateY(-2px);
    box-shadow: 0 6px 18px rgba(37, 99, 235, 0.4);
}

.user-card {
    background-color: #1E293B;
    padding: 15px;
    border-radius: 12px;
    text-align: center;
    margin-bottom: 15px;
}

div[data-testid="metric-container"] {
    background-color: white;
    padding: 22px;
    border-radius: 16px;
    box-shadow: 0 4px 16px rgba(0,0,0,0.06);
    border: 1px solid #E5E7EB;
}

.js-plotly-plot .plotly text {
    font-size: 14px !important;
    font-weight: 600 !important;
}

.sidebar-footer {
    margin-top: 40px;
    padding-top: 20px;
    border-top: 1px solid #334155;
    font-size: 13px;
    color: #CBD5E1;
    text-align: center;
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

        # 🔹 Se não houve intervalo (sem almoço real)
        if t3 == t2 or t3 == t4:
            total = t4 - t1
        else:
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



def get_pluviometria_cruzada(data_ref):
    try:
        latitude = -23.505
        longitude = -46.879

        data_str = data_ref.strftime("%Y-%m-%d")

        url = (
            "https://archive-api.open-meteo.com/v1/archive"
            f"?latitude={latitude}"
            f"&longitude={longitude}"
            f"&start_date={data_str}"
            f"&end_date={data_str}"
            "&hourly=precipitation"
            "&timezone=America/Sao_Paulo"
        )

        r = requests.get(url, timeout=20)
        r.raise_for_status()
        data = r.json()

        horas = {h: 0.0 for h in range(24)}

        if "hourly" not in data:
            return horas

        horas_lista = data["hourly"].get("time", [])
        chuva_lista = data["hourly"].get("precipitation", [])

        agora = datetime.now(pytz.timezone("America/Sao_Paulo"))

        for t, chuva in zip(horas_lista, chuva_lista):
            try:
                hora = int(t[11:13])

                # Remove horas futuras no dia atual
                if data_ref == agora.date() and hora > agora.hour:
                    continue

                horas[hora] += float(chuva or 0)
            except:
                continue

        return horas

    except Exception as e:
        st.error(f"❌ ERRO OPEN-METEO: {e}")
        return {h: 0.0 for h in range(24)}

# --- RELÓGIO COM FUSO BRASÍLIA ---
now_br = get_now_br()
st.markdown(f"<div class='clock-style'>🕒 {now_br.strftime('%d/%m/%Y - %H:%M')} (Brasília)</div>", unsafe_allow_html=True)

# --- BARRA LATERAL ---
with st.sidebar:
    st.markdown("<h2 style='text-align: center;'>🔐 ACESSO</h2>", unsafe_allow_html=True)
    
    if not st.session_state.logged_in:
        user = st.text_input("Usuário", placeholder="Digite seu usuário",autocomplete='off')
        password = st.text_input("Senha", type="password", placeholder="Digite sua senha",autocomplete='new-password')
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
        st.markdown(f"""
            <div style="
                text-align:center;
                padding:16px;
                background:linear-gradient(135deg,#1E293B,#0F172A);
                border-radius:12px;
                border:1px solid #334155;
                margin-bottom:12px;
            ">
                <div style="font-size:13px; color:#94A3B8;">Usuário Ativo</div>
                <div style="font-size:18px; font-weight:700; color:#FFFFFF;">
                    {st.session_state.user_name}
                </div>
            </div>
        """, unsafe_allow_html=True)

        if st.button("SAIR DO SISTEMA"):
            st.session_state.logged_in = False
            st.session_state.user_name = "Visitante"
            st.rerun()

    #st.markdown("---")
    #st.info("Sistema de Gestão de Obras v2.0")

# --- CORPO PRINCIPAL ---

st.markdown(f"""
<style>
.header-container {{
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-top: 10px;
}}

.header-title {{
    color: #111827;
    font-weight: 800;
    font-size: 30px;
}}
</style>

<div class="header-container">
    <div class="header-title">
        🏗️ GRUPO SANTIN - Controle de Obras
    </div>
    <img src="data:image/png;base64,{logo_base64}" width="120">
</div>
""", unsafe_allow_html=True)


# Definição das Abas (ORDEM CORRETA)
if st.session_state.logged_in:
    tabs_list = ["📅 Efetivo Diário", "➕ Novo Colaborador", "✍️ Apontar Horas", "📊 Dash Efetivo", "📈 Dash Produtividade", "📖 Consulta Geral", "⏱️ Registros de Horas", "⚙️ Gestão de Funções", "🚜 Gestão de Equipamentos", "✏️ Atualizar Dados", "🗑️ Remover Registro", "👥 Gestão de Usuários", "🔍 Auditoria", "🌧️ Pluviometria", "🌧️ Histórico Chuva"]
else:
    tabs_list = ["📅 Efetivo Diário", "📊 Dash Efetivo", "📈 Dash Produtividade", "📖 Consulta Geral", "⏱️ Registros de Horas", "🌧️ Pluviometria", "🌧️ Histórico Chuva"]

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
            extra_100 = st.checkbox("Considerar 100% Hora Extra")
            if st.form_submit_button("REGISTRAR EM OBRA"):
                if sel_mat and equip and ativ:

                    # 🔒 VALIDAÇÃO TEMPORAL RÍGIDA
                    fmt = '%H:%M:%S'
                    t1 = datetime.strptime(str(ent), fmt)
                    t2 = datetime.strptime(str(s_alm), fmt)
                    t3 = datetime.strptime(str(r_alm), fmt)
                    t4 = datetime.strptime(str(s_fin), fmt)

                    if not (t1 < t4):
                        st.error("⚠️ A entrada deve ser menor que o fim da jornada.")
                        st.stop()

                    if t2 < t1:
                        st.error("⚠️ Saída para intervalo não pode ser menor que a entrada.")
                        st.stop()

                    if t3 < t2:
                        st.error("⚠️ Retorno não pode ser menor que a saída para intervalo.")
                        st.stop()

                    if t4 < t3:
                        st.error("⚠️ Fim da jornada não pode ser menor que o retorno.")
                        st.stop()

                    # 🔎 Buscar apontamentos já existentes
                    aponts_existentes = db.get_apontamentos()

                    aponts_mesmo_dia = [
                        a for a in aponts_existentes
                        if str(a[0]) == str(sel_mat)
                        and str(a[10]) == str(data_ap)
                    ]

                    def to_dt(hora):
                        return datetime.strptime(str(hora), "%H:%M:%S")

                    novo_intervalos = [
                        (to_dt(ent), to_dt(s_alm)),
                        (to_dt(r_alm), to_dt(s_fin))
                    ]

                    sobreposicao = False

                    for ap in aponts_mesmo_dia:
                        ent_exist = to_dt(ap[5])
                        s_alm_exist = to_dt(ap[6])
                        r_alm_exist = to_dt(ap[7])
                        s_fin_exist = to_dt(ap[8])

                        intervalos_existentes = [
                            (ent_exist, s_alm_exist),
                            (r_alm_exist, s_fin_exist)
                        ]

                        for n_inicio, n_fim in novo_intervalos:
                            for e_inicio, e_fim in intervalos_existentes:
                                if n_inicio < e_fim and n_fim > e_inicio:
                                    sobreposicao = True
                                    break
                            if sobreposicao:
                                 st.error("⚠️ Já existe apontamento neste intervalo de horário para este colaborador nesta data.")
                    else:

                        # 🔹 Cálculo de horas normais e extras
                        horas = int(total_h.split(":")[0])
                        minutos = int(total_h.split(":")[1])
                        total_float = horas + minutos / 60

                        carga_dia = db.get_carga_dia(data_ap)

                        if extra_100:
                            horas_normais = 0
                            horas_extra = total_float
                        else:
                            if carga_dia == 0:
                                horas_normais = 0
                                horas_extra = total_float
                            else:
                                horas_extra = max(0, total_float - carga_dia)
                                horas_normais = total_float - horas_extra

                        db.add_apontamento(
                            sel_mat,
                            nome_auto,
                            funcao_auto,
                            equip,
                            ativ,
                            ent,
                            s_alm,
                            r_alm,
                            s_fin,
                            total_h,
                            horas_normais,
                            horas_extra,
                            data_ap,
                            st.session_state.user_name
                        )

                        st.success("Registrado!")
                        reset_form()
                        time.sleep(1)
                        st.rerun()

                else:
                    st.warning("Preencha os campos obrigatórios.")
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
def render_pluviometria():

    st.subheader("🌧️ Pluviometria – Open-Meteo | Barueri")

    c1, c2, c3 = st.columns([2,2,1])
    with c1:
        st.text_input("Origem / Fonte", "Open-Meteo", disabled=True)
    with c2:
        data_ref = st.date_input("Data", value=get_now_br().date())
    with c3:
        st.button("🔄 Atualizar")

    horas = get_pluviometria_cruzada(data_ref)
    total_mm = sum(horas.values())

    inicio_mes = data_ref.replace(day=1)

    url_mes = (
        "https://archive-api.open-meteo.com/v1/archive"
        f"?latitude=-23.505"
        f"&longitude=-46.879"
        f"&start_date={inicio_mes.strftime('%Y-%m-%d')}"
        f"&end_date={data_ref.strftime('%Y-%m-%d')}"
        "&daily=precipitation_sum"
        "&timezone=America/Sao_Paulo"
    )

    try:
        r_mes = requests.get(url_mes, timeout=20)
        r_mes.raise_for_status()
        dados_mes = r_mes.json()
        acumulado_mes = sum(dados_mes.get("daily", {}).get("precipitation_sum", []))
    except:
        acumulado_mes = 0.0

    # --- BOTÃO ADMIN: SALVAR PLUVIOMETRIA ---
    admin_user = None
    try:
        admin_user = st.secrets["credentials"]["admin_user"]
    except:
        admin_user = "admin"

    if st.session_state.get("user_name") == admin_user:
        st.markdown("---")
        if st.button("💾 Salvar Pluviometria no Banco"):
            sucesso = db.add_pluviometria(
                data_ref,
                horas,
                st.session_state.get("user_name", "admin")
            )

            if sucesso:
                st.success("Pluviometria salva com sucesso no banco.")
            else:
                st.warning("Não foi possível salvar.")


    col1, col2 = st.columns(2)
    with col1:
        st.metric("🌧️ Volume Hoje (mm)", f"{total_mm:.2f}")
    with col2:
        st.metric("📅 Acumulado no Mês (mm)", f"{acumulado_mes:.2f}")

    for periodo, horas_lista in {
        "Manhã":[6,7,8,9,10,11],
        "Tarde":[12,13,14,15,16,17],
        "Noite":[18,19,20,21,22,23],
        "Madrugada":[0,1,2,3,4,5]
    }.items():

        st.markdown(f"### {periodo}")
        cols = st.columns(6)
        for i, h in enumerate(horas_lista):
            with cols[i]:
                st.markdown(f"**{h}h**")
                st.markdown(
                    f"<div style='background:#FFD700;padding:8px;border-radius:8px;text-align:center;font-weight:700;color:#000'>{horas[h]:.2f} mm</div>",
                    unsafe_allow_html=True
                )

    st.markdown("## 📅 Previsão – Próximos 7 Dias (Barueri)")

    try:
        forecast_url = (
            "https://api.open-meteo.com/v1/forecast"
            "?latitude=-23.505"
            "&longitude=-46.879"
            "&daily=precipitation_sum,precipitation_probability_max"
            "&timezone=America/Sao_Paulo"
        )

        r_prev = requests.get(forecast_url, timeout=20)
        r_prev.raise_for_status()
        dados_prev = r_prev.json()

        if "daily" in dados_prev:
            df_prev = pd.DataFrame({
                "Data": dados_prev["daily"]["time"],
                "Precipitação (mm)": dados_prev["daily"]["precipitation_sum"],
                "Probabilidade (%)": dados_prev["daily"]["precipitation_probability_max"]
            })

            fig_prev = px.bar(
                df_prev,
                x="Data",
                y="Precipitação (mm)",
                text_auto=True
            )

            fig_prev.add_scatter(
                x=df_prev["Data"],
                y=df_prev["Probabilidade (%)"],
                mode="lines+markers+text",
                name="Probabilidade (%)",
                yaxis="y2",
                text=[f"{int(v)}%" for v in df_prev["Probabilidade (%)"]],
                textposition="top center",
                textfont=dict(
                    color="black",
                    size=12
                ),
                line=dict(
                    width=3,
                    color="#FF6B00"
                ),
                marker=dict(
                    size=8,
                    color="#FF6B00"
                )
            )

            fig_prev.update_layout(
                title="Precipitação e Probabilidade – Próximos 7 Dias",
                title_x=0.5,
                yaxis=dict(title="Precipitação (mm)"),
                yaxis2=dict(
                    title="Probabilidade (%)",
                    overlaying="y",
                    side="right"
                )
            )

            st.plotly_chart(fig_prev, use_container_width=True)

    except:
        st.warning("Não foi possível carregar previsão.")

pluv_index = tabs_list.index("🌧️ Pluviometria")
with aba_view[pluv_index]:
    render_pluviometria()

# --- FOOTER PROFISSIONAL ---
# --- FOOTER PROFISSIONAL ---
st.markdown(f"""
    <div style='display:none;'>
        <b>Hélio Silvestre dos Santos</b> - Analista de Dados e Business Intelligence
        <br>
        <a href='https://github.com/santoshelios' target='_blank'>📁 GitHub</a>
        <a href='https://www.linkedin.com/in/heliossantos' target='_blank'>💼 LinkedIn</a>
        <a href='https://wa.me/5534998375673' target='_blank'>💬 WhatsApp</a>
        <a href='https://app.xperiun.com//in/heliossantos' target='_blank'>🌐 Portfólio</a>
    </div>
""", unsafe_allow_html=True)





# --- ABA HISTÓRICO DE CHUVA ---
if "🌧️ Histórico Chuva" in tabs_list:
    hist_index = tabs_list.index("🌧️ Histórico Chuva")
    with aba_view[hist_index]:
        st.subheader("🌧️ Histórico de Pluviometria")

        col1, col2 = st.columns(2)

        with col1:
            d_ini = st.date_input(
                "Data Início",
                value=get_now_br().date().replace(day=1),
                key="hist_ini"
            )

        with col2:
            d_fim = st.date_input(
                "Data Fim",
                value=get_now_br().date(),
                key="hist_fim"
            )

        dados = db.get_pluviometria_periodo(d_ini, d_fim)

        if dados:
            df_hist = pd.DataFrame(
                dados,
                columns=["Data", "Hora", "Chuva (mm)"]
            )

            # 🔍 Dataframe dentro de expander
            with st.expander("🔍 Ver dados detalhados por hora"):
                df_formatado = df_hist.copy()
                df_formatado["Hora"] = df_formatado["Hora"].astype(str) + "h"
                st.dataframe(
                    df_formatado.sort_values(["Data", "Hora"]),
                    use_container_width=True
                )

            # 📊 Gráfico principal (Total diário)
            df_total = (
                df_hist.groupby("Data")["Chuva (mm)"]
                .sum()
                .reset_index()
            )

            fig = px.bar(
                df_total,
                x="Data",
                y="Chuva (mm)",
                title="Total Diário de Chuva",
                text_auto=True
            )

            fig.update_layout(
                xaxis_title="Data",
                yaxis_title="Chuva (mm)",
                title_x=0.5
            )

            st.plotly_chart(fig, use_container_width=True)

          


st.sidebar.markdown("""
<div class='sidebar-footer'>
<b>GRUPO SANTIN</b><br>
Sistema Corporativo de Controle de Obras<br>
Business Intelligence • Engenharia • Gestão de Projetos
</div>
""", unsafe_allow_html=True)


st.sidebar.markdown("---")
st.sidebar.info("Sistema de Gestão de Obras v2.0")

# --- FOOTER PROFISSIONAL ---
st.markdown("""
<div style="
    text-align:center;
    margin-top:50px;
    font-size:14px;
    color:#111827;
    line-height:1.6;
">
    <b>Hélio Silvestre dos Santos</b> - Analista de Dados e Business Intelligence
    <br>
    <a href='https://github.com/santoshelios' target='_blank'>📁 GitHub</a> |
    <a href='https://www.linkedin.com/in/heliossantos' target='_blank'>💼 LinkedIn</a> |
    <a href='https://wa.me/5534998375673' target='_blank'>💬 WhatsApp</a> |
    <a href='https://app.xperiun.com//in/heliossantos' target='_blank'>🌐 Portfólio</a>
</div>
""", unsafe_allow_html=True) 