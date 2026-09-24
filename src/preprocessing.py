import cv2
import os

def pre_processar_imagem():

    mapa_imagens = {
        "data/raw/alfabetoCursivo.jpg": "data/processed/alfabetoCursivoTratada.tiff",
        "data/raw/alfabetoMaiusculo.jpg": "data/processed/alfabetoMaiusculoTratada.tiff",
    }

    for caminho_entrada, caminho_saida in mapa_imagens.items():
        print(f"\nProcessando: {caminho_entrada}")
        imagem = cv2.imread(caminho_entrada)

        if imagem is None:
            print(f"ERRO: Imagem {caminho_entrada} não encontrada.")
            continue

        cinza = cv2.cvtColor(imagem, cv2.COLOR_BGR2GRAY)
        largura = int(cinza.shape[1] * 2)
        altura = int(cinza.shape[0] * 2)
        redimensionada = cv2.resize(cinza, (largura, altura), interpolation=cv2.INTER_CUBIC)
        denoised = cv2.fastNlMeansDenoising(redimensionada, h=15)
        _,binarizada = cv2.threshold(denoised, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)

        sucesso = cv2.imwrite(caminho_saida, binarizada)
    
        if sucesso:
            print(f"SUCESSO: Imagem salva em: {caminho_saida}")
        else:
            print("ERRO: Falha ao salvar. Verifique se a pasta data/processed/ existe.")

if __name__ == '__main__':
    pre_processar_imagem()