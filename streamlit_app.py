import streamlit as st
import pandas as pd
import os
import tempfile
from langchain_experimental.agents import create_pandas_dataframe_agent
from langchain_groq.chat_models import ChatGroq
from langchain.memory import ConversationBufferMemory
from zipfile import ZipFile
import matplotlib.pyplot as plt

st.set_page_config(page_title="Agente CSV LLM", layout="wide")

st.title("🤖 Agente de Análise Exploratória de Dados (LLM + CSV)")

# 🔑 Pega a chave do secrets (configurada no Streamlit Cloud)
api_key =  st.secrets["GROQ_API_KEY"]
if "GROQ_API_KEY" not in st.secrets:
    st.error("❌ Configure sua chave da OpenAI em st.secrets['GROQ_API_KEY']")
else:
    os.environ["GROQ_API_KEY"] = api_key

# 📂 Upload CSV
uploaded_file = st.file_uploader("Carregue um arquivo CSV", type=["csv"])

if uploaded_file and api_key:
    df = pd.read_csv(uploaded_file)

    st.write("### Pré-visualização dos dados")
    st.dataframe(df.head())

    prompt_inicial = """
        Você é um assistente especializado em análise de dados CSV. 
        Seu objetivo é permitir que o usuário faça perguntas sobre qualquer arquivo CSV carregado e fornecer análises detalhadas de EDA (Exploração de Dados)
        em formato de texto caso a pergunta seja simples ou em graficos e a quantidade de gráficos deve ser de no máximo o numero de colunas do arquivo carregado.

        O que você deve fazer:
        1. Descrição dos Dados:
            - Identifique tipos de dados (numéricos, categóricos).
            - Informe distribuição de cada variável (histogramas, distribuições).
            - Informe intervalos (mínimo, máximo) e medidas de tendência central (média, mediana).
            - Informe variabilidade (desvio padrão, variância).
        2. Identificação de Padrões e Tendências:
            - Analise padrões ou tendências temporais.
            - Informe os valores mais frequentes e menos frequentes.
            - Verifique a existência de agrupamentos (clusters) nos dados.
        3. Detecção de Outliers:
            - Detecte valores atípicos.
            - Analise como os outliers afetam a análise.
            - Sugira estratégias de tratamento (remoção, transformação, investigação).
        4. Relações entre Variáveis:
            - Analise relações entre variáveis (gráficos de dispersão, tabelas cruzadas).
            - Informe correlações.
            - Indique variáveis com maior ou menor influência sobre outras.
        5. Conclusões:
            - Sempre sintetize conclusões com base nas análises realizadas.

            REGRAS:
            
            - Para análise gráfica, utilize matplotlib ou pandas plotting e retorne o codigo para execução em formato de listas para mais de um grafico.
            - Nunca execute código diretamente na conversa; use sempre a ferramenta `python_repl_ast`.
            - Sempre tente fornecer respostas concisas e informativas.
            - Utilize a memória para lembrar perguntas anteriores e sintetizar conclusões ao longo da análise.
            - Só use "Final Answer" quando NÃO houver mais "Action".
            - Nunca coloque "Final Answer" junto com um "Action".
            - Se você gerar código Python, NÃO escreva a conclusão até que ele seja executado.
            - Retorne Thought junto com a resposta final

            IMPORTANTE:
            - Nunca escreva "Final Answer" junto com "Action".
            - Sempre gere código Python primeiro e use Action.
            - Depois que o código for executado, use Final Answer apenas para retornar o caminho do(s) arquivo(s).
            - Em caso de solicitação de gráficos na pergunta, CRIE SOMENTE O GRAFICO SOLICITADO e retorne somente o caminho ("files") do arquivo ou ZIP e nunca reimprima os gráficos caso
            contrário NÃO gerar graficos retornar somente a resposta. 
            Exemplo:
            ```python
            # código Python válido 
            import matplotlib.pyplot as plt
            import os
            from zipfile import ZipFile

            os.makedirs("files", exist_ok=True)
            arquivos = []

            numerical_cols = df.select_dtypes(include='number').columns

            for col in numerical_cols:
                caminho = f"files/hist_{{col}}.png"
                plt.figure()
                df[col].hist(bins=30)
                plt.title(f"Distribuição de {{col}}")
                plt.xlabel(col)
                plt.ylabel("Frequência")
                plt.tight_layout()
                plt.savefig(caminho)
                plt.close()
                arquivos.append(caminho)

            if len(arquivos) > 1:
                with ZipFile("files/graficos.zip", "w") as zipf:
                    for f in arquivos:
                        zipf.write(f, os.path.basename(f))
            ``` 
    """
    memory = ConversationBufferMemory(
        memory_key="chat_history", 
        return_messages=False
    )
    # Criar agente
    llm = ChatGroq(
        model="llama-3.3-70b-versatile", 
        temperature=0, 
        api_key=api_key, 
        base_url="https://api.groq.com"
    )
    agent = create_pandas_dataframe_agent(
        llm, 
        df, 
        verbose=True,
        prefix=prompt_inicial,
        max_iterations=5000,
        agent_executor_kwargs={
            "memory": memory,
            "handle_parsing_errors": True
        },
        allow_dangerous_code=True
    )

    # Pergunta do usuário
    pergunta = st.text_area("❓ Faça uma pergunta sobre os dados:")

    if st.button("Responder"):
        with st.spinner("Pensando..."):
            try:
                resposta = agent.run(pergunta)
                st.success("Resposta do Agente:")
                st.write(resposta)
            except Exception as e:
                st.error(f"Erro ao processar: {e}")

    # ⚡ Extra: gerar ZIP com histogramas
    st.write("### Gerar histogramas de todas as colunas numéricas")
    if st.button("Gerar ZIP de gráficos"):
        num_cols = df.select_dtypes(include="number").columns.tolist()
        if not num_cols:
            st.warning("Nenhuma coluna numérica encontrada!")
        else:
            with tempfile.TemporaryDirectory() as tmpdir:
                arquivos = []
                for col in num_cols:
                    fig, ax = plt.subplots()
                    df[col].hist(bins=30, ax=ax)
                    ax.set_title(f"Distribuição de {col}")
                    caminho = os.path.join(tmpdir, f"{col}.png")
                    fig.savefig(caminho)
                    arquivos.append(caminho)
                    plt.close(fig)

                zip_path = os.path.join(tmpdir, "graficos.zip")
                with ZipFile(zip_path, "w") as zipf:
                    for f in arquivos:
                        zipf.write(f, os.path.basename(f))

                with open(zip_path, "rb") as f:
                    st.download_button("📥 Baixar gráficos ZIP", f, file_name="graficos.zip")

# Exibe todo o histórico
st.subheader("Histórico de Perguntas e Respostas")
for idx, item in enumerate(st.session_state.historico, 1):
    st.markdown(f"**{idx}. Pergunta:** {item['pergunta']}")
    st.markdown(f"➡️ **Resposta:** {item['resposta']}")
    st.write("---")
