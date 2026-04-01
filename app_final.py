import streamlit as st
import pandas as pd
import time
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
from io import BytesIO
import pytz
import requests
import base64

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

def get_base64_logo(path):
    try:
        with open(path, "rb") as img_file:
            return base64.b64encode(img_file.read()).decode()
    except:
        return ""

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
/* Estilo Profissional para os Cards de Indicadores */
.metric-card {
    background: white;
    padding: 25px 20px;
    border-radius: 16px;
    box-shadow: 0 10px 25px rgba(0,0,0,0.05);
    border: 1px solid #F1F5F9;
    text-align: center;
    transition: all 0.3s ease;
    margin-bottom: 20px;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
}
.metric-card:hover {
    transform: translateY(-5px);
    box-shadow: 0 15px 35px rgba(0,0,0,0.1);
    border-color: #E2E8F0;
}
.metric-card h3 {
    color: #64748B;
    font-size: 15px;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 1px;
    margin: 0 0 10px 0;
}
.metric-card h2 {
    font-size: 42px;
    font-weight: 800;
    margin: 0;
    line-height: 1;
}
.metric-icon {
    font-size: 28px;
    margin-bottom: 12px;
    background: #F8FAFC;
    width: 60px;
    height: 60px;
    display: flex;
    align-items: center;
    justify-content: center;
    border-radius: 50%;
}

/* Estilo para o Footer Customizado */
.footer {
    position: fixed;
    left: 0;
    bottom: 0;
    width: 100%;
    background-color: #0F172A;
    color: #E2E8F0;
    text-align: center;
    padding: 10px 0;
    font-size: 14px;
    z-index: 999;
}
.footer a {
    color: #3B82F6;
    text-decoration: none;
    margin: 0 10px;
    font-weight: 600;
}
.footer a:hover {
    text-decoration: underline;
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
        if ":" not in str(h_m): return 0.0
        h, m = map(int, str(h_m).split(':'))
        return h + m / 60.0
    except:
        return 0.0

def converter_df_para_excel(df):
    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Dados')
    output.seek(0)
    return output

def get_pluviometria_cruzada(data_ref):
    try:
        latitude, longitude = -23.505, -46.879
        data_str = data_ref.strftime("%Y-%m-%d")
        url = f"https://archive-api.open-meteo.com/v1/archive?latitude={latitude}&longitude={longitude}&start_date={data_str}&end_date={data_str}&hourly=precipitation&timezone=America/Sao_Paulo"
        r = requests.get(url, timeout=20)
        r.raise_for_status()
        data = r.json()
        horas = {h: 0.0 for h in range(24)}
        if "hourly" not in data: return horas
        horas_lista = data["hourly"].get("time", [])
        chuva_lista = data["hourly"].get("precipitation", [])
        agora = get_now_br()
        for t, chuva in zip(horas_lista, chuva_lista):
            try:
                hora = int(t[11:13])
                if data_ref == agora.date() and hora > agora.hour: continue
                horas[hora] += float(chuva or 0)
            except: continue
        return horas
    except Exception as e:
        st.error(f"❌ ERRO OPEN-METEO: {e}")
        return {h: 0.0 for h in range(24)}

# --- RELÓGIO ---
now_br = get_now_br()
st.markdown(f"<div style='text-align: right; color: #666; font-size: 14px;'>🕒 {now_br.strftime('%d/%m/%Y - %H:%M')} (Brasília)</div>", unsafe_allow_html=True)

# --- BARRA LATERAL ---
with st.sidebar:
    st.markdown("<h2 style='text-align: center;'>🔐 ACESSO</h2>", unsafe_allow_html=True)
    if not st.session_state.logged_in:
        user = st.text_input("Usuário", placeholder="Digite seu usuário", autocomplete='off')
        password = st.text_input("Senha", type="password", placeholder="Digite sua senha", autocomplete='new-password')
        if st.button("ENTRAR NO SISTEMA",width='stretch'):
            if db.check_login(user, password):
                st.session_state.logged_in = True
                st.session_state.user_name = user
                st.success("Bem-vindo!")
                time.sleep(0.5); st.rerun()
            else:
                st.error("Acesso negado")
    else:
        st.markdown(f"""
            <div class="user-card">
                <div style="font-size:13px; color:#94A3B8;">Usuário Ativo</div>
                <div style="font-size:18px; font-weight:700; color:#FFFFFF;">{st.session_state.user_name}</div>
            </div>
        """, unsafe_allow_html=True)
        if st.button("SAIR DO SISTEMA",width='stretch'):
            st.session_state.logged_in = False
            st.session_state.user_name = "Visitante"
            st.rerun()

# --- CORPO PRINCIPAL ---
st.markdown(f"""
<div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px;">
    <div style="color: #111827; font-weight: 800; font-size: 30px;">🏗️ GRUPO SANTIN - Controle de Obras</div>
    <img src="data:image/png;base64,{logo_base64}" width="120">
</div>
""", unsafe_allow_html=True)

# Definição das Abas conforme perfil
if st.session_state.logged_in:
    tabs_list = ["📅 Efetivo Diário", "➕ Novo Colaborador", "✍️ Apontar Horas", "📊 Dash Efetivo", "📈 Dash Produtividade", "📖 Consulta Geral", "⏱️ Registros de Horas", "⚙️ Gestão de Funções", "🚜 Gestão de Equipamentos", "✏️ Atualizar Dados", "🗑️ Remover Registro", "👥 Gestão de Usuários", "🔍 Auditoria", "🌧️ Pluviometria", "🌧️ Histórico Chuva"]
else:
    tabs_list = ["📅 Efetivo Diário", "📊 Dash Efetivo", "📈 Dash Produtividade", "📖 Consulta Geral", "⏱️ Registros de Horas", "🌧️ Pluviometria", "🌧️ Histórico Chuva"]

aba_view = st.tabs(tabs_list)

# --- FUNÇÃO RENDERIZAR PLUVIOMETRIA (Unificada) ---
def render_pluviometria(key_suffix=""):
    st.subheader("🌧️ Pluviometria – Open-Meteo | Barueri")
    
    # Layout de botões no topo
    if st.session_state.logged_in and key_suffix == "log":
        c1, c2, c3, c4 = st.columns([2,2,1,1])
        with c1: st.text_input("Origem / Fonte", "Open-Meteo", disabled=True, key=f"pluv_src_{key_suffix}")
        with c2: data_ref = st.date_input("Data", value=get_now_br().date(), key=f"pluv_date_{key_suffix}")
        with c3: st.button("🔄 Atualizar", key=f"pluv_refresh_{key_suffix}", width='stretch')
        with c4:
            # Botão Salvar movido para o topo para usuários logados
            if st.button("💾 Salvar", key=f"pluv_save_{key_suffix}", width='stretch'):
                # Como a função precisa retornar data_ref e horas, salvaremos após obter as horas
                st.session_state[f'save_pluv_{key_suffix}'] = True
    else:
        c1, c2, c3 = st.columns([2,2,1])
        with c1: st.text_input("Origem / Fonte", "Open-Meteo", disabled=True, key=f"pluv_src_{key_suffix}")
        with c2: data_ref = st.date_input("Data", value=get_now_br().date(), key=f"pluv_date_{key_suffix}")
        with c3: st.button("🔄 Atualizar", key=f"pluv_refresh_{key_suffix}", width='stretch')
    
    horas = get_pluviometria_cruzada(data_ref)
    total_mm = sum(horas.values())
    
    # Executa o salvamento se o botão do topo foi clicado
    if st.session_state.get(f'save_pluv_{key_suffix}', False):
        if db.add_pluviometria(data_ref, horas, st.session_state.user_name):
            st.success("Pluviometria salva com sucesso!")
        st.session_state[f'save_pluv_{key_suffix}'] = False

    col1, col2 = st.columns(2)
    with col1: st.metric("🌧️ Volume Hoje (mm)", f"{total_mm:.2f}")
    


    def cor_chuva(mm):
        if mm == 0:
            return "#F8FAFC"
        elif mm <= 0.3:
            return "#BFDBFE"
        elif mm <= 1:
            return "#60A5FA"
        elif mm <= 3:
            return "#3B82F6"
        elif mm <= 6:
         return "#2563EB"
        else:
         return "#1E3A8A"
        #if mm == 0: return "#F8FAFC"
        #elif mm <= 0.2: return "#DBEAFE"
        #elif mm <= 1: return "#93C5FD"
        #elif mm <= 5: return "#3B82F6"
        #else: return "#1E3A8A"

    turnos = {
        "🌅 Manhã":[6,7,8,9,10,11], "☀️ Tarde":[12,13,14,15,16,17],
        "🌃 Noite":[18,19,20,21,22,23], "🌙 Madrugada":[0,1,2,3,4,5]
    }
    for periodo, horas_lista in turnos.items():
        st.markdown(f"### {periodo}")
        cols = st.columns(6)
        for i, h in enumerate(horas_lista):
            mm = horas[h]
            cor = cor_chuva(mm)
            if mm <=1:
                texto_cor = '#0F172A'
            else:
                texto_cor = 'white'
            #texto_cor = "#0F172A" if mm == 0 else "white"
            border = "1px solid #E5E7EB" if mm == 0 else "none"
            with cols[i]:
                st.markdown(f"**{h}h**")
                st.markdown(f"<div style='background:{cor};padding:8px;border-radius:8px;border:{border};text-align:center;font-weight:700;color:{texto_cor}'>{mm:.2f} mm</div>", unsafe_allow_html=True)
    
    st.markdown("""
    <div style="margin-top:30px;margin-bottom:20px;border-top:1px solid #9BBAE8;"></div>
    """, unsafe_allow_html=True)

# ===== PREVISÃO 7 DIAS =====
    st.markdown("### 🌦️ Previsão de Chuva — Próximos 7 dias")

    @st.cache_data(ttl=1800)
    def get_forecast():
        try:
            url = "https://api.open-meteo.com/v1/forecast"
            params = {
                "latitude": -23.505,
                "longitude": -46.879,
                "daily": "precipitation_sum",
                "timezone": "America/Sao_Paulo",
                "forecast_days": 7
            }
            # Adicionado verify=False para evitar erro de SSL no Streamlit Cloud
            r = requests.get(url, params=params, timeout=20, verify=False)
            r.raise_for_status()
            return r.json().get("daily", {})
        except Exception as e:
            st.warning(f"Não foi possível carregar a previsão do tempo: {e}")
            return {}

    prev = get_forecast()

    if prev:
        df_prev = pd.DataFrame({
            "Data": prev.get("time", []),
            "Chuva (mm)": prev.get("precipitation_sum", [])
        })

        fig_prev = px.bar(
            df_prev,
            x="Data",
            y="Chuva (mm)",
            color="Chuva (mm)",
            color_continuous_scale="Blues",
            text_auto=True
        )

        fig_prev.update_layout(
            xaxis_tickangle=-45,
            yaxis_title="mm",
            xaxis_title=None
        )

        st.plotly_chart(fig_prev, width='stretch')

    return data_ref, horas

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
                        try:
                            if df_u['Data'].dtype == 'object': df_u['Data'] = pd.to_datetime(df_u['Data'])
                            datas_no_arquivo = df_u['Data'].unique()
                            st.info(f"Deletando dados de {len(datas_no_arquivo)} data(s)...")
                            for d in datas_no_arquivo:
                                if hasattr(d, 'date'): d = d.date()
                                db.delete_efetivo_por_data(d, st.session_state.user_name)
                            st.info(f"Inserindo {len(df_u)} registros...")
                            if db.add_efetivo_diario_batch(df_u, st.session_state.user_name):
                                st.success("Efetivo carregado com sucesso!")
                                time.sleep(1); st.rerun()
                            else: st.error("Erro ao inserir registros no banco.")
                        except Exception as process_error: st.error(f"Erro ao processar arquivo: {process_error}")
                    else: st.error(f"Colunas necessárias: {', '.join(cols_required)}")
                except Exception as e: st.error(f"Erro: {e}")

    dados_efetivo = db.get_efetivo_diario()
    if dados_efetivo is not None and not dados_efetivo.empty:
        df_ef = pd.DataFrame(dados_efetivo)
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
        
        
        
        
        # 1. Cadastro de Funcionários (para classificação MOI/MOD)
        df_cadastro = db.get_funcionarios()
        df_mo_info = pd.DataFrame(columns=['Matricula', 'MO_Tipo'])
        if df_cadastro is not None and not df_cadastro.empty:
            df_cad_clean = df_cadastro[['matricula', 'mo']].copy()
            df_cad_clean['matricula'] = pd.to_numeric(df_cad_clean['matricula'], errors='coerce')
            df_cad_clean = df_cad_clean.drop_duplicates(subset=['matricula'])
            df_mo_info = df_cad_clean.rename(columns={'matricula': 'Matricula', 'mo': 'MO_Tipo'})

        # 2. Jornada Padrão
        df_jornada = db.get_jornada_padrao()
        dict_jornada = {int(row['dia_semana']): float(row['carga_horas']) for _, row in df_jornada.iterrows()} if not df_jornada.empty else {}

        # 3. Filtramos o período selecionado para o Realizado
        df_hist = df_ef[
            (df_ef['Data'] >= d_ini) &
            (df_ef['Data'] <= d_fim)
        ].copy()

        # 4. Processamento do Realizado (Período)
        hht_mod, hht_moi = 0, 0
        col_status = 'Status' if 'Status' in df_hist.columns else ('Status_Val' if 'Status_Val' in df_hist.columns else None)
        
        if col_status:
            df_hist[col_status] = pd.to_numeric(df_hist[col_status], errors='coerce')
            df_hist = df_hist[df_hist[col_status] == 1]
        
        if not df_hist.empty:
            df_hist['Matricula'] = pd.to_numeric(df_hist['Matricula'], errors='coerce')
            df_hist = df_hist.merge(df_mo_info, on='Matricula', how='left')
            df_hist['MO_Tipo'] = df_hist['MO_Tipo'].fillna('NÃO CADASTRADO').astype(str).str.upper().str.strip()
            df_hist['dia_semana'] = pd.to_datetime(df_hist['Data']).dt.dayofweek
            df_hist['carga_h'] = df_hist['dia_semana'].map(dict_jornada).fillna(0)
            hht_mod = df_hist[df_hist['MO_Tipo'] == 'MOD']['carga_h'].sum()
            hht_moi = df_hist[df_hist['MO_Tipo'] == 'MOI']['carga_h'].sum()

        # 5. Processamento do Histograma (Previsto)
        df_hist_obra = db.get_histograma()
        if df_hist_obra is not None and not df_hist_obra.empty:
            df_hist_obra['data'] = pd.to_datetime(df_hist_obra['data']).dt.date
            df_hist_obra['dia_semana'] = pd.to_datetime(df_hist_obra['data']).dt.dayofweek
            df_hist_obra['carga_h'] = df_hist_obra['dia_semana'].map(dict_jornada).fillna(0)
            
            # HH Previsto no Período
            df_prev_periodo = df_hist_obra[(df_hist_obra['data'] >= d_ini) & (df_hist_obra['data'] <= d_fim)].copy()
            hh_prev_mod_periodo = (df_prev_periodo['qtd_prevista_mod'] * df_prev_periodo['carga_h']).sum()
            hh_prev_moi_periodo = (df_prev_periodo['qtd_prevista_moi'] * df_prev_periodo['carga_h']).sum()
            
            # HH Realizado Acumulado
            hh_real_mod_acum, hh_real_moi_acum = 0, 0
            if df_ef is not None and not df_ef.empty:
                df_real_acum = df_ef[(df_ef['Data'] <= d_fim)].copy()
                col_st = 'Status' if 'Status' in df_real_acum.columns else ('Status_Val' if 'Status_Val' in df_real_acum.columns else None)
                if col_st:
                    df_real_acum[col_st] = pd.to_numeric(df_real_acum[col_st], errors='coerce')
                    df_real_acum = df_real_acum[df_real_acum[col_st] == 1]
                
                if not df_real_acum.empty:
                    df_real_acum['Matricula'] = pd.to_numeric(df_real_acum['Matricula'], errors='coerce')
                    df_real_acum = df_real_acum.merge(df_mo_info, on='Matricula', how='left')
                    df_real_acum['MO_Tipo'] = df_real_acum['MO_Tipo'].fillna('N/A').astype(str).str.upper().str.strip()
                    df_real_acum['dia_semana'] = pd.to_datetime(df_real_acum['Data']).dt.dayofweek
                    df_real_acum['carga_h'] = df_real_acum['dia_semana'].map(dict_jornada).fillna(0)
                    hh_real_mod_acum = df_real_acum[df_real_acum['MO_Tipo'] == 'MOD']['carga_h'].sum()
                    hh_real_moi_acum = df_real_acum[df_real_acum['MO_Tipo'] == 'MOI']['carga_h'].sum()

            # Função auxiliar para formatar números no padrão brasileiro (ponto como milhar)
            def fmt_br(valor):
                return f"{valor:,.0f}".replace(",", ".")

            # Exibição dos Indicadores de Performance em HH
            st.markdown("#### 🧑‍💼⚙️ Performance de Homem-Hora (HH) - Previsto vs Realizado")
            
            # --- FUNÇÃO PARA GERAR CARD DE DESVIO ---
            def render_deviation_card(prev, real, label):
                """Renderiza um card de desvio com cores baseadas na severidade"""
                if prev > 0:
                    desvio = real - prev
                    desvio_pct = ((real - prev) / prev) * 100
                    
                    # Determina cor e ícone baseado no desvio
                    if desvio_pct > 20:
                        cor_valor = "#DC2626"
                        cor_bg = "#FEE2E2"
                        icone = "🚨"
                        tipo_alerta = "CRÍTICO"
                    elif desvio_pct > 10:
                        cor_valor = "#D97706"
                        cor_bg = "#FEF3C7"
                        icone = "⚠️"
                        tipo_alerta = "ATENÇÃO"
                    elif desvio_pct < -10:
                        cor_valor = "#0369A1"
                        cor_bg = "#E0F2FE"
                        icone = "ℹ️"
                        tipo_alerta = "INFO"
                    else:
                        cor_valor = "#059669"
                        cor_bg = "#ECFDF5"
                        icone = "✅"
                        tipo_alerta = "OK"
                    
                    direcao = "ACIMA" if desvio_pct > 0 else "ABAIXO"
                    
                    st.markdown(f"""
                    <div class='metric-card' style='background-color: {cor_bg}; min-height: auto; padding: 20px 15px;'>
                        <h3 style='color: {cor_valor}; font-size: 13px; margin: 0 0 8px 0;'>{icone} Desvio {label}</h3>
                        <h2 style='color: {cor_valor}; font-size: 32px; margin: 0 0 6px 0;'>{abs(desvio_pct):.1f}%</h2>
                        <div style='font-size: 11px; color: {cor_valor}; margin: 0; line-height: 1.3;'>
                            <b>{tipo_alerta}</b><br>{abs(desvio_pct):.1f}% {direcao}
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
                else:
                    st.markdown(f"""
                    <div class='metric-card' style='background-color: #F3F4F6; min-height: auto; padding: 20px 15px;'>
                        <h3 style='color: #6B7280; font-size: 13px; margin: 0 0 8px 0;'>- Desvio {label}</h3>
                        <h2 style='color: #9CA3AF; font-size: 32px; margin: 0;'>--</h2>
                    </div>
                    """, unsafe_allow_html=True)

            # --- MOD (COM 3 CARDS: Previsto, Acumulado, Desvio) ---
            st.markdown("##### 👥 Mão de Obra Direta (MOD)")
            c1, c2, c3 = st.columns(3)
            with c1:
                st.markdown(f"<div class='metric-card'><h3>HH Previsto (Período)</h3><h2 style='color: #2563EB;'>{fmt_br(hh_prev_mod_periodo)} h</h2></div>", unsafe_allow_html=True)
            with c2:
                st.markdown(f"<div class='metric-card'><h3>HH Acumulado (Real)</h3><h2 style='color: #1E3A8A;'>{fmt_br(hh_real_mod_acum)} h</h2></div>", unsafe_allow_html=True)
            with c3:
                render_deviation_card(hh_prev_mod_periodo, hht_mod, "MOD")
            
            # --- MOI (COM 3 CARDS: Previsto, Acumulado, Desvio) ---
            st.markdown("##### 🧑‍💼 Mão de Obra Indireta (MOI)")
            c4, c5, c6 = st.columns(3)
            with c4:
                st.markdown(f"<div class='metric-card'><h3>HH Previsto (Período)</h3><h2 style='color: #F59E0B;'>{fmt_br(hh_prev_moi_periodo)} h</h2></div>", unsafe_allow_html=True)
            with c5:
                st.markdown(f"<div class='metric-card'><h3>HH Acumulado (Real)</h3><h2 style='color: #B45309;'>{fmt_br(hh_real_moi_acum)} h</h2></div>", unsafe_allow_html=True)
            with c6:
                render_deviation_card(hh_prev_moi_periodo, hht_moi, "MOI")

        # Exibição dos Cards de HHT (Mantido para compatibilidade visual)
        st.markdown("#### 🏭 Homem-Hora Trabalhado (HHT) no Período")
        c_hht1, c_hht2 = st.columns(2)
        with c_hht1:
            st.markdown(f"""
            <div class='metric-card'>
                <div class='metric-icon' style='color: #2563EB; background: #DBEAFE;'>🛠️</div>
                <h3>HHT Total (MOD)</h3>
                <h2 style='color: #2563EB;'>{fmt_br(hht_mod)} h</h2>
            </div>
            """, unsafe_allow_html=True)
        with c_hht2:
            st.markdown(f"""
            <div class='metric-card'>
                <div class='metric-icon' style='color: #F59E0B; background: #FEF3C7;'>🖥️</div>
                <h3>HHT Total (MOI)</h3>
                <h2 style='color: #F59E0B;'>{fmt_br(hht_moi)} h</h2>
            </div>
            """, unsafe_allow_html=True)

        if not df_hist.empty:

                # 5. Criamos a base de datas para o gráfico não ter buracos
                intervalo_datas = pd.date_range(start=d_ini, end=d_fim)
                df_full_base = pd.DataFrame({'Data': pd.to_datetime(intervalo_datas).date}, columns=['Data'])

                fig_hist = go.Figure()
                cores_mo = {'MOD': '#2563EB', 'MOI': '#F59E0B'}

                # 6. Geramos as linhas para MOD e MOI
                for tipo in ['MOD', 'MOI']:
                    # Filtra os presentes (Status 1) que pertencem ao tipo de MO atual
                    df_tipo = df_hist[df_hist['MO_Tipo'] == tipo].copy()
                    
                    # Agrupa por data contando registros (paridade total com gráfico de barras)
                    df_count = (
                        df_tipo.groupby('Data').size()
                        .reset_index(name='Quantidade')
                    )
                    
                    # Garante que todos os dias do intervalo apareçam (mesmo com 0)
                    df_plot = (
                        df_full_base
                        .merge(df_count, on='Data', how='left')
                        .fillna(0)
                    )
                    df_plot['Quantidade'] = df_plot['Quantidade'].astype(int)

                    # Adiciona a linha ao gráfico
                    fig_hist.add_trace(go.Scatter(
                        x=df_plot['Data'],
                        y=df_plot['Quantidade'],
                        mode='lines+markers+text',
                        name=tipo,
                        line=dict(width=3, color=cores_mo[tipo], shape='spline'),
                        marker=dict(size=10, color=cores_mo[tipo]),
                        text=df_plot['Quantidade'],
                        textposition='top center',
                        hovertemplate="<b>%{x|%d/%m/%Y}</b><br>Tipo: " + tipo + "<br>Qtd: %{y}<extra></extra>"
                    ))

                # 7. Configurações visuais do gráfico
                fig_hist.update_layout(
                    title='Evolução do Efetivo Presente por Tipo de MO (Status = 1)',
                    xaxis_title='Data',
                    yaxis_title='Quantidade de Funcionários',
                    legend_title='Tipo de MO',
                    hovermode='x unified',
                    hoverlabel=dict(
                        bgcolor="white",
                        font_size=16,
                        font_family="Arial"
                    ),
                    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
                    margin=dict(t=80, b=40, l=40, r=40)
                )

                st.plotly_chart(fig_hist, width='stretch')

        else:
            # Fallback: gráfico único caso o cadastro não esteja disponível
            df_hist_count = (
                df_hist.groupby('Data')['Matricula']
                .nunique()
                .reset_index(name='Quantidade')
            )
            intervalo_datas = pd.date_range(start=d_ini, end=d_fim)
            df_full = pd.DataFrame({'Data': intervalo_datas})
            df_hist_count['Data'] = pd.to_datetime(df_hist_count['Data'])
            df_full = (
                df_full
                .merge(df_hist_count, on='Data', how='left')
                .fillna(0)
            )
            df_full['Quantidade'] = df_full['Quantidade'].astype(int)
            fig_hist = px.line(
                df_full,
                x='Data',
                y='Quantidade',
                title='Evolução do Efetivo Presente',
                markers=True,
                line_shape='spline',
                text='Quantidade'
            )
            fig_hist.update_traces(
                line=dict(width=2.5, color='#2563EB'),
                marker=dict(size=8, color='#1E3A8A'),
                textposition='top center'
            )
            st.plotly_chart(fig_hist, width='stretch')


        st.markdown("---")
        st.markdown("### 📋 Status do Dia")
        data_recente = df_ef['Data'].max()
        df_recente = df_ef[df_ef['Data'] == data_recente]
        if sit_filtro != "TODAS": df_recente = df_recente[df_recente['Situacao'] == sit_filtro]
        if not df_recente.empty:
            df_status_dia = df_recente.groupby('Situacao').size().reset_index(name='Total')
            col_graf, col_tab = st.columns([1, 1])
            with col_graf:
                fig_status = px.bar(df_status_dia, y='Situacao', x='Total', orientation='h', title=f"Distribuição Status - {data_recente.strftime('%d/%m/%Y')}", color_discrete_sequence=['#000000'], text_auto=True)
                sel_status = st.plotly_chart(fig_status, width='stretch', on_select="rerun")
            with col_tab:
                if sel_status and "selection" in sel_status and "points" in sel_status["selection"] and sel_status["selection"]["points"]:
                    sit_filtrada = sel_status["selection"]["points"][0]["y"]
                    st.markdown(f"#### Detalhes: {sit_filtrada}")
                    df_detalhe = df_recente[df_recente['Situacao'] == sit_filtrada]
                    dados_func = db.get_funcionarios()
                    dict_abrev = {str(f[0]): (f[3].upper() if f[3] else f[2].upper()) for _, f in dados_func.iterrows()}
                    df_detalhe['Abrev'] = df_detalhe['Matricula'].astype(str).map(dict_abrev).fillna(df_detalhe['Funcao'])
                    for a in sorted(df_detalhe['Abrev'].unique()):
                        with st.expander(f"🔸 {a}"):
                            for n in df_detalhe[df_detalhe['Abrev'] == a]['Nome'].tolist(): st.write(f"- {n}")
                else: st.info("Clique sobre o status para visualizar o efetivo.")
    else: st.info("Nenhum dado de efetivo diário carregado.")

# --- ABA 1: NOVO COLABORADOR / DASH EFETIVO ---
with aba_view[1]:
    if st.session_state.logged_in:
        st.subheader("➕ Cadastro de Novo Colaborador")
        funcoes_disponiveis = db.get_funcoes()
        with st.form(key=f"form_novo_colab_{st.session_state.form_key}"):
            c1, c2 = st.columns(2)
            with c1:
                mat = st.text_input("Matrícula *",autocomplete='off')
                nome = st.text_input("Nome Completo *",autocomplete='off')
                func = st.selectbox("Função/Cargo *", funcoes_disponiveis)
            with c2:
                abrev = st.text_input("Abreviação",autocomplete='off')
                adm = st.date_input("Data de Admissão")
                mo = st.selectbox("Tipo de MO", ["MOD", "MOI"])
                status = st.selectbox("Status", ["Ativo", "Inativo"])
            if st.form_submit_button("CADASTRAR COLABORADOR"):
                if mat and nome:
                    success, msg = db.add_funcionario(mat, nome, func, abrev, adm, mo, status, st.session_state.user_name)
                    if success: st.success("Cadastrado!"); reset_form(); time.sleep(0.5); st.rerun()
                    else: st.error(f"Erro: {msg}")
                else: st.error("Preencha os campos obrigatórios.")
    else:
        st.subheader("📊 Dashboard de Efetivo")
        df = db.get_funcionarios()
        if df is not None and not df.empty:
            m1, m2, m3 = st.columns(3)
            total_geral = len(df)
            total_ativos = len(df[df['status'] == 'Ativo'])
            total_inativos = len(df[df['status'] == 'Inativo'])
            
            with m1:
                st.markdown(f"""
                <div class='metric-card'>
                    <div class='metric-icon' style='color: #1E3A8A; background: #DBEAFE;'>👥</div>
                    <h3>Total Efetivo</h3>
                    <h2 style='color: #1E3A8A;'>{total_geral}</h2>
                </div>
                """, unsafe_allow_html=True)
            with m2:
                st.markdown(f"""
                <div class='metric-card'>
                    <div class='metric-icon' style='color: #15803D; background: #DCFCE7;'>✅</div>
                    <h3>Ativos na Obra</h3>
                    <h2 style='color: #15803D;'>{total_ativos}</h2>
                </div>
                """, unsafe_allow_html=True)
            with m3:
                st.markdown(f"""
                <div class='metric-card'>
                    <div class='metric-icon' style='color: #B91C1C; background: #FEE2E2;'>🚫</div>
                    <h3>Inativos</h3>
                    <h2 style='color: #B91C1C;'>{total_inativos}</h2>
                </div>
                """, unsafe_allow_html=True)
                     
            
            df_ativos = df[df['status'] == 'Ativo'].copy()
            if df_ativos is not None and not df_ativos.empty:
                df_ativos['Abrev_Upper'] = df_ativos['abrev'].fillna(df_ativos['funcao']).astype(str).str.upper()
                counts = df_ativos['Abrev_Upper'].value_counts().reset_index()
                counts.columns = ['Função', 'Quantidade']
                fig = px.bar(counts, x='Função', y='Quantidade', title="Efetivo por Função (Ativos)", color_discrete_sequence=['#FFD700'], text_auto=True)
                fig.update_layout(
                    xaxis_tickangle = -45
                )
                
                st.plotly_chart(fig, width='stretch')

# --- ABA 2: APONTAR HORAS / DASH PRODUTIVIDADE ---
with aba_view[2]:
    if st.session_state.logged_in:
        st.subheader("✍️ Novo Apontamento Diário")
        df_func = db.get_funcionarios()
        mats = df_func['matricula'].tolist() if not df_func.empty else []
        equipamentos_disp = db.get_equipamentos()
        with st.form(key=f"form_apont_horas_{st.session_state.form_key}"):
            c1, c2, c3 = st.columns(3)
            with c1:
                sel_mat = st.selectbox("Matrícula Colaborador *", [""] + mats)
                func_info = df_func[df_func['matricula'] == sel_mat].iloc[0] if sel_mat and not df_func.empty else None
                nome_auto = func_info['nome'] if func_info is not None else ""
                funcao_auto = func_info['funcao'] if func_info is not None else ""
                st.text_input("Nome", value=nome_auto, disabled=True,autocomplete='off')
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
                    total_float = horas_para_decimal(total_h)
                    carga_dia = db.get_carga_dia(data_ap)
                    if extra_100: h_norm, h_extra = 0, total_float
                    else:
                        h_extra = max(0, total_float - carga_dia)
                        h_norm = total_float - h_extra
                    success, msg = db.add_apontamento(sel_mat, nome_auto, funcao_auto, equip, ativ, ent, s_alm, r_alm, s_fin, total_h, h_norm, h_extra, data_ap, st.session_state.user_name, considerar_100_extra=extra_100)
                    if success: st.success("Registrado!"); reset_form(); time.sleep(0.5); st.rerun()
                    else: st.error(f"Erro: {msg}")
                else: st.warning("Preencha os campos obrigatórios.")
    else:
        st.subheader("📈 Dashboard de Produtividade Dinâmico")
        df_ap = db.get_apontamentos()
        if df_ap is not None and not df_ap.empty:
            df_ap['data'] = pd.to_datetime(df_ap['data'])
            df_ap['Horas_Dec'] = df_ap['total'].apply(horas_para_decimal)
            df_ap['Mes_Ano'] = df_ap['data'].dt.strftime('%m/%Y')
            meses_disp = sorted(df_ap['Mes_Ano'].unique(), reverse=True)
            mes_sel = st.selectbox("Mês de Referência", meses_disp, key="pub_mes_sel")
            df_mes = df_ap[df_ap['Mes_Ano'] == mes_sel]
            df_func_prod = df_mes.groupby('funcao')['Horas_Dec'].sum().reset_index().sort_values('Horas_Dec', ascending=False)
            fig_func = px.bar(df_func_prod, x='funcao', y='Horas_Dec', title="Produtividade por Função (Horas)", color_discrete_sequence=['#1E3A8A'], text_auto=True)
            sel_func = st.plotly_chart(fig_func, width='stretch', on_select="rerun")
            df_equip_filtered = df_mes.copy()
            if sel_func and "selection" in sel_func and "points" in sel_func["selection"] and sel_func["selection"]["points"]:
                func_filtrada = sel_func["selection"]["points"][0]["x"]
                df_equip_filtered = df_equip_filtered[df_equip_filtered['funcao'] == func_filtrada]                
            df_equip_prod = df_equip_filtered.groupby('equipamento')['Horas_Dec'].sum().reset_index().sort_values('Horas_Dec', ascending=False)
            fig_equip = px.bar(df_equip_prod, x='equipamento', y='Horas_Dec', title="Produtividade por Equipamento (Horas)", color_discrete_sequence=['#2563EB'], text_auto=True)
            st.plotly_chart(fig_equip, width='stretch')

# --- ABA 3: DASH EFETIVO / CONSULTA GERAL ---
with aba_view[3]:
    if st.session_state.logged_in:
        st.subheader("📊 Dashboard de Efetivo")
        df = db.get_funcionarios()
        if df is not None and not df.empty:
            m1, m2, m3 = st.columns(3)
            total_geral = len(df)
            total_ativos = len(df[df['status'] == 'Ativo'])
            total_inativos = len(df[df['status'] == 'Inativo'])
            
            with m1:
                st.markdown(f"""
                <div class='metric-card'>
                    <div class='metric-icon' style='color: #1E3A8A; background: #DBEAFE;'>👥</div>
                    <h3>Total Efetivo</h3>
                    <h2 style='color: #1E3A8A;'>{total_geral}</h2>
                </div>
                """, unsafe_allow_html=True)
            with m2:
                st.markdown(f"""
                <div class='metric-card'>
                    <div class='metric-icon' style='color: #15803D; background: #DCFCE7;'>✅</div>
                    <h3>Ativos na Obra</h3>
                    <h2 style='color: #15803D;'>{total_ativos}</h2>
                </div>
                """, unsafe_allow_html=True)
            with m3:
                st.markdown(f"""
                <div class='metric-card'>
                    <div class='metric-icon' style='color: #B91C1C; background: #FEE2E2;'>🚫</div>
                    <h3>Inativos</h3>
                    <h2 style='color: #B91C1C;'>{total_inativos}</h2>
                </div>
                """, unsafe_allow_html=True)
            
            df_ativos = df[df['status'] == 'Ativo'].copy()
            if df_ativos is not None and not df_ativos.empty:
                df_ativos['Abrev_Upper'] = df_ativos['abrev'].fillna(df_ativos['funcao']).astype(str).str.upper()
                counts = df_ativos['Abrev_Upper'].value_counts().reset_index()
                counts.columns = ['Função', 'Quantidade']
                fig = px.bar(counts, x='Função', y='Quantidade', title="Efetivo por Função (Ativos)", color_discrete_sequence=['#FFD700'], text_auto=True)
                fig.update_layout(xaxis_tickangle = -45)
                st.plotly_chart(fig, width='stretch')
    else:
        st.subheader("📖 Consulta de Efetivo")
        df = db.get_funcionarios()
        if df is not None and not df.empty:
            col_f1, col_f2, col_f3 = st.columns(3)
            with col_f1: f_nome = st.text_input("Buscar por Nome", key="pub_f_nome")
            with col_f2: f_mat = st.text_input("Buscar por Matrícula", key="pub_f_mat")
            with col_f3: f_func = st.text_input("Buscar por Função", key="pub_f_func")
            df_f = df.copy()
            if f_nome: df_f = df_f[df_f["nome"].str.contains(f_nome, case=False, na=False)]
            if f_mat: df_f = df_f[df_f["matricula"].astype(str).str.contains(f_mat, case=False, na=False)]
            if f_func: df_f = df_f[df_f["funcao"].str.contains(f_func, case=False, na=False)]
            st.dataframe(df_f.map(lambda x: str(x).upper() if pd.notnull(x) else x), width='stretch')

# --- ABA 4: DASH PRODUTIVIDADE DINÂMICO / REGISTRO DE HORAS ---
with aba_view[4]:
    if st.session_state.logged_in:
        st.subheader("📈 Dashboard de Produtividade Dinâmico")
        df_ap = db.get_apontamentos()
        if df_ap is not None and not df_ap.empty:
            df_ap['data'] = pd.to_datetime(df_ap['data'])
            df_ap['Horas_Dec'] = df_ap['total'].apply(horas_para_decimal)
            df_ap['Mes_Ano'] = df_ap['data'].dt.strftime('%m/%Y')
            meses_disp = sorted(df_ap['Mes_Ano'].unique(), reverse=True)
            mes_sel = st.selectbox("Mês de Referência", meses_disp, key="dyn_mes_sel")
            df_mes = df_ap[df_ap['Mes_Ano'] == mes_sel]
            df_func_prod = df_mes.groupby('funcao')['Horas_Dec'].sum().reset_index().sort_values('Horas_Dec', ascending=False)
            fig_func = px.bar(df_func_prod, x='funcao', y='Horas_Dec', title="Produtividade por Função (Horas)", color_discrete_sequence=['#1E3A8A'], text_auto=True)
            sel_func = st.plotly_chart(fig_func, width='stretch', on_select="rerun")
            df_equip_filtered = df_mes.copy()
            if sel_func and "selection" in sel_func and "points" in sel_func["selection"] and sel_func["selection"]["points"]:
                func_filtrada = sel_func["selection"]["points"][0]["x"]
                df_equip_filtered = df_equip_filtered[df_equip_filtered['funcao'] == func_filtrada]                
            df_equip_prod = df_equip_filtered.groupby('equipamento')['Horas_Dec'].sum().reset_index().sort_values('Horas_Dec', ascending=False)
            fig_equip = px.bar(df_equip_prod, x='equipamento', y='Horas_Dec', title="Produtividade por Equipamento (Horas)", color_discrete_sequence=['#2563EB'], text_auto=True)
            st.plotly_chart(fig_equip, width='stretch')
    else:
        st.subheader("⏱️ Registros de Horas Detalhados")
        df_ap_full = db.get_apontamentos_com_id()
        if df_ap_full is not None and not df_ap_full.empty:
            st.dataframe(df_ap_full.head(100), width='stretch')
            st.info("💡 A exclusão de registros é permitida apenas para administradores.")

# --- ABA 5: CONSULTA GERAL / PLUVIOMETRIA ---
with aba_view[5]:
    if st.session_state.logged_in:
        st.subheader("📖 Consulta de Efetivo Completa")
        df = db.get_funcionarios()
        if df is not None and not df.empty:
            excel_data = converter_df_para_excel(df)
            st.download_button(label="📥 Exportar para Excel", data=excel_data, file_name=f"efetivo_{now_br.strftime('%Y%m%d')}.xlsx")
            col_f1, col_f2, col_f3 = st.columns(3)
            with col_f1: f_nome = st.text_input("Buscar por Nome", key="log_f_nome")
            with col_f2: f_mat = st.text_input("Buscar por Matrícula", key="log_f_mat")
            with col_f3: f_func = st.text_input("Buscar por Função", key="log_f_func")
            df_f = df.copy()
            if f_nome: df_f = df_f[df_f["nome"].str.contains(f_nome, case=False, na=False)]
            if f_mat: df_f = df_f[df_f["matricula"].astype(str).str.contains(f_mat, case=False, na=False)]
            if f_func: df_f = df_f[df_f["funcao"].str.contains(f_func, case=False, na=False)]
            st.dataframe(df_f.map(lambda x: str(x).upper() if pd.notnull(x) else x), width='stretch')
    else:
        render_pluviometria("pub")

# --- ABA 6: REGISTRO DE HORAS / HISTÓRICO CHUVA ---
with aba_view[6]:
    if st.session_state.logged_in:
        st.subheader("⏱️ Registros de Horas Detalhados")
        df_ap_full = db.get_apontamentos_com_id()
        if df_ap_full is not None and not df_ap_full.empty:
            st.dataframe(df_ap_full.head(100), width='stretch')
            with st.expander("🗑️ Excluir Registros"):
                sel_excluir = st.multiselect("Selecione os IDs para remover", df_ap_full['id'].tolist())
                if st.button("EXCLUIR SELECIONADOS"):
                    if st.session_state.user_name == 'admin':
                        for s in sel_excluir: db.delete_apontamento_por_id(s, st.session_state.user_name)
                        st.success("Excluído!"); time.sleep(0.5); st.rerun()
                    else: st.error("Apenas o administrador pode excluir registros.")
    else:
        st.subheader("🌧️ Histórico de Pluviometria")
        c1, c2 = st.columns(2)
        d_ini_p = c1.date_input("Início", value=get_now_br().date() - timedelta(days=7), key="h_ini_pub")
        d_fim_p = c2.date_input("Fim", value=get_now_br().date(), key="h_fim_pub")
        df_h = db.get_pluviometria_periodo(d_ini_p, d_fim_p)
        if df_h is not None and not df_h.empty:
            df_h['data'] = pd.to_datetime(df_h['data'])
            fig_p = px.bar(df_h.groupby('data')['chuva_mm'].sum().reset_index(), x='data', y='chuva_mm', title="Total Diário de Chuva", text_auto=True)
            st.plotly_chart(fig_p, width='stretch')

# Abas exclusivas de Gestão (Logado)
if st.session_state.logged_in:
    with aba_view[7]:
        st.subheader("⚙️ Gestão de Funções")
        c1, c2 = st.columns([2, 1])
        funcoes = db.get_funcoes()
        with c1: st.table(pd.DataFrame(funcoes, columns=["Função"]))
        with c2:
            n_f = st.text_input("Nova Função")
            if st.button("SALVAR FUNÇÃO"):
                if n_f: db.add_funcao(n_f, st.session_state.user_name); st.success("Salvo!"); st.rerun()
            f_del = st.selectbox("Remover Função", [""] + funcoes)
            if st.button("EXCLUIR FUNÇÃO"):
                if f_del: db.delete_funcao(f_del, st.session_state.user_name); st.success("Removido!"); st.rerun()

    with aba_view[8]:
        st.subheader("🚜 Gestão de Equipamentos")
        c1, c2 = st.columns([2, 1])
        equips = db.get_equipamentos()
        with c1: st.table(pd.DataFrame(equips, columns=["Equipamento"]))
        with c2:
            n_e = st.text_input("Novo Equipamento")
            if st.button("SALVAR EQUIPAMENTO"):
                if n_e: db.add_equipamento(n_e, st.session_state.user_name); st.success("Salvo!"); st.rerun()
            e_del = st.selectbox("Remover Equipamento", [""] + equips)
            if st.button("EXCLUIR EQUIPAMENTO"):
                if e_del: db.delete_equipamento(e_del, st.session_state.user_name); st.success("Removido!"); st.rerun()

    with aba_view[9]:
        st.subheader("✏️ Atualizar Cadastro")
        df_func = db.get_funcionarios()
        if df_func is not None and not df_func.empty:
            mats = df_func['matricula'].tolist()
            s_m = st.selectbox("Selecione a Matrícula", mats, key="upd_sel_mat")
            f_d = df_func[df_func['matricula'] == s_m].iloc[0]
            with st.form(key=f"form_upd_{st.session_state.form_key}"):
                u_n = st.text_input("Nome", value=f_d['nome'])
                u_f = st.selectbox("Função", db.get_funcoes(), index=0)
                u_a = st.text_input("Abreviação", value=f_d['abrev'])
                u_d = st.date_input("Admissão", value=pd.to_datetime(f_d['admissao']).date())
                u_mo = st.selectbox("MO", ["MOD", "MOI"], index=0 if f_d['mo'] == "MOD" else 1)
                u_st = st.selectbox("Status", ["Ativo", "Inativo"], index=0 if f_d['status'] == "Ativo" else 1)
                if st.form_submit_button("SALVAR ALTERAÇÕES"):
                    db.update_funcionario(s_m, u_n, u_f, u_a, u_d, u_mo, u_st, st.session_state.user_name)
                    st.success("Atualizado!"); reset_form(); time.sleep(0.5); st.rerun()

    with aba_view[10]:
        st.subheader("🗑️ Remover Colaborador")
        df_func = db.get_funcionarios()
        if df_func is not None and not df_func.empty:
            d_m = st.selectbox("Excluir Matrícula Definitivamente", df_func['matricula'].tolist())
            if st.button("CONFIRMAR EXCLUSÃO"):
                db.delete_funcionario(d_m, st.session_state.user_name); st.success("Removido!"); time.sleep(0.5); st.rerun()

    with aba_view[11]:
        st.subheader("👥 Gestão de Usuários")
        with st.form("novo_usuario"):
            n_u = st.text_input("Novo Usuário")
            n_p = st.text_input("Senha", type="password")
            if st.form_submit_button("CRIAR USUÁRIO"):
                if n_u and n_p: db.add_usuario(n_u, n_p, st.session_state.user_name); st.success("Criado!"); st.rerun()
        usuarios = db.get_usuarios()
        u_del = st.selectbox("Remover Usuário", [u for u in usuarios if u != 'admin'])
        if st.button("EXCLUIR USUÁRIO"):
            db.delete_usuario(u_del, st.session_state.user_name); st.success("Removido!"); st.rerun()

    with aba_view[12]:
        st.subheader("🔍 Auditoria")
        df_logs = db.get_logs()
        if not df_logs.empty: st.dataframe(df_logs, width='stretch')
        else: st.info("Nenhum log registrado.")

    with aba_view[-2]:
        # Botão salvar foi movido para dentro da função render_pluviometria para alinhamento superior
        render_pluviometria("log")

    with aba_view[-1]:
        st.subheader("🌧️ Histórico de Pluviometria")
        c1, c2 = st.columns(2)
        d_ini_p = c1.date_input("Início", value=get_now_br().date() - timedelta(days=7), key="h_ini_log")
        d_fim_p = c2.date_input("Fim", value=get_now_br().date(), key="h_fim_log")
        df_h = db.get_pluviometria_periodo(d_ini_p, d_fim_p)
        if df_h is not None and not df_h.empty:
            df_h['data'] = pd.to_datetime(df_h['data'])
            fig_p = px.bar(df_h.groupby('data')['chuva_mm'].sum().reset_index(), x='data', y='chuva_mm', title="Total Diário de Chuva", text_auto=True)
            st.plotly_chart(fig_p, width='stretch')

st.sidebar.markdown("---")
st.sidebar.markdown("<div class='sidebar-footer'><b>GRUPO SANTIN</b><br>Sistema Corporativo de Controle de Obras<br>Business Intelligence • Engenharia • Gestão de Projetos</div>", unsafe_allow_html=True)
#st.sidebar.info("Sistema de Gestão de Obras v2.0")
st.sidebar.markdown(
    "<div style='margin-top:60px'></div>",
    unsafe_allow_html=True
)

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
