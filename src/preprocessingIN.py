import cv2
import os
import numpy as np  # Necessário para criar o kernel da erosão

def pre_processar_imagem():

    caminho_entrada = "data/raw/frasesCursivas.tiff"
    caminho_saida = "data/processed/frasesCursivasTratadas.tiff"

    print(f"Tentando ler a imagem em: {caminho_entrada}")
    imagem = cv2.imread(caminho_entrada)

    if imagem is None:
        print("ERRO: Imagem não encontrada. Verifique se o nome está correto e se ela está dentro de data/raw/")
        return

    cinza = cv2.cvtColor(imagem, cv2.COLOR_BGR2GRAY)
    largura = int(cinza.shape[1] * 2)
    altura = int(cinza.shape[0] * 2)
    redimensionada = cv2.resize(cinza, (largura, altura), interpolation=cv2.INTER_CUBIC)

    # 1. Reduzi o 'h' de 15 para 7 para preservar mais a nitidez dos traços originais
    denoised = cv2.fastNlMeansDenoising(redimensionada, h=7)

    _, binarizada = cv2.threshold(denoised, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)

    # 2. NOVA ETAPA: Erosão (Engrossar o texto preto e tapar buracos brancos)
    # Um kernel 2x2 ou 3x3 determina o quanto a letra vai engrossar
    kernel = np.ones((8, 8), np.uint8)
    imagem_final = cv2.erode(binarizada, kernel, iterations=1)

    sucesso = cv2.imwrite(caminho_saida, imagem_final)

    if sucesso:
        print(f"SUCESSO: Imagem salva em: {caminho_saida}")
    else:
        print("ERRO: Falha ao salvar. Verifique se a pasta data/processed/ existe.")

if __name__ == '__main__':
    pre_processar_imagem()