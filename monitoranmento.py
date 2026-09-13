#!/usr/bin/env python3
"""
Copyright (c) 2026, Felipe da Silva Braz
Licença: GPLv3

Verificador de disponibilidade de hosts usando fping — versão com interface
gráfica Tkinter.

Formato do arquivo de hosts (hosts.csv):
    Cada linha contém dois parâmetros separados por ";":
        <ip_ou_host>;<nome_descritivo>
    Exemplo:
        192.168.0.1;Roteador principal
        8.8.8.8;DNS Google
    O primeiro parâmetro é usado pelo fping. O segundo é apenas o rótulo
    exibido junto ao IP nas áreas de hosts ONLINE/OFFLINE.

Requisitos:
    sudo apt install fping               (ou o gerenciador de pacotes do seu sistema)
    sudo apt install python3-tk          (ou o gerenciador de pacotes do seu sistema)
    sudo apt install python3-reportlab   (ou o gerenciador de pacotes do seu sistema)

Log de indisponibilidade:
    Sempre que um host for detectado como OFFLINE ou INVÁLIDO, um registro é
    adicionado ao arquivo "hosts_offline.log" (criado automaticamente na
    primeira ocorrência), no formato:
        data,hora,ip,rótulo

Relatório mensal em PDF:
    O botão "Relatório PDF" lê o arquivo "hosts_offline.log" e
    gera um PDF com uma seção por mês (os últimos N meses, configurável),
    listando cada host que ficou indisponível naquele mês e por quanto
    tempo (dias, horas e minutos), com base nos registros de log.

Uso:
    python3 monitoranmento.py
"""

import calendar
import os
import shutil
import subprocess
import threading
import tkinter as tk
from collections import OrderedDict, defaultdict
from datetime import datetime, timedelta
from tkinter import ttk, filedialog, messagebox


class MonitorHosts(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Monitor de Hosts")
        self.geometry("720x560")
        self.minsize(600, 420)

        self.hosts = {}
        self.monitorando = False
        self.job_timer = None  # id retornado por self.after, para poder cancelar
        self.arquivo_log = "hosts_offline.log"

        self._montar_ui()

    # ------------------------------------------------------------------ UI
    def _montar_ui(self):
        layout_principal = ttk.Frame(self, padding=8)
        layout_principal.pack(fill="both", expand=True)

        # --- Linha de configuração: arquivo de hosts + intervalo ---------
        config_box = ttk.LabelFrame(layout_principal, text="Configuração", padding=8)
        config_box.pack(fill="x")

        ttk.Label(config_box, text="Arquivo de hosts:").pack(side="left")
        self.var_arquivo = tk.StringVar(value="hosts.csv")
        self.campo_arquivo = ttk.Entry(config_box, textvariable=self.var_arquivo, width=40)
        self.campo_arquivo.pack(side="left", padx=(4, 4), fill="x", expand=True)

        botao_procurar = ttk.Button(config_box, text="Procurar...", command=self.escolher_arquivo)
        botao_procurar.pack(side="left", padx=(0, 12))

        ttk.Label(config_box, text="Intervalo (s):").pack(side="left")
        self.var_intervalo = tk.IntVar(value=60)
        self.campo_intervalo = ttk.Spinbox(
            config_box, from_=5, to=3600, textvariable=self.var_intervalo, width=6
        )
        self.campo_intervalo.pack(side="left", padx=(4, 0))

        ttk.Label(config_box, text="Meses no relatório:").pack(side="left", padx=(12, 0))
        self.var_meses_relatorio = tk.IntVar(value=12)
        self.campo_meses_relatorio = ttk.Spinbox(
            config_box, from_=1, to=36, textvariable=self.var_meses_relatorio, width=4
        )
        self.campo_meses_relatorio.pack(side="left", padx=(4, 0))

        # --- Botões de controle -------------------------------------------
        controle_layout = ttk.Frame(layout_principal, padding=(0, 8))
        controle_layout.pack(fill="x")

        self.botao_iniciar = ttk.Button(
            controle_layout, text="Iniciar monitoramento", command=self.alternar_monitoramento
        )
        self.botao_iniciar.pack(side="left")

        self.botao_verificar_agora = ttk.Button(
            controle_layout, text="Verificar agora", command=self.iniciar_verificacao
        )
        self.botao_verificar_agora.pack(side="left", padx=(8, 0))

        self.botao_relatorio = ttk.Button(
            controle_layout, text="Relatório PDF", command=self.gerar_relatorio_pdf
        )
        self.botao_relatorio.pack(side="left", padx=(8, 0))

        self.botao_sobre = ttk.Button(
            controle_layout, text="Sobre", command=self.mostrar_sobre
        )
        self.botao_sobre.pack(side="right")

        # --- Áreas de status: ONLINE / OFFLINE -----------------------------
        status_layout = ttk.Frame(layout_principal)
        status_layout.pack(fill="both", expand=True)

        online_box = ttk.LabelFrame(status_layout, text="Hosts ONLINE", padding=4)
        online_box.pack(side="left", fill="both", expand=True, padx=(0, 4))
        self.texto_online = tk.Text(online_box, state="disabled", wrap="word")
        self.texto_online.pack(fill="both", expand=True)

        offline_box = ttk.LabelFrame(status_layout, text="Hosts OFFLINE ou INVÁLIDOS", padding=4)
        offline_box.pack(side="left", fill="both", expand=True, padx=(4, 0))
        self.texto_offline = tk.Text(offline_box, state="disabled", wrap="word")
        self.texto_offline.pack(fill="both", expand=True)

        # --- Barra de status -------------------------------------------
        self.var_status = tk.StringVar(value="Pronto.")
        label_status = ttk.Label(layout_principal, textvariable=self.var_status, anchor="w")
        label_status.pack(fill="x", pady=(8, 0))

    # ------------------------------------------------------------- ações
    def mostrar_sobre(self):
        messagebox.showinfo(
            "Sobre",
            "Monitor de Hosts (fping)\n\n"
            "Verifica periodicamente a disponibilidade de uma lista de hosts "
            "usando o utilitário 'fping', separando-os em ONLINE e "
            "OFFLINE/INVÁLIDOS.\n\n"
            "Os hosts são lidos de um arquivo CSV (ip;rótulo), um por linha.\n\n"
            "Sempre que um host é detectado como OFFLINE/INVÁLIDO, um registro "
            "com data, hora, IP e rótulo é gravado no arquivo "
            "'hosts_offline.log' (criado automaticamente).\n\n"
            "Requisitos: fping instalado no sistema.\n\n"
            "Felipe da Silva Braz\n"
            "Copyright(c) 2026 - GPLv3",
        )

    def escolher_arquivo(self):
        caminho = filedialog.askopenfilename(
            title="Selecionar arquivo de hosts",
            filetypes=[("Arquivos CSV", "*.csv"), ("Todos", "*.*")],
        )
        if caminho:
            self.var_arquivo.set(caminho)

    def alternar_monitoramento(self):
        if self.monitorando:
            self._parar_timer()
            self.monitorando = False
            self.botao_iniciar.config(text="Iniciar monitoramento")
            self.var_status.set("Monitoramento parado.")
        else:
            if not self._validar_pre_requisitos():
                return
            self.monitorando = True
            self.botao_iniciar.config(text="Parar monitoramento")
            self.iniciar_verificacao()
            self._agendar_proxima_verificacao()

    def _agendar_proxima_verificacao(self):
        intervalo_ms = int(self.var_intervalo.get()) * 1000
        self.job_timer = self.after(intervalo_ms, self._tick_timer)

    def _tick_timer(self):
        if not self.monitorando:
            return
        self.iniciar_verificacao()
        self._agendar_proxima_verificacao()

    def _parar_timer(self):
        if self.job_timer is not None:
            self.after_cancel(self.job_timer)
            self.job_timer = None

    def _validar_pre_requisitos(self) -> bool:
        if shutil.which("fping") is None:
            messagebox.showerror(
                "Erro",
                "O 'fping' não está instalado.\n"
                "Instale-o usando seu gerenciador de pacotes (ex: sudo apt install fping).",
            )
            return False

        arquivo = self.var_arquivo.get().strip()

        if not os.path.isfile(arquivo):
            messagebox.showerror("Erro", f"O arquivo '{arquivo}' não foi encontrado.")
            return False

        return True

    def _carregar_hosts(self, arquivo: str) -> dict:
        """
        Lê o arquivo de hosts no formato 'ip;rótulo' (uma entrada por linha)
        e retorna um dicionário {ip: rótulo}. Linhas vazias, mal formatadas
        ou iniciadas com '#' são ignoradas.
        """
        hosts = {}
        with open(arquivo, "r", encoding="utf-8") as f:
            for linha in f:
                linha = linha.strip()
                if not linha or linha.startswith("#"):
                    continue
                partes = linha.split(";", 1)
                ip = partes[0].strip()
                rotulo = partes[1].strip() if len(partes) > 1 else ""
                if ip:
                    hosts[ip] = rotulo
        return hosts

    def iniciar_verificacao(self):
        if not self._validar_pre_requisitos():
            if self.monitorando:
                self._parar_timer()
                self.monitorando = False
                self.botao_iniciar.config(text="Iniciar monitoramento")
            return

        self.var_status.set("Verificando hosts...")
        self._definir_texto(self.texto_online, "")
        self._definir_texto(self.texto_offline, "")

        arquivo = self.var_arquivo.get().strip()

        try:
            self.hosts = self._carregar_hosts(arquivo)
        except OSError as erro:
            messagebox.showerror("Erro", f"Não foi possível ler o arquivo:\n{erro}")
            return

        if not self.hosts:
            self.var_status.set("Nenhum host válido encontrado no arquivo.")
            return

        # Apenas os IPs/hosts são enviados ao fping via stdin
        lista_ips = "\n".join(self.hosts.keys())

        # Executa fping -a (hosts online) e fping -u (hosts offline) em
        # threads separadas, para não travar a interface gráfica.
        self._executar_fping_async("-a", lista_ips, self.texto_online)
        self._executar_fping_async("-u", lista_ips, self.texto_offline)

    def _executar_fping_async(self, flag: str, lista_ips: str, area_texto: tk.Text):
        thread = threading.Thread(
            target=self._rodar_fping, args=(flag, lista_ips, area_texto), daemon=True
        )
        thread.start()

    def _rodar_fping(self, flag: str, lista_ips: str, area_texto: tk.Text):
        try:
            resultado = subprocess.run(
                ["fping", flag],
                input=lista_ips,
                capture_output=True,
                text=True,
            )
            saida = resultado.stdout
        except OSError as erro:
            saida = ""
            # Agenda a exibição do erro na thread principal
            self.after(0, lambda: messagebox.showerror("Erro", f"Falha ao executar fping:\n{erro}"))

        # Agenda a atualização da UI para rodar na thread principal do Tkinter
        self.after(0, self._ao_finalizar_fping, saida, area_texto)

    def _ao_finalizar_fping(self, saida: str, area_texto: tk.Text):
        linhas_formatadas = self._formatar_saida(saida)
        self._definir_texto(area_texto, linhas_formatadas or "(nenhum host encontrado)")
        self.var_status.set("Verificação concluída.")

        # Se este resultado é o do painel de hosts OFFLINE/INVÁLIDOS,
        # registra cada host indisponível no arquivo de log.
        if area_texto is self.texto_offline:
            self._registrar_log_offline(saida)

    def _registrar_log_offline(self, saida: str):
        """
        Para cada host presente na saída de 'fping -u' (hosts offline ou
        inválidos), grava uma linha no arquivo de log com data, hora, IP e
        rótulo. O arquivo é criado automaticamente caso ainda não exista
        (o modo de abertura 'a' cria o arquivo se necessário).
        """
        linhas = [linha.strip() for linha in saida.splitlines() if linha.strip()]
        if not linhas:
            return

        agora = datetime.now()
        data = agora.strftime("%Y-%m-%d")
        hora = agora.strftime("%H:%M:%S")

        registros = []
        for linha in linhas:
            ip = linha.split()[0]
            rotulo = self.hosts.get(ip, "")
            registros.append(f"{data},{hora},{ip},{rotulo}")

        try:
            with open(self.arquivo_log, "a", encoding="utf-8") as f:
                f.write("\n".join(registros) + "\n")
        except OSError as erro:
            messagebox.showerror(
                "Erro", f"Não foi possível gravar no arquivo de log:\n{erro}"
            )

    # ---------------------------------------------------- relatório em PDF
    def gerar_relatorio_pdf(self):
        """
        Ponto de entrada do botão "Relatório PDF". Valida pré-requisitos,
        pede ao usuário onde salvar o arquivo e dispara a geração em uma
        thread separada (para não travar a interface).
        """
        try:
            import reportlab  # noqa: F401
        except ImportError:
            messagebox.showerror(
                "Erro",
                "A biblioteca 'reportlab' não está instalada.\n"
                "Instale-a com: pip install reportlab",
            )
            return

        if not os.path.isfile(self.arquivo_log):
            messagebox.showinfo(
                "Relatório",
                f"O arquivo de log '{self.arquivo_log}' ainda não existe.\n"
                "Nenhuma indisponibilidade foi registrada até o momento.",
            )
            return

        try:
            quantidade_meses = int(self.var_meses_relatorio.get())
        except (tk.TclError, ValueError):
            quantidade_meses = 12
        quantidade_meses = max(1, min(quantidade_meses, 36))

        caminho_pdf = filedialog.asksaveasfilename(
            title="Salvar relatório como",
            defaultextension=".pdf",
            initialfile="relatorio_indisponibilidade.pdf",
            filetypes=[("Arquivo PDF", "*.pdf")],
        )
        if not caminho_pdf:
            return

        self.botao_relatorio.config(state="disabled")
        self.var_status.set("Gerando relatório PDF...")

        thread = threading.Thread(
            target=self._gerar_relatorio_thread,
            args=(caminho_pdf, quantidade_meses),
            daemon=True,
        )
        thread.start()

    def _gerar_relatorio_thread(self, caminho_pdf: str, quantidade_meses: int):
        erro = None
        try:
            intervalo_s = int(self.var_intervalo.get())
        except (tk.TclError, ValueError):
            intervalo_s = 60

        try:
            eventos_por_host = self._ler_log_offline(self.arquivo_log)
            meses = self._ultimos_n_meses(quantidade_meses)
            dados_por_mes = self._agrupar_por_mes(eventos_por_host, meses, intervalo_s)
            self._construir_pdf(caminho_pdf, dados_por_mes)
        except Exception as exc:  # noqa: BLE001 - queremos reportar qualquer falha na UI
            erro = str(exc)

        self.after(0, self._ao_finalizar_relatorio, caminho_pdf, erro)

    def _ao_finalizar_relatorio(self, caminho_pdf: str, erro: "str | None"):
        self.botao_relatorio.config(state="normal")
        if erro:
            self.var_status.set("Falha ao gerar relatório.")
            messagebox.showerror("Erro", f"Não foi possível gerar o relatório:\n{erro}")
            return

        self.var_status.set("Relatório PDF gerado com sucesso.")
        messagebox.showinfo("Relatório", f"Relatório gerado em:\n{caminho_pdf}")

    def _ler_log_offline(self, arquivo: str) -> dict:
        """
        Lê "hosts_offline.log" e retorna um dicionário:
            {ip: {"rotulo": str, "eventos": [datetime, ...]}}
        Cada "evento" representa um instante em que o host foi encontrado
        OFFLINE/INVÁLIDO em uma verificação. Linhas mal formatadas são
        ignoradas silenciosamente.
        """
        eventos_por_host = {}
        with open(arquivo, "r", encoding="utf-8") as f:
            for linha in f:
                linha = linha.strip()
                if not linha:
                    continue
                partes = linha.split(",", 3)
                if len(partes) < 3:
                    continue
                data, hora, ip = partes[0], partes[1], partes[2]
                rotulo = partes[3] if len(partes) > 3 else ""
                try:
                    momento = datetime.strptime(f"{data} {hora}", "%Y-%m-%d %H:%M:%S")
                except ValueError:
                    continue

                entrada = eventos_por_host.setdefault(ip, {"rotulo": rotulo, "eventos": []})
                entrada["eventos"].append(momento)
                # Mantém o rótulo mais recente não vazio encontrado no log
                if rotulo:
                    entrada["rotulo"] = rotulo
        return eventos_por_host

    def _ultimos_n_meses(self, quantidade: int) -> list:
        """
        Retorna uma lista de tuplas (ano, mes) com os últimos "quantidade"
        meses, do mais antigo para o mais recente, incluindo o mês atual.
        """
        hoje = datetime.now()
        meses = []
        ano, mes = hoje.year, hoje.month
        for _ in range(quantidade):
            meses.append((ano, mes))
            mes -= 1
            if mes == 0:
                mes = 12
                ano -= 1
        meses.reverse()
        return meses

    def _agrupar_por_mes(self, eventos_por_host: dict, meses: list, intervalo_s: int) -> "OrderedDict":
        """
        Organiza os eventos de indisponibilidade por mês e calcula, para
        cada host, o número de incidentes e o tempo total indisponível
        naquele mês.

        Como o log só registra o instante em que um host foi visto
        OFFLINE (não o instante em que ele voltou a ficar ONLINE),
        eventos consecutivos do mesmo host separados por um intervalo
        pequeno são agrupados em um único "incidente contínuo". A duração
        de cada incidente é estimada como (última - primeira detecção) +
        um intervalo de verificação, já que o host provavelmente já
        estava indisponível um pouco antes da primeira detecção e/ou
        continuou assim um pouco depois da última.
        """
        tolerancia = timedelta(seconds=max(intervalo_s * 2, 60))
        um_intervalo = timedelta(seconds=intervalo_s)

        meses_validos = set(meses)
        resultado = OrderedDict((mes_chave, {}) for mes_chave in meses)

        for ip, info in eventos_por_host.items():
            rotulo = info["rotulo"]
            eventos_ordenados = sorted(info["eventos"])

            # Agrupa os eventos em incidentes contínuos, sem cruzar a
            # fronteira do mês (um incidente pertence ao mês em que
            # ocorreu; se atravessar a virada do mês, ele é dividido).
            incidentes_por_mes = defaultdict(list)
            incidente_atual = []

            def fechar_incidente(incidente):
                if not incidente:
                    return
                inicio = incidente[0]
                fim = incidente[-1]
                duracao = (fim - inicio) + um_intervalo
                chave_mes = (inicio.year, inicio.month)
                incidentes_por_mes[chave_mes].append(duracao)

            for momento in eventos_ordenados:
                if not incidente_atual:
                    incidente_atual = [momento]
                    continue

                anterior = incidente_atual[-1]
                mesma_janela = (momento - anterior) <= tolerancia
                mesmo_mes = (momento.year, momento.month) == (anterior.year, anterior.month)

                if mesma_janela and mesmo_mes:
                    incidente_atual.append(momento)
                else:
                    fechar_incidente(incidente_atual)
                    incidente_atual = [momento]
            fechar_incidente(incidente_atual)

            for chave_mes, duracoes in incidentes_por_mes.items():
                if chave_mes not in meses_validos:
                    continue
                total_segundos = sum(d.total_seconds() for d in duracoes)
                resultado[chave_mes][ip] = {
                    "rotulo": rotulo,
                    "incidentes": len(duracoes),
                    "segundos": total_segundos,
                }

        return resultado

    @staticmethod
    def _formatar_duracao(segundos: float) -> str:
        segundos_int = int(round(segundos))
        dias, resto = divmod(segundos_int, 86400)
        horas, resto = divmod(resto, 3600)
        minutos, _ = divmod(resto, 60)

        partes = []
        if dias:
            partes.append(f"{dias} dia" + ("s" if dias != 1 else ""))
        if horas:
            partes.append(f"{horas}h")
        if minutos or not partes:
            partes.append(f"{minutos}min")
        return " ".join(partes)

    def _construir_pdf(self, caminho_pdf: str, dados_por_mes: "OrderedDict"):
        from reportlab.lib import colors
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.styles import getSampleStyleSheet
        from reportlab.lib.units import cm
        from reportlab.platypus import (
            SimpleDocTemplate,
            Paragraph,
            Spacer,
            Table,
            TableStyle,
            PageBreak,
        )

        nomes_meses = [
            "Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho",
            "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro",
        ]

        estilos = getSampleStyleSheet()
        elementos = []

        elementos.append(Paragraph("Relatório de Indisponibilidade de Hosts", estilos["Title"]))
        elementos.append(Paragraph(
            f"Gerado em {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}",
            estilos["Normal"],
        ))
        elementos.append(Spacer(1, 0.5 * cm))
        elementos.append(Paragraph(
            "Cada incidente é estimado a partir dos registros do log "
            "(hosts_offline.log). Como o log só marca o instante em que um "
            "host foi visto OFFLINE, a duração de cada incidente inclui "
            "um intervalo de verificação extra como margem de segurança.",
            estilos["Normal"],
        ))
        elementos.append(PageBreak())

        chaves_meses = list(dados_por_mes.keys())
        for indice, chave_mes in enumerate(chaves_meses):
            ano, mes = chave_mes
            titulo_mes = f"{nomes_meses[mes - 1]} de {ano}"
            elementos.append(Paragraph(titulo_mes, estilos["Heading1"]))
            elementos.append(Spacer(1, 0.3 * cm))

            hosts_mes = dados_por_mes[chave_mes]
            if not hosts_mes:
                elementos.append(Paragraph(
                    "Nenhuma indisponibilidade registrada neste mês.",
                    estilos["Normal"],
                ))
            else:
                linhas = [["Host", "Rótulo", "Incidentes", "Tempo indisponível"]]
                itens_ordenados = sorted(
                    hosts_mes.items(), key=lambda item: item[1]["segundos"], reverse=True
                )
                for ip, dados in itens_ordenados:
                    linhas.append([
                        ip,
                        dados["rotulo"] or "-",
                        str(dados["incidentes"]),
                        self._formatar_duracao(dados["segundos"]),
                    ])

                tabela = Table(linhas, colWidths=[3.5 * cm, 6 * cm, 2.5 * cm, 4 * cm], repeatRows=1)
                tabela.setStyle(TableStyle([
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#2f3b52")),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                    ("FONTSIZE", (0, 0), (-1, -1), 9),
                    ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                    ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f2f2f2")]),
                    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                    ("ALIGN", (2, 0), (2, -1), "CENTER"),
                ]))
                elementos.append(tabela)

            if indice < len(chaves_meses) - 1:
                elementos.append(PageBreak())

        documento = SimpleDocTemplate(
            caminho_pdf,
            pagesize=A4,
            leftMargin=2 * cm,
            rightMargin=2 * cm,
            topMargin=2 * cm,
            bottomMargin=2 * cm,
        )
        documento.build(elementos)

    def _definir_texto(self, area_texto: tk.Text, conteudo: str):
        area_texto.config(state="normal")
        area_texto.delete("1.0", "end")
        area_texto.insert("1.0", conteudo)
        area_texto.config(state="disabled")

    def _formatar_saida(self, saida: str) -> str:
        """
        Recebe a saída do fping (uma linha por host, contendo o IP e,
        dependendo da versão/flags, informações extras) e monta as linhas
        exibidas como "ip - rótulo", usando o dicionário self.hosts para
        buscar o rótulo correspondente a cada IP.
        """
        linhas_saida = []
        for linha in saida.splitlines():
            linha = linha.strip()
            if not linha:
                continue
            # O primeiro "token" da linha é sempre o host/IP consultado
            ip = linha.split()[0]
            rotulo = self.hosts.get(ip, "")
            if rotulo:
                linhas_saida.append(f"{ip} - {rotulo}")
            else:
                linhas_saida.append(ip)
        return "\n".join(linhas_saida)


def main():
    app = MonitorHosts()
    app.mainloop()


if __name__ == "__main__":
    main()
