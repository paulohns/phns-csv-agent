import streamlit as st
import pandas as pd
import os
import glob
from langchain_experimental.agents import create_pandas_dataframe_agent
from zipfile import ZipFile
import matplotlib.pyplot as plt
from utils import Utils
from agent import CSVAnalysisAgent

st.set_page_config(page_title="Agente CSV LLM", layout="wide")

st.title("🤖 PHNS - Agent CSV com LangChain")

# Inicializa o histórico na sessão
if "historico" not in st.session_state:
    st.session_state.historico = []

# 🔑 Pega a chave do secrets (configurada no Streamlit Cloud)
api_key =  st.secrets["GROQ_API_KEY"]
if "GROQ_API_KEY" not in st.secrets:
    st.error("❌ Configure sua chave da OpenAI em st.secrets['GROQ_API_KEY']")
else:
    os.environ["GROQ_API_KEY"] = api_key

CSVAnalysisAgent = CSVAnalysisAgent(key=api_key)
utils = Utils()

# 📂 Upload CSV
uploaded_file = st.file_uploader("Carregue um arquivo CSV", type=["csv"])
PASTA_ARQUIVOS = "files"
os.makedirs(PASTA_ARQUIVOS, exist_ok=True)

# Função para limpar o campo
def limpar_pergunta():
    st.session_state.pergunta = ""


if uploaded_file and api_key:
    df = pd.read_csv(uploaded_file)
    CSVAnalysisAgent.load_file(df)

    st.write("### Pré-visualização dos dados")
    st.dataframe(df.head())

    # Pergunta do usuário
    pergunta = st.text_area("❓ Faça uma pergunta sobre os dados:")
    # Inicializa o estado da sessão
    if "pergunta" not in st.session_state:
        st.session_state.pergunta = pergunta

    if st.button("Perguntar", disabled=not pergunta):
        utils.limpar_pasta_graficos(PASTA_ARQUIVOS)
        utils.limpar_pasta_graficos(".")
        with st.spinner("Pensando..."):
            try:
                resposta = CSVAnalysisAgent.agent.run(pergunta)
                
                # Armazena no histórico
                st.session_state.historico.append({"pergunta": pergunta, "resposta": resposta})
                st.success("Resposta do Agente")
                st.write(resposta)
                limpar_pergunta()
            except Exception as e:
                st.error(f"Erro ao processar: {e}")

    arquivos = glob.glob(os.path.join(PASTA_ARQUIVOS, "*.png"))
    zip_path = os.path.join(PASTA_ARQUIVOS, "graficos.zip")
    with ZipFile(zip_path, "w") as zipf:
        if len(arquivos) > 0:
            for f in arquivos:
                zipf.write(f, os.path.basename(f))

    with open(zip_path, "rb") as f:
        st.download_button("📥 Baixar gráficos ZIP", f, file_name="graficos.zip", disabled=utils.verificar_pasta_arquivos(PASTA_ARQUIVOS))

# Exibe todo o histórico
st.subheader("Histórico de Perguntas e Respostas")
for idx, item in enumerate(st.session_state.historico, 1):
    st.markdown(f"**{idx}. Pergunta:** {item['pergunta']}")
    st.markdown(f"➡️ **Resposta:** {item['resposta']}")
    st.write("---")
