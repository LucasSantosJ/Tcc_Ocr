import os
import jiwer

def ler_arquivo(caminho):
    with open(caminho, 'r', encoding='utf-8') as f:
        return f.read().strip()

def calcular_metricas_llm():
    pasta_gabarito = "data/ground_truth"
    pasta_respostas = "data/outputs/gemini"  # Altere conforme o modelo testado

    soma_txc = 0  # soma das taxas de erro por caractere
    soma_txp = 0  # soma das taxas de erro por palavra
    quantidade = 0

    for arquivo in os.listdir(pasta_gabarito):
        if not arquivo.endswith(".txt"):
            continue

        caminho_gabarito = os.path.join(pasta_gabarito, arquivo)
        caminho_resposta = os.path.join(pasta_respostas, arquivo)

        if not os.path.exists(caminho_resposta):
            print(f"Aviso: Resposta para {arquivo} não encontrada.")
            continue

        texto_gabarito = ler_arquivo(caminho_gabarito)
        texto_resposta = ler_arquivo(caminho_resposta)

        # Taxa de erro por palavra (TXP) e por caractere (TXC)
        # jiwer.wer e jiwer.cer são nomes da biblioteca e não podem ser alterados
        txp = jiwer.wer(texto_gabarito, texto_resposta)
        txc = jiwer.cer(texto_gabarito, texto_resposta)

        soma_txp += txp
        soma_txc += txc
        quantidade += 1

        print(f"Arquivo: {arquivo} | TXC: {txc:.2%} | TXP: {txp:.2%}")

    if quantidade > 0:
        media_txc = soma_txc / quantidade
        media_txp = soma_txp / quantidade
        print("-" * 30)
        print("MÉDIA GERAL DO MODELO:")
        print(f"TAXA DE ERRO POR CARACTERE (TXC): {media_txc:.2%}")
        print(f"TAXA DE ERRO POR PALAVRA (TXP): {media_txp:.2%}")

if __name__ == '__main__':
    calcular_metricas_llm()