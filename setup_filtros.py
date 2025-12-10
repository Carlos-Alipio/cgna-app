import streamlit as st
from sqlalchemy import text

conn = st.connection("supabase", type="sql")

# Tabela para guardar: "Quero ver ASSUNTO: Pista" ou "Quero ver CONDIÇÃO: Fechado"
sql = """
CREATE TABLE IF NOT EXISTS config_filtros (
    tipo TEXT,  -- 'assunto' ou 'condicao'
    valor TEXT, -- O texto exato (ex: 'Pista (Runway)')
    PRIMARY KEY (tipo, valor)
);
"""

with conn.session as s:
    s.execute(text(sql))
    s.commit()

print("Tabela 'config_filtros' criada!")
