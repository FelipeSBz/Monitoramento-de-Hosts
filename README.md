# Monitoramento-de-Hosts
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

    sudo apt install fping   (ou o gerenciador de pacotes do seu sistema)
    (Tkinter já vem incluso na maioria das instalações padrão do Python)
    pip install reportlab    (apenas para gerar o relatório em PDF)

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
