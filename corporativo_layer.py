import pandas as pd
from datetime import datetime

def criar_snapshot_efetivo(conn, usuario):
    cur = conn.cursor()

    # tabela de versões
    cur.execute("""
    CREATE TABLE IF NOT EXISTS efetivo_versions (
        id SERIAL PRIMARY KEY,
        data_snapshot TIMESTAMP,
        usuario TEXT,
        qtd_registros INTEGER
    )
    """)

    # tabela snapshot
    cur.execute("""
    CREATE TABLE IF NOT EXISTS efetivo_snapshot (
        version_id INTEGER,
        data DATE,
        matricula TEXT,
        nome TEXT,
        funcao TEXT,
        status_val INTEGER,
        situacao TEXT
    )
    """)

    # quantidade atual
    cur.execute("SELECT COUNT(*) FROM efetivo_diario")
    qtd = cur.fetchone()[0]

    # cria versão
    cur.execute(
        "INSERT INTO efetivo_versions (data_snapshot, usuario, qtd_registros) VALUES (%s,%s,%s) RETURNING id",
        (datetime.now(), usuario, qtd)
    )

    version_id = cur.fetchone()[0]

    # copia dados
    cur.execute("""
        INSERT INTO efetivo_snapshot
        SELECT %s, data, matricula, nome, funcao, status_val, situacao
        FROM efetivo_diario
    """, (version_id,))

    conn.commit()

    return version_id


def restaurar_snapshot(conn, version_id):
    cur = conn.cursor()

    # limpa base atual
    cur.execute("DELETE FROM efetivo_diario")

    # restaura versão
    cur.execute("""
        INSERT INTO efetivo_diario (data, matricula, nome, funcao, status_val, situacao)
        SELECT data, matricula, nome, funcao, status_val, situacao
        FROM efetivo_snapshot
        WHERE version_id = %s
    """, (version_id,))

    conn.commit()