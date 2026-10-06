import os
from google import genai
from dotenv import load_dotenv

load_dotenv()
chave_api = os.getenv("GEMINI_API_KEY")
if not chave_api:
    print("ERRO CRÍTICO: Chave GEMINI_API_KEY não encontrada!")
    exit()

cliente = genai.Client(api_key=chave_api)

def extrair_texto_gemini():
    pasta_imagens = "data/processed"
    pasta_saida = "data/outputs/gemini"
    os.makedirs(pasta_saida, exist_ok=True)

    prompt = "Retorne apenas a Transcrição."

    for arquivo in os.listdir(pasta_imagens):
        if not arquivo.lower().endswith(('.jpg', '.jpeg', '.png', '.tiff')):
            continue

        caminho_imagem = os.path.join(pasta_imagens, arquivo)
        nome_txt = os.path.splitext(arquivo)[0] + ".txt"
        caminho_txt = os.path.join(pasta_saida, nome_txt)

        print(f"\nProcessando: {arquivo}...")

        try:
            arquivo_upload = cliente.files.upload(file=caminho_imagem)

            resposta = cliente.models.generate_content(
                model='gemini-3.5-flash-lite',
                contents=[arquivo_upload, prompt]
            )

            with open(caminho_txt, 'w', encoding='utf-8') as f:
                f.write(resposta.text.strip())

            print(f"SUCESSO: Transcrição salva em {caminho_txt}")

        except Exception as e:
            print(f"ERRO: Falha ao processar {arquivo}: {e}")

if __name__ == '__main__':
    extrair_texto_gemini()