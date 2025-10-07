
import os
import glob
import zipfile


class Utils:
    
    @staticmethod
    def limpar_pasta_graficos(pasta: str):
        print("limpar_pasta_graficos")
        """
        Remove todos os arquivos PNG e ZIP da pasta 'files' antes de gerar novos gráficos.
        """
        
        # Certifica-se que a pasta existe
        os.makedirs(pasta, exist_ok=True)

        # Buscar todos os PNG e ZIP
        arquivos = glob.glob(os.path.join(pasta, "*.png")) + glob.glob(os.path.join(pasta, "*.zip")) + glob.glob(os.path.join(pasta, "*.csv")) + glob.glob(os.path.join(pasta, "*.jpeg")) + glob.glob(os.path.join(pasta, "*.jpg"))
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
            for arquivo in arquivos:
                if arquivo.endswith(".zip"):
                    with zipfile.ZipFile(arquivo, 'r') as zip_ref:
                        if len(zip_ref.namelist()) == 0:
                            return True
            return False
        else:
            print(f"Nenhum arquivo encontrado em {pasta}.")
            return True
