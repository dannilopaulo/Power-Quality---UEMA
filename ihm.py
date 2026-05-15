from nicegui import ui
import serial
import serial.tools.list_ports
import threading
import time
import csv  # Para manipulação de arquivos locais
from datetime import datetime # Para timestamps precisos
from collections import deque

class SupervisorioEduardo:
    def __init__(self):
        self.ser = None
        self.conectado = False
        self.running = False

        # Atributos de Gravação (DATALOGGER)
        self.gravando = False
        self.arquivo_log = None
        self.escritor_csv = None
        self.caminho_arquivo = ""
        
        # Dados do Gráfico de Linha
        self.dados_analog = {'0': 0}
        self.historico = {'0': deque([0]*150, maxlen=150)}

        # Dados do Gráfico FFT (O ESP32 envia 15 Bins: do Bin 1 ao Bin 15)
        # Índice 0 = 60Hz, Índice 2 = 180Hz (3ª), Índice 4 = 300Hz (5ª), Índice 6 = 420Hz (7ª)
        self.fft_labels = [f"{i*60}Hz" for i in range(1, 16)]
        self.fft_data = [0.0] * 15 
        
        # Variáveis de Memória das Grandezas Principais
        self.vrms_val = "0.00"
        self.freq_val = "0.00"
        self.fase_val = "0.0"
        self.thd_val  = "0.00"
        self.ruido_val = "0.0000"
        
        # Variáveis de Extração Harmônica
        self.h3_val = "0.0"
        self.h5_val = "0.0"
        self.h7_val = "0.0"
        
        # Status Unificado do Sistema
        self.status_msg   = "SISTEMA PRONTO - AGUARDANDO DADOS"
        self.status_color = "text-gray-500"
        
        # Variáveis exclusivas para a Árvore de Decisão
        self.flag_swell = False
        self.flag_sag = False
        self.flag_spike = False
        self.flag_freq = False
        self.flag_fase = False
        self.flag_thd = False
        self.flag_ruido = False

    def listar_portas(self):
        return [p.device for p in serial.tools.list_ports.comports()]

    # Lógica de Gravação de Dados (DATALOGGER)
    def alternar_gravacao(self):
        if not self.gravando:
            try:
                # Cria nome de arquivo único baseado na data e hora atual
                timestamp_inicio = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
                self.caminho_arquivo = f"log_rede_{timestamp_inicio}.csv"
                
                # Abre o arquivo e escreve o cabeçalho
                self.arquivo_log = open(self.caminho_arquivo, mode='w', newline='')
                self.escritor_csv = csv.writer(self.arquivo_log)
                self.escritor_csv.writerow(['Timestamp', 'Vrms(V)', 'Freq(Hz)', 'Fase(Deg)', 'THD(%)', 'Ruido(%)', 'H3', 'H5', 'H7', 'Status'])
                
                self.gravando = True
                ui.notify(f'Gravando dados em: {self.caminho_arquivo}', type='positive', icon='save')
            except Exception as e:
                ui.notify(f'Erro ao criar arquivo: {e}', type='negative')
        else:
            self.gravando = False
            if self.arquivo_log:
                self.arquivo_log.close()
                self.arquivo_log = None
            ui.notify(f'Gravação encerrada. Arquivo salvo.', type='info', icon='file_download')
        
    def conectar(self, porta, baud):
        try:
            self.ser = serial.serial_for_url(porta, baudrate=baud, timeout=0.1)
            time.sleep(0.1)
            self.ser.reset_input_buffer()
            self.running = True
            self.conectado = True
            threading.Thread(target=self.thread_leitura, daemon=True).start()
            ui.notify(f'Conectado: {porta} @ {baud}', type='positive')
        except Exception as e:
            ui.notify(f'Erro: {e}', type='negative')

    def desconectar(self):
        self.running = False
        self.conectado = False
        if self.ser: self.ser.close()
        ui.notify('Conexão Serial Encerrada', type='warning')

    def enviar(self, tipo, pino, valor):
        if self.ser and self.ser.is_open:
            self.ser.write(f"{tipo}:{pino}:{valor}\n".encode())

    def thread_leitura(self):
        while self.running:
            try:
                if self.ser and self.ser.in_waiting:
                    msg = self.ser.readline().decode().strip()
                    
                    # 1. Dados Analógicos (Osciloscópio)
                    if msg.startswith("A:"):
                        partes = msg.split(":")
                        if len(partes) >= 3:
                            ch, val = partes[1], int(partes[2])
                            self.dados_analog[ch] = val
                            self.historico[ch].append(val)
                            
                    # 2. Leitura de Grandezas Numéricas
                    elif msg.startswith("Vrms:"):
                        self.vrms_val = msg.split(":")[1].strip()
                    elif msg.startswith("Freq:"):
                        self.freq_val = msg.split("Freq:")[1].strip()
                    elif msg.startswith("Fase:"):
                        self.fase_val = msg.split("Fase:")[1].strip()
                    elif msg.startswith("THD:"):
                        self.thd_val = msg.split("THD:")[1].strip()
                    elif msg.startswith("RuidoFFT:"):
                        self.ruido_val = msg.split("RuidoFFT:")[1].strip()

                    # 3. Captura do Espectro FFT e Extração das Harmônicas (3ª, 5ª e 7ª)
                    elif msg.startswith("FFT:"):
                        try:
                            valores_str = msg.split("FFT:")[1].strip().split(",")
                            self.fft_data = [float(v) for v in valores_str]
                            
                            # Extrai os valores das harmônicas exigidas
                            if len(self.fft_data) >= 7:
                                self.h3_val = f"{self.fft_data[2]:.1f}" # Índice 2 = 3 * 60Hz = 180Hz
                                self.h5_val = f"{self.fft_data[4]:.1f}" # Índice 4 = 5 * 60Hz = 300Hz
                                self.h7_val = f"{self.fft_data[6]:.1f}" # Índice 6 = 7 * 60Hz = 420Hz

                                # Grava os dados no CSV
                                # Registramos uma linha sempre que um novo ciclo de FFT é completado (fim do ciclo)
                                if self.gravando and self.escritor_csv:
                                    agora = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
                                    self.escritor_csv.writerow([
                                        agora, self.vrms_val, self.freq_val, self.fase_val, 
                                        self.thd_val, self.ruido_val, self.h3_val, self.h5_val, 
                                        self.h7_val, self.status_msg
                                    ])
                                    self.arquivo_log.flush()
                        except: pass
                        
                    # Mapeamento Booleano para a Árvore de Decisão
                    if "SWELL DETECTADO" in msg:
                        self.status_msg = 'Alerta para Manutenção'
                        self.status_color = 'text-red-600'
                        self.flag_swell = True
                        self.flag_sag = False
                        self.flag_spike = False
                    elif "SAG DETECTADO" in msg:
                        self.status_msg = 'Alerta para Manutenção'
                        self.status_color = 'text-orange-600'
                        self.flag_sag = True
                        self.flag_swell = False
                        self.flag_spike = False
                    elif "SPIKE DETECTADO" in msg:
                        self.status_msg = 'Alerta para Manutenção'
                        self.status_color = 'text-pink-600'
                        self.flag_spike = True
                        self.flag_swell = False
                        self.flag_sag = False
                    elif "DESVIO DE FREQUENCIA" in msg:
                        self.status_msg = 'Alerta para Manutenção'
                        self.status_color = 'text-indigo-600'
                        self.flag_freq = True
                    elif "SALTO DE FASE" in msg:
                        self.status_msg = 'Alerta para Manutenção'
                        self.status_color = 'text-purple-600'
                        self.flag_fase = True
                    elif "DISTORCAO HARMONICA ELEVADA" in msg:
                        self.status_msg = 'Alerta para Manutenção'
                        self.status_color = 'text-red-600'
                        self.flag_thd = True
                    elif "RUIDO DE ALTA FREQUENCIA" in msg:
                        self.status_msg = 'Alerta para Manutenção'
                        self.status_color = 'text-orange-600'
                        self.flag_ruido = True
                    elif "REDE NORMAL" in msg and self.flag_freq == False and self.flag_fase == False and self.flag_thd == False and self.flag_ruido == False and self.flag_swell == False:
                        self.status_msg = "REDE NORMAL"
                        self.status_color = "text-green-600"
                        # Limpa as flags se a rede normalizou
                        self.flag_swell = False
                        self.flag_sag = False
                        self.flag_freq = False
                        self.flag_fase = False
                        self.flag_thd = False
                        self.flag_ruido = False

            except Exception:
                pass

sup = SupervisorioEduardo()

# --- INTERFACE DE USUÁRIO (UI) ---
ui.query('.q-page').classes('bg-slate-200')

# 1. CABEÇALHO
with ui.header().classes('bg-zinc-900 items-center justify-between shadow-md'):
    ui.label('ANALISADOR DE QUALIDADE DE ENERGIA - UEMA').classes('text-h6 text-bold p-2')
    
    with ui.row().classes('items-center bg-white/10 p-2 rounded-lg gap-4'):
        sel_baud = ui.select(options=[9600, 115200], value=115200, label='Velocidade').props('dark dense standout')
        opcoes_porta = sup.listar_portas() + ['socket://127.0.0.1:31415']
        sel_porta = ui.select(options=opcoes_porta, value='socket://127.0.0.1:31415', label='Porta').props('dark dense standout')
        
        ui.button('CONECTAR', on_click=lambda: sup.conectar(sel_porta.value, sel_baud.value))\
            .bind_visibility_from(sup, 'conectado', backward=lambda x: not x).props('color=green-7')
        ui.button('DESCONECTAR', on_click=sup.desconectar)\
            .bind_visibility_from(sup, 'conectado').props('color=red-7')
        ui.button(on_click=sup.alternar_gravacao)\
            .bind_text_from(sup, 'gravando', backward=lambda g: 'PARAR LOG' if g else 'GRAVAR LOG')\
            .bind_visibility_from(sup, 'gravando', backward=lambda g: 'color=red-9 icon=stop' if g else 'color=blue-8 icon=save')

# Container Principal
with ui.column().classes('w-full max-w-7xl mx-auto p-4 gap-6'):
    
    # 1. PAINEL DE DIAGNÓSTICO E HARMÔNICAS
    with ui.row().classes('w-full gap-4'):
        # Status Geral
        with ui.card().classes('flex-grow p-4 shadow-sm border-l-4 border-blue-600 items-center justify-center'):
            ui.label('DIAGNÓSTICO GERAL DA REDE').classes('text-xs font-bold text-gray-500 uppercase')
            lbl_status = ui.label('AGUARDANDO').classes('text-2xl font-bold mt-2 text-center')

        # Monitoramento das Harmônicas Específicas do Professor
        with ui.card().classes('w-1/2 p-4 shadow-sm'):
            ui.label('MONITORAMENTO DE HARMÔNICAS CRÍTICAS').classes('text-xs font-bold text-gray-500 uppercase mb-2')
            with ui.row().classes('w-full justify-around'):
                with ui.column().classes('items-center'):
                    ui.label('3ª (180Hz)').classes('text-sm font-bold text-purple-700')
                    lbl_h3 = ui.label('0.0').classes('text-xl font-mono')
                with ui.column().classes('items-center'):
                    ui.label('5ª (300Hz)').classes('text-sm font-bold text-purple-700')
                    lbl_h5 = ui.label('0.0').classes('text-xl font-mono')
                with ui.column().classes('items-center'):
                    ui.label('7ª (420Hz)').classes('text-sm font-bold text-purple-700')
                    lbl_h7 = ui.label('0.0').classes('text-xl font-mono')

    # 2. SISTEMA ESPECIALISTA (ÁRVORE DE DECISÃO) - NOVO RECURSO EXIGIDO
    with ui.card().classes('w-full p-4 shadow-sm border-l-4 border-yellow-500 bg-yellow-50'):
        ui.label('SISTEMA ESPECIALISTA - SUGESTÕES DE INTERVENÇÃO TÉCNICA').classes('text-sm font-bold text-yellow-900 uppercase tracking-wider mb-2')
        lbl_sugestoes = ui.html('<span class="text-gray-500">Aguardando análise de dados...</span>').classes('text-base')

    # 3. MÉTRICAS PRINCIPAIS
    with ui.row().classes('w-full grid grid-cols-5 gap-4'):
        def criar_card_metrica(titulo, cor_texto):
            with ui.card().classes('items-center p-4 shadow-sm'):
                ui.label(titulo).classes('text-xs font-bold text-gray-500 uppercase tracking-wider text-center')
                lbl_valor = ui.label('--').classes(f'text-3xl font-mono {cor_texto} mt-2')
            return lbl_valor

        lbl_rms   = criar_card_metrica('Tensão RMS', 'text-blue-700')
        lbl_freq  = criar_card_metrica('Frequência (Hz)', 'text-indigo-700')
        lbl_fase  = criar_card_metrica('Salto Fase (°)', 'text-pink-700')
        lbl_thd   = criar_card_metrica('THD Total (%)', 'text-red-700')
        lbl_ruido = criar_card_metrica('Ruído EMI (%)', 'text-orange-700')

    # 4. GRÁFICOS E SIMULADOR
    with ui.row().classes('w-full gap-4 flex-wrap'):
        with ui.column().classes('flex-grow w-2/3 gap-4'):
            
            # Osciloscópio
            with ui.card().classes('w-full p-4 shadow-sm'):
                ui.label('DOMÍNIO DO TEMPO (Osciloscópio)').classes('text-bold text-blue-9 text-caption')
                grafico_onda = ui.echart({
                    'animation': False,
                    'xAxis': {'type': 'category', 'show': False},
                    'yAxis': {'type': 'value', 'min': -450, 'max': 450},
                    'series': [{'data': list(sup.historico['0']), 'type': 'line', 'smooth': True, 'symbol': 'none', 'areaStyle': {}, 'color': '#1976d2'}],
                    'grid': {'top': 10, 'bottom': 10, 'left': 45, 'right': 10}
                }).classes('h-40 w-full')

            # Espectro FFT
            with ui.card().classes('w-full p-4 shadow-sm'):
                ui.label('ESPECTRO DE FREQUÊNCIAS (Transformada Rápida de Fourier)').classes('text-bold text-purple-9 text-caption')
                grafico_fft = ui.echart({
                    'animation': False, 
                    'xAxis': {'type': 'category', 'data': sup.fft_labels, 'axisLabel': {'fontSize': 10, 'rotate': 0}},
                    'yAxis': {'type': 'value', 'name': 'Mag'},
                    'series': [{'type': 'bar', 'data': sup.fft_data, 'color': '#9c27b0', 'barWidth': '50%'}],
                    'grid': {'top': 30, 'bottom': 20, 'left': 45, 'right': 10}
                }).classes('h-40 w-full')

        # Coluna do Simulador de Anomalias (Simulação de Formas de Onda e Injeção de Distúrbios)
        with ui.column().classes('w-1/4 min-w-[250px] gap-4'):
            with ui.card().classes('w-full p-4 shadow-sm bg-slate-50'):
                ui.label('PAINEL DE SIMULAÇÃO').classes('text-bold text-slate-800 text-subtitle2 mb-4 text-center')
                
                with ui.column().classes('w-full gap-3'):
                    ui.label('Formas de Onda (Base):').classes('text-xs text-gray-500 font-bold')
                    ui.button('Sinal Limpo', on_click=lambda: sup.enviar('D', 2, 1)).props('outline color=blue size=sm w-full')
                    ui.button('THD Alto', on_click=lambda: sup.enviar('D', 4, 1)).props('outline color=red size=sm w-full')
                    ui.button('Ruído EMI Alto', on_click=lambda: sup.enviar('D', 12, 1)).props('outline color=orange size=sm w-full')
                    
                    ui.separator()
                    
                    ui.label('Injeção de Distúrbios:').classes('text-xs text-gray-500 font-bold')
                    ui.button('Gerar Swell (Sobretensão)', on_click=lambda: sup.enviar('D', 13, 1)).props('outline color=indigo size=sm w-full')
                    ui.button('Gerar Sag (Queda)', on_click=lambda: sup.enviar('D', 14, 1)).props('outline color=indigo size=sm w-full')
                    ui.button('Gerar Spike (Transiente)', on_click=lambda: sup.enviar('D', 26, 1)).props('outline color=indigo size=sm w-full')
                    
                    ui.separator()
                    
                    # Botão Mestre de Reset
                    def reset_sinal():
                        sup.enviar('D', 27, 1)
                        sup.flag_swell = False
                        sup.flag_sag = False
                        sup.flag_freq = False
                        sup.flag_fase = False
                        sup.flag_thd = False
                        sup.flag_ruido = False
                    ui.button('RESETAR SINAL', on_click=reset_sinal).props('color=red icon=refresh w-full')

# --- REGRAS DO SISTEMA ESPECIALISTA ---
def motor_de_inferencia():
    if not sup.conectado: return '<span class="text-gray-500">Aguardando comunicação com a placa...</span>'
    
    sugestoes = []
    
    # 1. Análise de Amplitude
    if sup.flag_swell:
        sugestoes.append("⚠️ <b>TENSÃO (SWELL):</b> Sobretensão detectada. Sugestão de Intervenção Tecnica")
    if sup.flag_sag:
        sugestoes.append("⚠️ <b>TENSÃO (SAG):</b> Queda de tensão. Sugestão de Intervenção Tecnica")
    if sup.flag_spike:
        sugestoes.append("⚠️ <b>TRANSIENTE (SPIKE):</b> Pico de tensão detectado. Sugestão de Intervenção Tecnica")
        
    # 2. Análise de Sincronismo
    if sup.flag_freq:
        sugestoes.append("⚠️ <b>FREQUÊNCIA:</b> Instabilidade detectada (Desvio de 60Hz). Sugestão de Intervenção Tecnica")
    if sup.flag_fase:
        sugestoes.append("❌ <b>CRÍTICO (FASE):</b> Salto de fase ou centelhamento detectado. Sugestão de Intervenção Tecnica")
        
    # 3. Análise de DSP (Harmônicas e Ruído)
    if sup.flag_thd:
        sugestoes.append(f"⚠️ <b>HARMÔNICAS:</b> Elevado ruído harmônico (THD = {sup.thd_val}%). Sugestão de Intervenção Tecnica")
    if sup.flag_ruido:
        sugestoes.append("⚠️ <b>INTERFERÊNCIA EMI/RFI:</b> Ruído de alta frequência acoplado. Sugestão de Intervenção Tecnica")

    # Conclusão
    if len(sugestoes) == 0:
        return '<div class="text-green-700 font-bold">✅ REDE ESTÁVEL: Qualidade de energia dentro dos parâmetros normativos. Nenhuma intervenção de manutenção requerida no momento.</div>'
    else:
        return '<div class="text-red-700 flex flex-col gap-2">' + ''.join([f'<div>{s}</div>' for s in sugestoes]) + '</div>'


CORES_STATUS = 'text-gray-500 text-red-600 text-orange-600 text-green-600'

def atualizar_graficos():
    if sup.conectado:
        # Atualiza Gráficos
        grafico_onda.options['series'][0]['data'] = list(sup.historico['0'])
        grafico_onda.update()

        grafico_fft.options['series'][0]['data'] = sup.fft_data
        grafico_fft.update()

        # Atualiza as Métricas
        lbl_rms.set_text(sup.vrms_val)
        lbl_freq.set_text(sup.freq_val)
        lbl_fase.set_text(sup.fase_val)
        lbl_thd.set_text(sup.thd_val)
        lbl_ruido.set_text(sup.ruido_val)
        
        # Atualiza Harmônicas Específicas
        lbl_h3.set_text(sup.h3_val)
        lbl_h5.set_text(sup.h5_val)
        lbl_h7.set_text(sup.h7_val)
        
        # Atualiza Status Unificado
        lbl_status.set_text(sup.status_msg)
        lbl_status.classes(remove=CORES_STATUS, add=sup.status_color)
        
        # Executa a Árvore de Decisão
        lbl_sugestoes.set_content(motor_de_inferencia())

ui.timer(0.016, atualizar_graficos)
ui.run(title='Power Quality - UEMA', port=8080)