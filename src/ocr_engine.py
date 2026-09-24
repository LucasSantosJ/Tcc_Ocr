import pytesseract
from PIL import Image

from preprocessing import pre_processar_imagem

imagem = Image.open("data/processed/tratada_OcrTest.tiff")

# Configurações para maximizar a extração nativa do Tesseract
configuracao = r'--oem 1 --psm 6 -c preserve_interword_spaces=1'

texto_extraido = pytesseract.image_to_string(imagem, lang='por', config=configuracao)

# Exibe o resultado no console
print("Texto extraído:")
print("----------------")
print(texto_extraido)