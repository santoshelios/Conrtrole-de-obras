import sqlite3
import os
from datetime import datetime

# Caminho do banco de dados
DB_PATH = "santin_obras.db"

def get_connection():
    conn = sqlite3.connect(DB_PATH)
    return conn

def init_db():
    """Inicializa as tabelas do banco de dados se não existirem."""
    conn = get_connection()
    cursor = conn.cursor()
    
    # Tabela de Funcionários
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS funcionarios (
            matricula TEXT PRIMARY KEY,
            nome TEXT NOT NULL,
            funcao TEXT,
            abreviacao TEXT,
            admissao TEXT,
            mo TEXT,
            status TEXT
        )
    ''')
    
    # Tabela de Funções
    cursor.execute('CREATE TABLE IF NOT EXISTS funcoes (nome TEXT PRIMARY KEY)')
    
    # Tabela de Equipamentos
    cursor.execute('CREATE TABLE IF NOT EXISTS equipamentos (tag TEXT PRIMARY KEY)')
    
    # Tabela de Apontamentos
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS apontamentos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            matricula TEXT,
            nome TEXT,
            funcao TEXT,
            equipamento TEXT,
            atividade TEXT,
            entrada TEXT,
            saida_almoco TEXT,
            retorno_almoco TEXT,
            saida_final TEXT,
            total_horas TEXT,
            data_apontamento TEXT
        )
    ''')
    
    # Tabela de Usuários (Login)
    cursor.execute('CREATE TABLE IF NOT EXISTS usuarios (usuario TEXT PRIMARY KEY, senha TEXT)')
    
    # Insere usuário padrão se não existir
    cursor.execute("INSERT OR IGNORE INTO usuarios (usuario, senha) VALUES ('admin', '1234')")
    
    # Insere algumas funções básicas se estiver vazio (apenas para o sistema não iniciar totalmente pelado de funções)
    cursor.execute("SELECT COUNT(*) FROM funcoes")
    if cursor.fetchone()[0] == 0:
        for f in ["ENCARREGADO", "MONTADOR", "SOLDADOR", "AJUDANTE", "TECNICO"]:
            cursor.execute("INSERT INTO funcoes (nome) VALUES (?)", (f,))

    conn.commit()
    conn.close()

# Inicializa o banco ao carregar o módulo
init_db()

def check_login(user, pwd):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM usuarios WHERE usuario = ? AND senha = ?", (user, pwd))
    result = cursor.fetchone()
    conn.close()
    return result is not None

def get_funcionarios():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM funcionarios")
    rows = cursor.fetchall()
    conn.close()
    return [list(row) for row in rows]

def add_funcionario(mat, nome, func, abrev, adm, mo, status):
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("INSERT INTO funcionarios VALUES (?, ?, ?, ?, ?, ?, ?)", 
                       (mat, nome, func, abrev, str(adm), mo, status))
        conn.commit()
        conn.close()
        return True, "Sucesso"
    except sqlite3.IntegrityError:
        return False, "Matrícula já existe"

def update_funcionario(mat, nome, func, abrev, adm, mo, status):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('''UPDATE funcionarios SET nome=?, funcao=?, abreviacao=?, admissao=?, mo=?, status=? 
                      WHERE matricula=?''', (nome, func, abrev, str(adm), mo, status, mat))
    conn.commit()
    conn.close()
    return True

def delete_funcionario(mat):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM funcionarios WHERE matricula = ?", (mat,))
    conn.commit()
    conn.close()
    return True

def get_funcoes():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT nome FROM funcoes ORDER BY nome")
    rows = cursor.fetchall()
    conn.close()
    return [row[0] for row in rows]

def add_funcao(nome):
    if not nome: return False
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("INSERT INTO funcoes VALUES (?)", (nome.strip().upper(),))
        conn.commit()
        conn.close()
        return True
    except: return False

def get_equipamentos():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT tag FROM equipamentos ORDER BY tag")
    rows = cursor.fetchall()
    conn.close()
    return [row[0] for row in rows]

def add_equipamento(tag):
    if not tag: return False
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("INSERT INTO equipamentos VALUES (?)", (tag.strip().upper(),))
        conn.commit()
        conn.close()
        return True
    except: return False

def delete_equipamento(tag):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM equipamentos WHERE tag = ?", (tag,))
    conn.commit()
    conn.close()
    return True

def get_apontamentos():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT matricula, nome, funcao, equipamento, atividade, entrada, saida_almoco, retorno_almoco, saida_final, total_horas, data_apontamento FROM apontamentos")
    rows = cursor.fetchall()
    conn.close()
    return [list(row) for row in rows]

def add_apontamento(mat, nome, func, equip, ativ, ent, s_alm, r_alm, s_fin, total, data):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('''INSERT INTO apontamentos (matricula, nome, funcao, equipamento, atividade, entrada, saida_almoco, retorno_almoco, saida_final, total_horas, data_apontamento) 
                      VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''', 
                   (mat, nome, func, equip, ativ, str(ent), str(s_alm), str(r_alm), str(s_fin), total, str(data)))
    conn.commit()
    conn.close()
    return True

def delete_funcao(nome):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM funcoes WHERE nome = ?", (nome,))
    conn.commit()
    conn.close()
    return True

def delete_apontamento(matricula, data, total_horas):
    """Exclui um apontamento específico baseado em matrícula, data e total de horas."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM apontamentos WHERE matricula = ? AND data_apontamento = ? AND total_horas = ?", 
                   (matricula, str(data), total_horas))
    conn.commit()
    conn.close()
    return True

def get_apontamentos_com_id():
    """Retorna apontamentos incluindo o ID para facilitar a exclusão precisa."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id, matricula, nome, funcao, equipamento, atividade, entrada, saida_almoco, retorno_almoco, saida_final, total_horas, data_apontamento FROM apontamentos")
    rows = cursor.fetchall()
    conn.close()
    return [list(row) for row in rows]

def delete_apontamento_por_id(apontamento_id):
    """Exclui um apontamento pelo seu ID único."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM apontamentos WHERE id = ?", (apontamento_id,))
    conn.commit()
    conn.close()
    return True
