import streamlit as st

# Tenta conectar
try:
    conn = st.connection("supabase", type="sql")
    st.success("✅ Conexão com Supabase realizada com sucesso!")
    
    # Tenta fazer uma consulta simples (quem sou eu?)
    df = conn.query("SELECT current_user;", ttl=0)
    st.write("Usuário do banco:", df)
    
except Exception as e:
    st.error(f"❌ Erro na conexão: {e}")