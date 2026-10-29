import csv
import os
import re
import statistics
import unicodedata
from collections import defaultdict
from difflib import SequenceMatcher

import jiwer

# ======================= CONFIGURAÇÃO =======================
PASTA_GABARITO = "data/pages/0013"
PASTA_RESPOSTAS = "data/outputs/gemini"  # Altere conforme o modelo testado
NOME_MODELO = "gemini"
PASTA_SAIDA = "data/metricas"

IGNORAR_MAIUSCULAS = False       # True = "A" e "a" passam a ser iguais
INCLUIR_RISCADO_LEGIVEL = False  # True = texto riscado legível entra no gabarito

NOMES_ACENTOS = {
    "\u0301": "agudo",
    "\u0300": "crase",
    "\u0302": "circunflexo",
    "\u0303": "til",
    "\u0327": "cedilha",
    "\u0308": "trema",
}

COLUNAS_TAXAS = [
    "txc", "txp", "txc_sem_acento", "acuracia_palavras",
    "taxa_acerto_acento", "taxa_omissao", "taxa_troca",
    "taxa_letra_errada", "taxa_acrescimo",
]
COLUNAS_CONTAGENS = [
    "palavras_inseridas", "total_acentos", "acertos_acento",
    "omissoes", "trocas", "letras_erradas", "acrescimos",
]
CABECALHO = ["modelo", "arquivo"] + COLUNAS_TAXAS + COLUNAS_CONTAGENS

# Marcações do dataset. A ordem importa: as mais específicas vêm primeiro.
REGRAS_MARCACAO = [
    ("ilegivel", re.compile(r"(?:##|\$\$)?@@\?\?\?@@(?:##|\$\$)?"), ""),
    ("riscado_ilegivel", re.compile(r"(?:##|\$\$)?--x+--(?:##|\$\$)?"), ""),
    ("riscado_legivel",
     re.compile(r"(?:##|\$\$)--(.+?)--(?:##|\$\$)|--(.+?)--", re.DOTALL),
     lambda m: (m.group(1) or m.group(2) or "") if INCLUIR_RISCADO_LEGIVEL else ""),
    ("sobrescrito", re.compile(r"##(.+?)##", re.DOTALL), r"\1"),
    ("subscrito", re.compile(r"\$\$(.+?)\$\$", re.DOTALL), r"\1"),
]


# ======================= TEXTO =======================
def ler_arquivo(caminho):
    with open(caminho, "r", encoding="utf-8") as f:
        return f.read().strip()


def limpar_marcacoes(texto):
    """Converte as anotações do dataset no texto que seria visto na folha.
    Retorna o texto limpo e a contagem de cada marcação encontrada."""
    contagem = {}
    for nome, padrao, substituto in REGRAS_MARCACAO:
        texto, n = padrao.subn(substituto, texto)
        contagem[nome] = n

    # remove o espaço deixado antes de pontuação
    texto = re.sub(r"\s+([.,;:!?])", r"\1", texto)

    sobras = re.findall(r"##|\$\$|@@|--", texto)
    if sobras:
        print(f"  Aviso: restaram {len(sobras)} símbolos de marcação. Confira o gabarito.")
    return texto, contagem


def normalizar(texto):
    """NFC + espaços/quebras de linha unificados (+ minúsculas, se configurado)."""
    texto = unicodedata.normalize("NFC", texto)
    if IGNORAR_MAIUSCULAS:
        texto = texto.lower()
    return re.sub(r"\s+", " ", texto).strip()


def separar_letra_e_acento(caractere):
    """'é' -> ('e', '\u0301'); 'a' -> ('a', '')."""
    decomposto = unicodedata.normalize("NFD", caractere)
    marcas = "".join(c for c in decomposto[1:] if unicodedata.category(c) == "Mn")
    return decomposto[0], marcas


def remover_acentos(texto):
    """Tira os acentos mantendo exatamente o mesmo número de caracteres."""
    return "".join(separar_letra_e_acento(c)[0] for c in texto)


def pct(parte, total):
    return round(100 * parte / total, 2) if total else None


# ======================= ACENTUAÇÃO =======================
def novo_contador():
    return {
        "total": 0, "acertos": 0, "omissoes": 0,
        "trocas": 0, "letras_erradas": 0, "acrescimos": 0,
        "por_tipo": defaultdict(lambda: {"total": 0, "acertos": 0}),
    }


def analisar_acentos(ref, hyp):
    """Alinha os textos ignorando acentos e depois confere os acentos
    nas posições em que as letras coincidem."""
    c = novo_contador()
    exemplos = []

    alinhamento = SequenceMatcher(
        None, remover_acentos(ref), remover_acentos(hyp), autojunk=False
    )

    def registrar(tipo_erro, i, j):
        exemplos.append({
            "tipo_erro": tipo_erro,
            "trecho_gabarito": ref[max(0, i - 12): i + 13],
            "trecho_modelo": hyp[max(0, j - 12): j + 13],
        })

    for tag, i1, i2, j1, j2 in alinhamento.get_opcodes():
        if tag == "equal":
            for k in range(i2 - i1):
                i, j = i1 + k, j1 + k
                marca_ref = separar_letra_e_acento(ref[i])[1]
                marca_hyp = separar_letra_e_acento(hyp[j])[1]

                if marca_ref:
                    tipo = NOMES_ACENTOS.get(marca_ref, "outro")
                    c["total"] += 1
                    c["por_tipo"][tipo]["total"] += 1
                    if marca_ref == marca_hyp:
                        c["acertos"] += 1
                        c["por_tipo"][tipo]["acertos"] += 1
                    elif not marca_hyp:
                        c["omissoes"] += 1
                        registrar("omissão", i, j)
                    else:
                        c["trocas"] += 1
                        registrar("troca", i, j)
                elif marca_hyp:
                    c["acrescimos"] += 1
                    registrar("acréscimo", i, j)

        elif tag in ("replace", "delete"):
            # a letra em si está errada ou ausente: não é problema de acento
            for i in range(i1, i2):
                marca_ref = separar_letra_e_acento(ref[i])[1]
                if marca_ref:
                    tipo = NOMES_ACENTOS.get(marca_ref, "outro")
                    c["total"] += 1
                    c["por_tipo"][tipo]["total"] += 1
                    c["letras_erradas"] += 1

    return c, exemplos


def somar_contadores(lista):
    soma = novo_contador()
    for c in lista:
        for chave in ("total", "acertos", "omissoes", "trocas", "letras_erradas", "acrescimos"):
            soma[chave] += c[chave]
        for tipo, v in c["por_tipo"].items():
            soma["por_tipo"][tipo]["total"] += v["total"]
            soma["por_tipo"][tipo]["acertos"] += v["acertos"]
    return soma


# ======================= MÉTRICAS =======================
def calcular(refs, hyps, c):
    """refs e hyps são listas de textos. Com 1 texto = métrica da redação;
    com todos = métrica global (o jiwer agrega sobre o conjunto inteiro)."""
    # TXP (jiwer.wer) vem do process_words, que também fornece acertos e inserções
    palavras = jiwer.process_words(refs, hyps)
    total_palavras = palavras.hits + palavras.substitutions + palavras.deletions

    refs_sem = [remover_acentos(t) for t in refs]
    hyps_sem = [remover_acentos(t) for t in hyps]

    return {
        "txc": round(100 * jiwer.cer(refs, hyps), 2),
        "txp": round(100 * palavras.wer, 2),
        "txc_sem_acento": round(100 * jiwer.cer(refs_sem, hyps_sem), 2),
        "acuracia_palavras": pct(palavras.hits, total_palavras),
        "palavras_inseridas": palavras.insertions,
        "total_acentos": c["total"],
        "acertos_acento": c["acertos"],
        "omissoes": c["omissoes"],
        "trocas": c["trocas"],
        "letras_erradas": c["letras_erradas"],
        "acrescimos": c["acrescimos"],
        "taxa_acerto_acento": pct(c["acertos"], c["total"]),
        "taxa_omissao": pct(c["omissoes"], c["total"]),
        "taxa_troca": pct(c["trocas"], c["total"]),
        "taxa_letra_errada": pct(c["letras_erradas"], c["total"]),
        "taxa_acrescimo": pct(c["acrescimos"], c["total"]),
    }


def resumo(linhas, nome, funcao):
    linha = {"modelo": NOME_MODELO, "arquivo": nome}
    for col in COLUNAS_TAXAS:
        valores = [l[col] for l in linhas if l[col] is not None]
        linha[col] = round(funcao(valores), 2) if valores else None
    return linha


# ======================= EXECUÇÃO =======================
def calcular_metricas_llm():
    os.makedirs(PASTA_SAIDA, exist_ok=True)
    linhas, refs, hyps, contadores, todos_exemplos = [], [], [], [], []

    for arquivo in sorted(os.listdir(PASTA_GABARITO)):
        if not arquivo.lower().endswith(".txt"):
            continue

        caminho_gabarito = os.path.join(PASTA_GABARITO, arquivo)
        caminho_resposta = os.path.join(PASTA_RESPOSTAS, arquivo)

        if not os.path.exists(caminho_resposta):
            print(f"Aviso: Resposta para {arquivo} não encontrada.")
            continue

        # Gabarito: limpa as marcações do dataset e normaliza
        bruto = ler_arquivo(caminho_gabarito)
        limpo, contagem = limpar_marcacoes(bruto)
        ref = normalizar(limpo)

        # Resposta do modelo: só normaliza (não tem marcações do dataset)
        hyp = normalizar(ler_arquivo(caminho_resposta))

        if not ref:
            print(f"Aviso: gabarito de {arquivo} está vazio. Ignorado.")
            continue

        c, exemplos = analisar_acentos(ref, hyp)
        metricas = calcular([ref], [hyp], c)

        linhas.append({"modelo": NOME_MODELO, "arquivo": arquivo, **metricas})
        refs.append(ref)
        hyps.append(hyp)
        contadores.append(c)
        for e in exemplos:
            todos_exemplos.append({"modelo": NOME_MODELO, "arquivo": arquivo, **e})

        print(f"\n{arquivo} | marcações tratadas: {contagem}")
        print(f"  TXC: {metricas['txc']}% | TXC sem acento: {metricas['txc_sem_acento']}% "
              f"| TXP: {metricas['txp']}% | Acurácia palavras: {metricas['acuracia_palavras']}%")
        print(f"  Acentos: {metricas['acertos_acento']}/{metricas['total_acentos']} certos "
              f"({metricas['taxa_acerto_acento']}%) | omitidos: {metricas['omissoes']} "
              f"| trocados: {metricas['trocas']} | letra errada: {metricas['letras_erradas']} "
              f"| acrescentados: {metricas['acrescimos']}")

    if not linhas:
        print("Nenhum arquivo avaliado.")
        return

    c_global = somar_contadores(contadores)
    linha_global = {"modelo": NOME_MODELO, "arquivo": "GLOBAL",
                    **calcular(refs, hyps, c_global)}

    print(f"\n{'-' * 50}\nGLOBAL ({len(linhas)} arquivos, textos somados)")
    print(f"  TXC: {linha_global['txc']}% | TXC sem acento: {linha_global['txc_sem_acento']}% "
          f"| TXP: {linha_global['txp']}% | Acurácia palavras: {linha_global['acuracia_palavras']}%")
    print(f"  Acerto de acentuação: {linha_global['taxa_acerto_acento']}% "
          f"({linha_global['acertos_acento']}/{linha_global['total_acentos']})")
    print("  Por tipo de acento:")
    for tipo, v in sorted(c_global["por_tipo"].items()):
        print(f"    {tipo:<12} {v['acertos']}/{v['total']} ({pct(v['acertos'], v['total'])}%)")

    media = resumo(linhas, "MEDIA", statistics.mean)
    mediana = resumo(linhas, "MEDIANA", statistics.median)
    print(f"\nMÉDIA das redações:   TXC {media['txc']}% | TXP {media['txp']}%")
    print(f"MEDIANA das redações: TXC {mediana['txc']}% | TXP {mediana['txp']}%")

    with open(os.path.join(PASTA_SAIDA, "metricas.csv"), "w", newline="", encoding="utf-8-sig") as f:
        escritor = csv.DictWriter(f, fieldnames=CABECALHO, restval="")
        escritor.writeheader()
        escritor.writerows(linhas + [media, mediana, linha_global])

    with open(os.path.join(PASTA_SAIDA, "erros_acentuacao.csv"), "w", newline="", encoding="utf-8-sig") as f:
        escritor = csv.DictWriter(
            f, fieldnames=["modelo", "arquivo", "tipo_erro", "trecho_gabarito", "trecho_modelo"]
        )
        escritor.writeheader()
        escritor.writerows(todos_exemplos)

    print(f"\nArquivos salvos em {PASTA_SAIDA}/ (metricas.csv e erros_acentuacao.csv)")


if __name__ == "__main__":
    calcular_metricas_llm()