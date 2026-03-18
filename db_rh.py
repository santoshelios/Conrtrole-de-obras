import psycopg2
import pandas as pd
from datetime import datetime, timedelta, time

# =========================
# CONEXÃO SUPABASE (POSTGRESQL)
# =========================

DB_URL = "postgresql://postgres.pzqutgzekgffqlwkmsst:MvjDgb3oWeC1n5n@aws-1-us-east-2.pooler.supabase.com:5432/postgres"

def get_connection():
    try:
        conn = psycopg2.connect(DB_URL)
        return conn
    except Exception as e:
        print("Erro conexão:", e)
        return None

# =========================
# QUERY PADRÃO
# =========================

def run_query(sql, params=None):
    conn = get_connection()
    if not conn:
        return pd.DataFrame()
    try:
        df = pd.read_sql(sql, conn, params=params)
        return df
    except Exception as e:
        print("ERRO QUERY:", e)
        return pd.DataFrame()
    finally:
        conn.close()

def execute_non_query(sql, params=None, action="", table="", user=""):
    conn = get_connection()
    if not conn:
        return False, "Erro de conexão"
    try:
        cur = conn.cursor()
        cur.execute(sql, params)
        conn.commit()
        if action and table:
            add_log(user, action, table, str(params))
        return True, "Sucesso"
    except Exception as e:
        print(f"ERRO EXECUTE: {e}")
        return False, str(e)
    finally:
        conn.close()

# =========================
# LOGS / AUDITORIA
# =========================

def add_log(usuario, acao, tabela, detalhes):
    sql = "INSERT INTO logs_auditoria (usuario, acao, tabela, detalhes, data_hora) VALUES (%s, %s, %s, %s, %s)"
    now = datetime.now()
    execute_non_query(sql, (usuario, acao, tabela, detalhes, now))

def get_logs():
    return run_query("SELECT data_hora, usuario, acao, tabela, detalhes FROM logs_auditoria ORDER BY data_hora DESC LIMIT 500")

# =========================
# LOGIN E USUÁRIOS
# =========================

def check_login(user, password):
    sql = "SELECT * FROM usuarios WHERE username = %s AND password = %s"
    df = run_query(sql, (user, password))
    return not df.empty

def get_usuarios():
    df = run_query("SELECT username FROM usuarios ORDER BY username")
    return df['username'].tolist() if not df.empty else []

def add_usuario(user, pwd, usuario_admin):
    sql = "INSERT INTO usuarios (username, password) VALUES (%s, %s)"
    return execute_non_query(sql, (user, pwd), "INSERT", "usuarios", usuario_admin)

def delete_usuario(user, usuario_admin):
    sql = "DELETE FROM usuarios WHERE username=%s"
    return execute_non_query(sql, (user,), "DELETE", "usuarios", usuario_admin)

# =========================
# FUNCIONÁRIOS
# =========================

def get_funcionario_por_matricula(mat):
    sql = "SELECT matricula, nome, status, funcao FROM funcionarios WHERE matricula = %s"
    df = run_query(sql, (mat,))
    if not df.empty:
        return df.iloc[0].to_dict()
    return None

def get_funcionarios():
    return run_query("SELECT matricula, nome, funcao, abrev, admissao, mo, status FROM funcionarios ORDER BY nome")

def add_funcionario(mat, nome, func, abrev, adm, mo, status, usuario):
    sql = "INSERT INTO funcionarios (matricula, nome, funcao, abrev, admissao, mo, status) VALUES (%s, %s, %s, %s, %s, %s, %s)"
    return execute_non_query(sql, (mat, nome, func, abrev, adm, mo, status), "INSERT", "funcionarios", usuario)

def update_funcionario(mat, nome, func, abrev, adm, mo, status, usuario):
    sql = "UPDATE funcionarios SET nome=%s, funcao=%s, abrev=%s, admissao=%s, mo=%s, status=%s WHERE matricula=%s"
    return execute_non_query(sql, (nome, func, abrev, adm, mo, status, mat), "UPDATE", "funcionarios", usuario)

def delete_funcionario(mat, usuario):
    sql = "DELETE FROM funcionarios WHERE matricula=%s"
    return execute_non_query(sql, (mat,), "DELETE", "funcionarios", usuario)

# =========================
# FUNÇÕES E EQUIPAMENTOS
# =========================

def get_funcoes():
    df = run_query("SELECT nome FROM funcoes ORDER BY nome")
    return df['nome'].tolist() if not df.empty else []

def add_funcao(nome, usuario):
    sql = "INSERT INTO funcoes (nome) VALUES (%s)"
    return execute_non_query(sql, (nome,), "INSERT", "funcoes", usuario)

def delete_funcao(nome, usuario):
    sql = "DELETE FROM funcoes WHERE nome=%s"
    return execute_non_query(sql, (nome,), "DELETE", "funcoes", usuario)

def get_equipamentos():
    df = run_query("SELECT nome FROM equipamentos ORDER BY nome")
    return df['nome'].tolist() if not df.empty else []

def add_equipamento(nome, usuario):
    sql = "INSERT INTO equipamentos (nome) VALUES (%s)"
    return execute_non_query(sql, (nome,), "INSERT", "equipamentos", usuario)

def delete_equipamento(nome, usuario):
    sql = "DELETE FROM equipamentos WHERE nome=%s"
    return execute_non_query(sql, (nome,), "DELETE", "equipamentos", usuario)

# =========================
# UTILITÁRIOS DE TEMPO E CÁLCULOS
# =========================

def str_to_time(t_str):
    if not t_str or t_str == 'None': return None
    if isinstance(t_str, time): return t_str
    try:
        t_str = str(t_str)
        for fmt in ('%H:%M:%S', '%H:%M'):
            try:
                return datetime.strptime(t_str, fmt).time()
            except ValueError:
                continue
        return None
    except:
        return None

def diff_hours(t1, t2):
    if not t1 or not t2: return 0.0
    today = datetime.today()
    dt1 = datetime.combine(today, t1)
    dt2 = datetime.combine(today, t2)
    if dt2 < dt1:
        dt2 += timedelta(days=1)
    diff = dt2 - dt1
    return diff.total_seconds() / 3600.0

def get_feriados_2026():
    return ["2026-01-01", "2026-02-16", "2026-02-17", "2026-04-03", "2026-04-21", "2026-05-01", "2026-06-04", "2026-09-07", "2026-10-12", "2026-11-02", "2026-11-15", "2026-11-20", "2026-12-25"]

def is_feriado_ou_fds(data):
    if isinstance(data, str):
        dt_obj = datetime.strptime(data, '%Y-%m-%d').date()
        data_str = data
    else:
        dt_obj = data
        data_str = data.strftime('%Y-%m-%d')
    if dt_obj.weekday() >= 5: return True
    if data_str in get_feriados_2026(): return True
    return False

def get_carga_dia(data):
    if is_feriado_ou_fds(data): return 0
    return 8.8

# =========================
# APONTAMENTOS
# =========================

def get_apontamentos():
    return run_query("SELECT id, matricula, nome, funcao, equipamento, atividade, entrada, s_almoco, r_almoco, saida, total, data, status, horas_normais, horas_extra FROM apontamentos ORDER BY data DESC")

def get_apontamentos_com_id():
    return get_apontamentos()

def check_sobreposicao(mat, data, ent, saida, id_ignore=None):
    sql = "SELECT entrada, saida FROM apontamentos WHERE matricula = %s AND data = %s"
    if id_ignore: sql += f" AND id != {id_ignore}"
    df = run_query(sql, (mat, data))
    if df.empty: return False
    new_ent = str_to_time(ent)
    new_sai = str_to_time(saida)
    for _, row in df.iterrows():
        ex_ent = str_to_time(row['entrada'])
        ex_sai = str_to_time(row['saida'])
        if not ex_ent or not ex_sai: continue
        if new_ent < ex_sai and new_sai > ex_ent: return True
    return False

def add_apontamento(mat, nome, func_name, equip, ativ, ent, s_alm, r_alm, s_fin, total_h, h_norm, h_extra, data, usuario, considerar_100_extra=False):
    # 1 - Verificação de Status Inativo
    func = get_funcionario_por_matricula(mat)
    if not func: return False, "Colaborador não encontrado."
    if str(func['status']).strip().lower() in ['inativo', 'desligado']:
        return False, f"Erro: Colaborador {func['nome']} está INATIVO. Apontamento não permitido."
    
    t_ent = str_to_time(ent)
    t_s_alm = str_to_time(s_alm)
    t_r_alm = str_to_time(r_alm)
    t_sai = str_to_time(s_fin)
    
    # 2 - Verificação de Horário de Almoço
    if t_r_alm and t_s_alm and t_r_alm < t_s_alm:
        return False, "Erro: Retorno do Almoço não pode ser menor que Saída para Almoço."
    
    # 3 - Verificação de Sobreposição
    if check_sobreposicao(mat, data, ent, s_fin):
        return False, "Erro: Já existe um apontamento neste horário (Sobreposição)."
    
    # 4 - Inserção com horas_normais e horas_extra calculadas
    sql = """INSERT INTO apontamentos 
             (matricula, nome, funcao, equipamento, atividade, entrada, s_almoco, r_almoco, saida, total, horas_normais, horas_extra, data, status) 
             VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)"""
    params = (mat, func['nome'], func['funcao'], equip, ativ, str(ent), str(s_alm), str(r_alm), str(s_fin), total_h, h_norm, h_extra, data, 'Registrado')
    return execute_non_query(sql, params, "INSERT", "apontamentos", usuario)

def delete_apontamento_por_id(id_ap, usuario):
    sql = "DELETE FROM apontamentos WHERE id=%s"
    return execute_non_query(sql, (id_ap,), "DELETE", "apontamentos", usuario)

# =========================
# EFETIVO DIÁRIO
# =========================

def get_efetivo_diario():
    return run_query("SELECT data as \"Data\", matricula as \"Matricula\", nome as \"Nome\", funcao as \"Funcao\", status_val as \"Status_Val\", situacao as \"Situacao\" FROM efetivo_diario ORDER BY data DESC")

def add_efetivo_diario_batch(df, usuario):
    conn = get_connection()
    if not conn: return False
    try:
        cur = conn.cursor()
        data_to_insert = []
        for _, row in df.iterrows():
            data_val = row['Data']
            if hasattr(data_val, 'to_pydatetime'): data_val = data_val.to_pydatetime().date()
            elif hasattr(data_val, 'date'): data_val = data_val.date()
            
            data_to_insert.append((
                data_val, 
                str(row['Matricula']), 
                str(row['Nome']), 
                str(row['Funcao']), 
                1, 
                str(row['Situacao'])
            ))
        
        from psycopg2.extras import execute_values
        sql = "INSERT INTO efetivo_diario (data, matricula, nome, funcao, status_val, situacao) VALUES %s"
        execute_values(cur, sql, data_to_insert)
        
        conn.commit()
        add_log(usuario, "INSERT_BATCH", "efetivo_diario", f"Lote de {len(df)} registros")
        return True
    except Exception as e:
        print(f"Erro batch: {e}")
        conn.rollback()
        return False
    finally:
        conn.close()

def delete_efetivo_por_data(data, usuario):
    sql = "DELETE FROM efetivo_diario WHERE data=%s"
    return execute_non_query(sql, (data,), "DELETE", "efetivo_diario", usuario)

# =========================
# PLUVIOMETRIA
# =========================

def get_pluviometria_periodo(d_ini, d_fim):
    sql = "SELECT data, hora, chuva_mm FROM pluviometria WHERE data BETWEEN %s AND %s ORDER BY data, hora"
    return run_query(sql, (d_ini, d_fim))

def add_pluviometria(data, horas_dict, usuario):
    conn = get_connection()
    if not conn: return False
    try:
        cur = conn.cursor()
        for h, mm in horas_dict.items():
            cur.execute("INSERT INTO pluviometria (data, hora, chuva_mm) VALUES (%s, %s, %s)", (data, h, mm))
        conn.commit()
        add_log(usuario, "INSERT_BATCH", "pluviometria", f"Data: {data}")
        return True
    except:
        return False
    finally:
        conn.close()
