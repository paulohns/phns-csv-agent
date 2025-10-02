import pandas as pd
import re
import matplotlib.pyplot as plt
import textwrap
import os
import glob
import zipfile
from io import BytesIO
from fastapi.responses import StreamingResponse


class Utils:

    @staticmethod
    def eh_grafico(resposta):
        print("Verificando se é gráfico:", resposta)
        """
        Verifica se a resposta contém dados reais para gráfico.
        """
        if isinstance(resposta, list) and all(isinstance(d, dict) for d in resposta):
            # Checa se existe chave 'distribution' com lista de bins ou valores
            for var in resposta:
                dist = var.get("distribution")
                if isinstance(dist, list) and len(dist) > 0 and all(isinstance(b, dict) for b in dist):
                    return True
            # Caso seja lista de dicts (x/y)
            if isinstance(resposta, list) and all(isinstance(d, dict) for d in resposta):
                if all("x" in d and "y" in d for d in resposta):
                    return True
            
            # Caso seja dict de colunas com min/max
            elif isinstance(resposta, dict):
                # Verifica se cada valor é um dict com 'min' e 'max'
                if all(isinstance(v, dict) and "min" in v and "max" in v for v in resposta.values()):
                    return True
                if all(isinstance(v, dict) and "mínimo" in v and "máximo" in v for v in resposta.values()):
                    return True
        
        df = pd.DataFrame(resposta)
        # Detecta colunas numéricas e categóricas
        cat_cols = df.select_dtypes(exclude="number").columns
        num_cols = df.select_dtypes(include="number").columns
        
        if isinstance(resposta, dict):
        
            if all(isinstance(v, dict) and "min" in v and "max" in v for v in resposta.values()):
                return True
            if all(isinstance(v, dict) and "mínimo" in v and "máximo" in v for v in resposta.values()):
                return True
            if all(isinstance(v, dict) and "mean" in v and "max" in v and "min" in v for v in resposta.values()):
                return True
            if all(isinstance(v, dict) and "média" in v and "máximo" in v and "mínimo" in v for v in resposta.values()):
                return True
            if all(isinstance(v, dict) and "variable" in v and "max" in v and "min" in v for v in resposta.values()):
                return True
        if len(cat_cols) > 0 and len(num_cols) > 0:
            return True
        else:
            print("Não há colunas categóricas e numéricas suficientes")
            return False

    @staticmethod
    def limpar_markdown_json(resposta: str) -> str:
        """
        Remove blocos de código Markdown do tipo ```json ... ``` ou ``` ... ``` da string.
        Retorna apenas o conteúdo limpo que pode ser parseado como JSON.
        """
        if not isinstance(resposta, str):
            return resposta  # Não é string, retorna como está

        # Regex para remover qualquer bloco ```...```
        resposta_limpa = re.sub(r'```.*?```', '', resposta, flags=re.DOTALL)
        
        # Remove espaços em excesso e quebras de linha no início/fim
        resposta_limpa = resposta_limpa.strip()
        return resposta_limpa

    @staticmethod
    def eh_grafico_old(resposta):
        """
        Verifica se a resposta é um formato válido para gráfico:
        - Lista de dicts
        - Contendo pelo menos uma coluna categórica e uma numérica
        """
        print("Verificando se é gráfico:", resposta)
        
        # Verifica se é lista de dicionários
        if isinstance(resposta, list) and all(isinstance(d, dict) for d in resposta):
            print("Resposta é lista de dicts")
            try:
                df = pd.DataFrame(resposta)
                # Detecta colunas numéricas e categóricas
                cat_cols = df.select_dtypes(exclude="number").columns
                num_cols = df.select_dtypes(include="number").columns
                if len(cat_cols) > 0 and len(num_cols) > 0:
                    return True
                else:
                    print("Não há colunas categóricas e numéricas suficientes")
                    return False
            except Exception as e:
                print("Erro ao criar DataFrame:", e)
                return False
        
        print("Resposta não é lista de dicts")
        return False
    
    @staticmethod
    def tipo_grafico(resposta):
        """
        Detecta se a resposta da LLM pode ser transformada em gráfico.
        Retorna o tipo de gráfico:
            - "xy" → lista de dicts com x/y
            - "categorical" → contagem de categorias
            - "stats" → estatísticas numéricas
            - None → não é gráfico
        """

        # 1️⃣ Lista de dicts com x/y
        if isinstance(resposta, list) and all(isinstance(d, dict) for d in resposta):
            # caso x/y
            if all("x" in d and "y" in d for d in resposta):
                return "xy"
            # caso estatísticas (min/max ou variável)
            if all("min" in d and "max" in d for d in resposta):
                return "stats"
            if all("variable" in d and "min" in d and "max" in d for d in resposta):
                return "stats"

        # 2️⃣ Distribuição categórica
        if isinstance(resposta, dict):
            for v in resposta.values():
                # contagens
                if isinstance(v, dict) and all(isinstance(count, int) for count in v.values()):
                    return "categorical"
                # estatísticas numéricas
                if isinstance(v, dict) and ("min" in v and "max" in v and "mean" in v):
                    return "stats"
                if isinstance(v, dict) and ("mínimo" in v and "máximo" in v and "média" in v):
                    return "stats"

        print("Resposta não é válida para gráfico")
        return None
    
    @staticmethod
    def gerar_grafico(resposta):
        print("Gerando gráfico com dados:")
        """
        Gera gráfico a partir da resposta da LLM.
        Retorna BytesIO pronto para StreamingResponse.
        """
        tipo = tipo_grafico(resposta)
        
        buf = BytesIO()
        print("Tipo de gráfico detectado:", tipo)
        if tipo == "xy":
            df = pd.DataFrame(resposta)
            plt.figure(figsize=(6,4))
            plt.plot(df["x"], df["y"], marker='o')
            plt.title("Gráfico gerado pela LLM")
            plt.xlabel("x")
            plt.ylabel("y")
            plt.grid(True)
            plt.tight_layout()
        
        elif tipo == "categorical":
            # pega a primeira chave categórica
            for k, v in resposta.items():
                if isinstance(v, dict) and all(isinstance(count, int) for count in v.values()):
                    categorias = list(v.keys())
                    counts = list(v.values())
                    plt.figure(figsize=(6,4))
                    plt.bar(categorias, counts)
                    plt.title(f"Distribuição de {k}")
                    plt.xlabel(k)
                    plt.ylabel("Contagem")
                    plt.xticks(rotation=45, ha="right")
                    plt.grid(True)
                    plt.tight_layout()
                    break
        
        elif tipo == "stats":
            colunas = []
            valores = []
            label = ""

            if isinstance(resposta, dict):
                # Caso 1: resposta em formato dict com médias
                for col, stats in resposta.items():
                    if isinstance(stats, dict) and "mean" in stats:
                        colunas.append(col)
                        valores.append(stats["mean"])
                        label = "Mean"
                    elif isinstance(stats, dict) and "média" in stats:
                        colunas.append(col)
                        valores.append(stats["média"])
                        label = "Média"

            elif isinstance(resposta, list):
                # Caso 2: resposta em formato lista de dicts (min/max/variable)
                for item in resposta:
                    if "variable" in item and "min" in item and "max" in item:
                        colunas.append(item["variable"])
                        # exemplo: diferença entre max e min (faixa)
                        valores.append(item["max"] - item["min"])
                        label = "Amplitude (max-min)"

            if colunas and valores:
                plt.figure(figsize=(10,5))
                plt.bar(colunas, valores)
                plt.xticks(rotation=90)
                plt.title("Estatísticas das variáveis")
                plt.ylabel(label)
                plt.grid(True)
                plt.tight_layout()
        
        else:
            raise ValueError("Resposta não é válida para gráfico")
        
        plt.savefig(buf, format="png")
        plt.close()
        buf.seek(0)

        return StreamingResponse(
            buf,
            media_type="image/png",
            headers={"Content-Disposition": "attachment; filename=grafico.png"}
        )

    @staticmethod
    def gerar_grafico_automatico(dados):
        """
        Detecta automaticamente o tipo de dados e gera gráfico apropriado:
        - Lista de dicts com 'x'/'y' ou qualquer par categórica/numérica → barras
        - Lista de dicts com 'value'/'percentage' → pizza
        - Lista de variáveis com 'distribution' → histograma
        """
        print("Gerando gráfico automático com dados")

        if all(isinstance(v, dict) and "min" in v and "max" in v for v in dados):
            print("DEBUG: Detectado dados de min/max para gráfico de barras")

        if all(isinstance(v, dict) and "mínimo" in v and "máximo" in v for v in dados):
            print("DEBUG: Detectado dados de mínimo/máximo para gráfico de barras")

        # Caso seja histograma/distribution
        if isinstance(dados, list) and 'variable' in dados[0] and 'distribution' in dados[0]:
            print("Detectado dados de distribuição para histograma")

            for i in range(len(dados)):
                print(f"Processando variável {i+1}/{len(dados)}")
                var = dados[i]  # pegando a variável atual
                nome_var = var['variable']
                dist = var['distribution']

                # Detectar bins ou categorias
                if 'bin_range' in dist[0]:
                    labels = [b['bin_range'] for b in dist]
                elif 'category' in dist[0]:
                    labels = [b['category'] for b in dist]
                else:
                    raise ValueError("Formato de distribuição desconhecido")

                counts = [b['count'] for b in dist]

                plt.figure(figsize=(10,6))
                plt.bar(labels, counts, color='skyblue')
                plt.xticks(rotation=45, ha='right')
                plt.title(f"Distribuição da variável {nome_var}")
                plt.xlabel(nome_var)
                plt.ylabel("Contagem")
                plt.grid(axis='y', linestyle='--', alpha=0.7)

        # Caso seja gráfico tipo pizza
        elif isinstance(dados, list) and 'value' in dados[0] and 'percentage' in dados[0]:
            print("Detectado dados para gráfico de pizza")
            df = pd.DataFrame(dados).sort_values('percentage', ascending=False).head(20)
            plt.figure(figsize=(8,8))
            plt.pie(df['percentage'], labels=df['value'], autopct="%1.1f%%", startangle=140)
            plt.title("Gráfico de Pizza")

        # Caso seja gráfico de barras genérico (x/y ou categórica/numérica)
        elif isinstance(dados, list) and all(isinstance(d, dict) for d in dados):
            print("Detectado dados para gráfico de barras")
            df = pd.DataFrame(dados)
            cat_cols = df.select_dtypes(exclude="number").columns
            num_cols = df.select_dtypes(include="number").columns
            if len(cat_cols) == 0 or len(num_cols) == 0:
                raise ValueError("Não foi possível identificar colunas para gráfico de barras.")
            cat_col = cat_cols[0]
            num_col = num_cols[0]
            df = df.sort_values(num_col, ascending=False).head(20)

            plt.figure(figsize=(10,6))
            plt.barh(df[cat_col], df[num_col], color="skyblue")
            plt.title("Gráfico de Barras")
            plt.xlabel(num_col)
            plt.ylabel(cat_col)
            plt.gca().invert_yaxis()
            plt.grid(axis="x", linestyle="--", alpha=0.7)
            print("dados para gráfico de barras ok")
        elif isinstance(dados, dict) and all(isinstance(v, dict) and "min" in v and "max" in v for v in dados):
            print("dados para gráfico de min/max")
            df = pd.DataFrame(dados).T  # Transpor para ter colunas: min, max
            df.reset_index(inplace=True)
            df.rename(columns={'index': 'Variable'}, inplace=True)

            # Plot
            plt.figure(figsize=(10,6))
            plt.bar(df['Variable'], df['max'], label='Max', alpha=0.7)
            plt.bar(df['Variable'], df['min'], label='Min', alpha=0.7)
            plt.xticks(rotation=45, ha='right')
            plt.ylabel('Valores')
            plt.title('Min e Max das variáveis')
            plt.legend()
            plt.grid(axis='y')
        elif isinstance(dados, dict) and all(isinstance(v, dict) and "mínimo" in v and "máximo" in v for v in dados):
            print("dados para gráfico de min/max")
            df = pd.DataFrame(dados).T  # Transpor para ter colunas: min, max
            df.reset_index(inplace=True)
            df.rename(columns={'index': 'Variable'}, inplace=True)

            # Plot
            plt.figure(figsize=(10,6))
            plt.bar(df['Variable'], df['máximo'], label='Max', alpha=0.7)
            plt.bar(df['Variable'], df['mínimo'], label='Min', alpha=0.7)
            plt.xticks(rotation=45, ha='right')
            plt.ylabel('Valores')
            plt.title('Min e Max das variáveis')
            plt.legend()
            plt.grid(axis='y') 
        else:
            print("Dados não reconhecidos para gráfico")
            raise ValueError("Formato de dados não suportado para gráfico.")

        # Salvar em PNG e retornar StreamingResponse
        buf = BytesIO()
        plt.tight_layout()
        plt.savefig(buf, format='png')
        plt.close()
        buf.seek(0)

        return StreamingResponse(
            buf,
            media_type="image/png",
            headers={"Content-Disposition": "attachment; filename=grafico.png"}
        )
    
    @staticmethod
    def executar_codigo_llm(codigo: str, variaveis=None):
        globals_dict = {"plt": plt, "BytesIO": BytesIO, "__builtins__": {"print": print, "len": len, "range": range}}
        
        if variaveis:
            globals_dict.update(variaveis)

        locals_dict = {}

        codigo = re.sub(r"plt\.show\(\)", "", codigo)
        codigo = textwrap.dedent(codigo).strip()

        bloco_salvar = f"""
            buf = BytesIO()
            plt.tight_layout()
            plt.savefig(r"/files/grafico.png", format="png")
            plt.close()
            buf.seek(0)
        """
        codigo = codigo.strip() + "\n" + bloco_salvar
        codigo = textwrap.dedent(codigo).strip()
        exec(codigo, globals_dict, locals_dict)
        return locals_dict
    
    @staticmethod
    def eh_codigo_grafico(codigo: str) -> bool:
        print("Entrou aqui eh_codigo_grafico")
        padroes = ["plt.", "sns.", "plt.savefig", "plt.show", "hist(", "plot("]
        return any(p in codigo for p in padroes)

    @staticmethod
    def executar_graficos_llm(codigos: list[str], contexto: dict) -> dict:
        """
        Executa código Python da LLM que gera gráficos e salva os arquivos.
        Se houver mais de um arquivo, cria um ZIP.
        
        Args:
            codigos: lista de strings com código da LLM.
            contexto: dicionário com variáveis disponíveis (ex: {"df": df}).
            pasta_saida: pasta onde os arquivos serão salvos.
            
        Returns:
            dict: {"status": "ok", "arquivos": [...]} ou {"status": "erro", "detalhe": "..."}
        """
        print("antes do makers")
        
        # Criar pasta para arquivos se não existir
        if not os.path.exists("graficos"):
            os.makedirs("graficos")
            
        print("Passou do makers")
        arquivos_gerados = []

        for i, codigo in enumerate(codigos):
            # Normaliza indentação
            codigo_limpo = textwrap.dedent(codigo).strip()

            # Gera nome do arquivo
            arquivo_png = os.path.join("graficos", f"grafico_{i+1}.png")

            # Substitui plt.show() por salvar o gráfico
            codigo_limpo = codigo_limpo.replace(
                "plt.show()", f"plt.tight_layout(); plt.savefig(r'{arquivo_png}'); plt.close()"
            )

            globals_dict = {"plt": plt, **contexto}
            locals_dict = {}

            try:
                exec(codigo_limpo, globals_dict, locals_dict)
                arquivos_gerados.append(arquivo_png)
            except Exception as e:
                return {"status": "erro", "detalhe": str(e)}

        # Se houver mais de um gráfico, gera um ZIP
        if len(arquivos_gerados) > 1:
            zip_path = os.path.join("graficos", "graficos.zip")
            with zipfile.ZipFile(zip_path, 'w') as zipf:
                for arquivo in arquivos_gerados:
                    zipf.write(arquivo, os.path.basename(arquivo))
            return {"status": "ok", "arquivos": arquivos_gerados, "zip": zip_path}

        return {"status": "ok", "arquivos": arquivos_gerados}
    
    @staticmethod
    def extrair_codigo_python(texto: str) -> str:
        """
        Recebe a resposta da LLM e retorna apenas o código Python contido nela.
        Funciona para blocos de código com ```python ou ``` ou linhas iniciadas com 4 espaços.
        """
        # Primeiro, tenta encontrar blocos ```python ... ```
        padrao = r"```(?:python)?\s*(.*?)```"
        match = re.search(padrao, texto, re.DOTALL | re.IGNORECASE)
        if match:
            return match.group(1).strip()
        
        # Caso não encontre, tenta linhas com indentação de código
        linhas = texto.splitlines()
        codigo = "\n".join([l[4:] for l in linhas if l.startswith("    ")])
        if codigo:
            return codigo.strip()
        
        # Se não encontrar nada, retorna None
        return None
    
    @staticmethod
    def limpar_pasta_graficos(pasta: str):
        print("limpar_pasta_graficos")
        """
        Remove todos os arquivos PNG e ZIP da pasta 'files' antes de gerar novos gráficos.
        """
        
        # Certifica-se que a pasta existe
        os.makedirs(pasta, exist_ok=True)

        # Buscar todos os PNG e ZIP
        arquivos = glob.glob(os.path.join(pasta, "*.png")) + glob.glob(os.path.join(pasta, "*.zip"))
        print("arquivos")
        print(arquivos)
        for arq in arquivos:
            try:
                os.remove(arq)
                print(f"Removido: {arq}")
            except Exception as e:
                print(f"Erro ao remover {arq}: {e}")

    @staticmethod
    def verificar_pasta_arquivos(pasta: str):
        print("verificar_pasta_arquivos")
        """
        Verifica se a pasta 'files' contém arquivos PNG ou ZIP.
        """
        arquivos = glob.glob(os.path.join(pasta, "*.png")) + glob.glob(os.path.join(pasta, "*.zip"))
        if arquivos:
            print(f"Arquivos encontrados em {pasta}: {arquivos}")
            return False
        else:
            print(f"Nenhum arquivo encontrado em {pasta}.")
            return True
