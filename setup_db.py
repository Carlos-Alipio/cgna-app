import streamlit as st
from sqlalchemy import text

conn = st.connection("supabase", type="sql")

# Cria tabela para guardar os aeroportos da sua frota/interesse
sql = """
CREATE TABLE IF NOT EXISTS frota_icao (
    icao TEXT PRIMARY KEY,
    descricao TEXT,
    criado_em TIMESTAMP DEFAULT NOW()
);
"""

with conn.session as s:
    s.execute(text(sql))
    s.commit()

print("Tabela 'frota_icao' criada com sucesso!")