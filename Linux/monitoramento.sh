#!/usr/bin/env bash
#
# monitoramento.sh
# Script para verificar dependências e executar o "Monitor de Hosts"
# (monitoramento.py).
#
# Uso:
#   ./monitoramento.sh
#
# Opcional: coloque este script na mesma pasta do arquivo monitoramento.py,
# ou ajuste a variável SCRIPT_PYTHON abaixo.

set -euo pipefail

# --- Configurações -----------------------------------------------------
DIR_ATUAL="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SCRIPT_PYTHON="${DIR_ATUAL}/monitoramento.py"

echo "=== Monitor de Hosts - script de execução ==="

# --- 1) Verifica se o arquivo Python existe -----------------------------
if [[ ! -f "${SCRIPT_PYTHON}" ]]; then
    echo "Erro: não encontrei '${SCRIPT_PYTHON}'."
    echo "Coloque este script na mesma pasta do monitoramento.py, ou edite a variável SCRIPT_PYTHON."
    exit 1
fi

# --- 2) Verifica se o python3 está instalado -----------------------------
if ! command -v python3 >/dev/null 2>&1; then
    echo "Erro: python3 não está instalado."
    echo "Instale com: sudo apt install python3"
    exit 1
fi

# --- 3) Verifica se o Tkinter está disponível ----------------------------
if ! python3 -c "import tkinter" >/dev/null 2>&1; then
    echo "Aviso: o módulo 'tkinter' não foi encontrado."
    echo "Instale com: sudo apt install python3-tk"
    exit 1
fi

# --- 4) Verifica se o reportlab está instalado ---------------------------
if ! python3 -c "import reportlab" >/dev/null 2>&1; then
    echo "Aviso: o módulo 'reportlab' não foi encontrado (necessário para o Relatório PDF)."
    echo "Instale com: sudo apt install python3-reportlab"
    echo "  (ou: pip3 install reportlab)"
    exit 1
fi

# --- 5) Verifica se o fping está instalado -------------------------------
if ! command -v fping >/dev/null 2>&1; then
    echo "Aviso: o utilitário 'fping' não foi encontrado (necessário para checar os hosts)."
    echo "Instale com: sudo apt install fping"
    exit 1
fi

# --- 6) Executa o programa -----------------------------------------------
echo "Todas as dependências foram encontradas. Iniciando o programa..."
cd "${DIR_ATUAL}"
exec python3 "${SCRIPT_PYTHON}"
