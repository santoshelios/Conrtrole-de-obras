import psycopg2
from psycopg2 import extras
import streamlit as st
from datetime import datetime, date

# --- CONFIGURAÇÃO DE CONEXÃO (SUPABASE) ---
def get_connection():
    """Conexão ultra-resiliente com múltiplos fallbacks."""
    # 1. Tenta segredos do Streamlit
    try:
        if "database" in st.secrets:
            return psycopg2.connect(st.secrets["database"]["url"])
    except:
        pass
        
    # 2. Tenta Pooler (Porta 6543) - Mais estável para Web
    try:
        url_pooler = "postgresql://postgres.pzqutgzekgffqlwkmsst:Hss90352806amora@aws-0-sa-east-1.pooler.supabase.com:6543/postgres?sslmode=require"
        return psycopg2.connect(url_pooler)
    except:
        # 3. Tenta Conexão Direta (Porta 5432)
        try:
            url_direct = "postgresql://postgres:Hss90352806amora@db.pzqutgzekgffqlwkmsst.supabase.co:5432/postgres"
            return psycopg2.connect(url_direct)
        except Exception as e:
            st.error(f"Erro de conexão com o banco de dados: {e}")
            return None

def init_db():
    """Garante que as tabelas existam e o RLS esteja desativado (UNRESTRICTED)."""
    conn = get_connection()
    if not conn: return
    try:
        conn.autocommit = True
        c = conn.cursor()
        
        # Criação das tabelas
        c.execute('''CREATE TABLE IF NOT EXISTS funcionarios (
                        matricula TEXT PRIMARY KEY, nome TEXT, funcao TEXT, abrev TEXT,
                        admissao DATE, mo TEXT, status TEXT)''')
        
        c.execute('''CREATE TABLE IF NOT EXISTS apontamentos (
                        id SERIAL PRIMARY KEY, matricula TEXT, nome TEXT, funcao TEXT,
                        equipamento TEXT, atividade TEXT, entrada TEXT, saida_alm TEXT,
                        retorno_alm TEXT, saida_fin TEXT, total TEXT, data DATE)''')
        
        c.execute('CREATE TABLE IF NOT EXISTS funcoes (nome TEXT PRIMARY KEY)')
        c.execute('CREATE TABLE IF NOT EXISTS equipamentos (nome TEXT PRIMARY KEY)')
        
        c.execute('''CREATE TABLE IF NOT EXISTS efetivo_diario (
                        id SERIAL PRIMARY KEY, data DATE, matricula TEXT, nome TEXT,
                        funcao TEXT, status_val INTEGER, situacao TEXT)''')
        
        c.execute('CREATE TABLE IF NOT EXISTS usuarios (username TEXT PRIMARY KEY, password TEXT)')
        
        # Desativa RLS para manter status UNRESTRICTED
        for t in ['funcionarios', 'apontamentos', 'funcoes', 'equipamentos', 'efetivo_diario', 'usuarios']:
            try: c.execute(f"ALTER TABLE {t} DISABLE ROW LEVEL SECURITY;")
            except: pass
            
        c.execute("INSERT INTO usuarios (username, password) VALUES ('admin', '1234') ON CONFLICT DO NOTHING")
        conn.close()
    except Exception as e:
        print(f"Erro init_db: {e}")

# --- FUNÇÕES DE FUNCIONÁRIOS ---
def add_funcionario(mat, nome, func, abrev, adm, mo, status):
    conn = get_connection()
    if not conn: return False, "Sem conexão"
    try:
        c = conn.cursor()
        # Converte data para string se necessário
        d_adm = adm.strftime('%Y-%m-%d') if isinstance(adm, (date, datetime)) else adm
        c.execute("INSERT INTO funcionarios (matricula, nome, funcao, abrev, admissao, mo, status) VALUES (%s, %s, %s, %s, %s, %s, %s) ON CONFLICT (matricula) DO UPDATE SET nome=EXCLUDED.nome, funcao=EXCLUDED.funcao, abrev=EXCLUDED.abrev, admissao=EXCLUDED.admissao, mo=EXCLUDED.mo, status=EXCLUDED.status", 
                 (str(mat), nome, func, abrev, d_adm, mo, status))
        conn.commit()
        conn.close()
        return True, ""
    except Exception as e:
        return False, str(e)

def get_funcionarios():
    conn = get_connection()
    if not conn: return []
    try:
        c = conn.cursor()
        c.execute("SELECT matricula, nome, funcao, abrev, admissao, mo, status FROM funcionarios ORDER BY nome")
        data = c.fetchall()
        conn.close()
        # Converte datas para string para evitar erro no st.date_input do app_final
        result = []
        for r in data:
            row = list(r)
            if isinstance(row[4], (date, datetime)):
                row[4] = row[4].strftime('%Y-%m-%d')
            result.append(row)
        return result
    except: return []

def update_funcionario(mat, nome, func, abrev, adm, mo, status):
    conn = get_connection()
    if not conn: return False
    try:
        c = conn.cursor()
        d_adm = adm.strftime('%Y-%m-%d') if isinstance(adm, (date, datetime)) else adm
        c.execute("UPDATE funcionarios SET nome=%s, funcao=%s, abrev=%s, admissao=%s, mo=%s, status=%s WHERE matricula=%s",
                 (nome, func, abrev, d_adm, mo, status, str(mat)))
        conn.commit()
        conn.close()
        return True
    except: return False

def delete_funcionario(mat):
    conn = get_connection()
    if not conn: return False
    try:
        c = conn.cursor()
        c.execute("DELETE FROM funcionarios WHERE matricula=%s", (str(mat),))
        conn.commit()
        conn.close()
        return True
    except: return False

# --- FUNÇÕES DE APONTAMENTOS ---
def add_apontamento(mat, nome, func, equip, ativ, ent, s_a, r_a, s_f, total, data):
    conn = get_connection()
    if not conn: return False
    try:
        c = conn.cursor()
        d_ap = data.strftime('%Y-%m-%d') if isinstance(data, (date, datetime)) else data
        c.execute("INSERT INTO apontamentos (matricula, nome, funcao, equipamento, atividade, entrada, saida_alm, retorno_alm, saida_fin, total, data) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)",
                 (str(mat), nome, func, equip, ativ, str(ent), str(s_a), str(r_a), str(s_f), total, d_ap))
        conn.commit()
        conn.close()
        return True
    except: return False

def get_apontamentos():
    conn = get_connection()
    if not conn: return []
    try:
        c = conn.cursor()
        c.execute("SELECT matricula, nome, funcao, equipamento, atividade, entrada, saida_alm, retorno_alm, saida_fin, total, data FROM apontamentos ORDER BY data DESC")
        data = c.fetchall()
        conn.close()
        return [list(r) for r in data]
    except: return []

def get_apontamentos_com_id():
    conn = get_connection()
    if not conn: return []
    try:
        c = conn.cursor()
        c.execute("SELECT id, matricula, nome, funcao, equipamento, atividade, entrada, saida_alm, retorno_alm, saida_fin, total, data FROM apontamentos ORDER BY data DESC")
        data = c.fetchall()
        conn.close()
        return [list(r) for r in data]
    except: return []

def delete_apontamento_por_id(id_ap):
    conn = get_connection()
    if not conn: return False
    try:
        c = conn.cursor()
        c.execute("DELETE FROM apontamentos WHERE id=%s", (id_ap,))
        conn.commit()
        conn.close()
        return True
    except: return False

# --- FUNÇÕES DE APOIO ---
def get_funcoes():
    conn = get_connection()
    if not conn: return []
    try:
        c = conn.cursor()
        c.execute("SELECT nome FROM funcoes ORDER BY nome")
        data = [r[0] for r in c.fetchall()]
        conn.close()
        return data
    except: return []

def add_funcao(nome):
    if not nome: return False
    conn = get_connection()
    if not conn: return False
    try:
        c = conn.cursor()
        c.execute("INSERT INTO funcoes VALUES (%s) ON CONFLICT DO NOTHING", (nome.strip().upper(),))
        conn.commit()
        conn.close()
        return True
    except: return False

def delete_funcao(nome):
    conn = get_connection()
    if not conn: return False
    try:
        c = conn.cursor()
        c.execute("DELETE FROM funcoes WHERE nome=%s", (nome,))
        conn.commit()
        conn.close()
        return True
    except: return False

def get_equipamentos():
    conn = get_connection()
    if not conn: return []
    try:
        c = conn.cursor()
        c.execute("SELECT nome FROM equipamentos ORDER BY nome")
        data = [r[0] for r in c.fetchall()]
        conn.close()
        return data
    except: return []

def add_equipamento(nome):
    if not nome: return False
    conn = get_connection()
    if not conn: return False
    try:
        c = conn.cursor()
        c.execute("INSERT INTO equipamentos VALUES (%s) ON CONFLICT DO NOTHING", (nome.strip().upper(),))
        conn.commit()
        conn.close()
        return True
    except: return False

def delete_equipamento(nome):
    conn = get_connection()
    if not conn: return False
    try:
        c = conn.cursor()
        c.execute("DELETE FROM equipamentos WHERE nome=%s", (nome,))
        conn.commit()
        conn.close()
        return True
    except: return False

# --- EFETIVO DIÁRIO ---
def add_efetivo_diario_batch(df):
    conn = get_connection()
    if not conn: return False
    try:
        c = conn.cursor()
        for _, row in df.iterrows():
            d_ef = row['Data'].strftime('%Y-%m-%d') if isinstance(row['Data'], (date, datetime, pd.Timestamp)) else row['Data']
            c.execute("INSERT INTO efetivo_diario (data, matricula, nome, funcao, status_val, situacao) VALUES (%s, %s, %s, %s, %s, %s)",
                     (d_ef, str(row['Matricula']), row['Nome'], row['Funcao'], int(row['Status']), row['Situacao']))
        conn.commit()
        conn.close()
        return True
    except: return False

def get_efetivo_diario():
    conn = get_connection()
    if not conn: return []
    try:
        c = conn.cursor()
        c.execute("SELECT data, matricula, nome, funcao, status_val, situacao FROM efetivo_diario ORDER BY data DESC")
        data = c.fetchall()
        conn.close()
        return [list(r) for r in data]
    except: return []

def delete_efetivo_por_data(data):
    conn = get_connection()
    if not conn: return False
    try:
        c = conn.cursor()
        d_del = data.strftime('%Y-%m-%d') if isinstance(data, (date, datetime)) else data
        c.execute("DELETE FROM efetivo_diario WHERE data=%s", (d_del,))
        conn.commit()
        conn.close()
        return True
    except: return False

# --- USUÁRIOS ---
def add_usuario(user, pwd):
    conn = get_connection()
    if not conn: return False
    try:
        c = conn.cursor()
        c.execute("INSERT INTO usuarios VALUES (%s, %s)", (user, pwd))
        conn.commit()
        conn.close()
        return True
    except: return False

def check_login(user, pwd):
    conn = get_connection()
    if not conn: return False
    try:
        c = conn.cursor()
        c.execute("SELECT * FROM usuarios WHERE username=%s AND password=%s", (user, pwd))
        data = c.fetchone()
        conn.close()
        return data is not None
    except: return False

def get_usuarios():
    conn = get_connection()
    if not conn: return []
    try:
        c = conn.cursor()
        c.execute("SELECT username FROM usuarios")
        data = [r[0] for r in c.fetchall()]
        conn.close()
        return data
    except: return []

def delete_usuario(user):
    if user == 'admin': return False
    conn = get_connection()
    if not conn: return False
    try:
        c = conn.cursor()
        c.execute("DELETE FROM usuarios WHERE username=%s", (user,))
        conn.commit()
        conn.close()
        return True
    except: return False

# Inicialização automática
init_db()
