import serial
import serial.tools.list_ports
import threading
import time
import csv
from datetime import datetime
from collections import deque
from nicegui import ui

class SupervisorioPowerQuality:
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
                import os
                
                # 1. Identifica onde este arquivo de código está rodando fisicamente
                diretorio_script = os.path.dirname(os.path.abspath(__file__))
                
                # 2. Constrói o caminho absoluto subindo até a raiz e entrando em /data/logs_csv
                # Se o arquivo estiver em software/core/, subimos dois níveis (.. / ..)
                pasta_destino = os.path.abspath(os.path.join(diretorio_script, '..', '..', 'data', 'logs_csv'))
                
                # 3. Garante que a estrutura de diretórios exista. Se não existir, o Python cria na hora.
                os.makedirs(pasta_destino, exist_ok=True)
                
                # 4. Define o nome do arquivo final acoplado ao caminho absoluto completo
                timestamp_inicio = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
                self.caminho_arquivo = os.path.join(pasta_destino, f"log_rede_{timestamp_inicio}.csv")
                
                # Abre o arquivo com segurança e a codificação correta para o Excel
                self.arquivo_log = open(self.caminho_arquivo, mode='w', newline='', encoding='utf-8-sig')
                self.escritor_csv = csv.writer(self.arquivo_log)
                self.escritor_csv.writerow(['Timestamp', 'Vrms(V)', 'Freq(Hz)', 'Fase(Deg)', 'THD(%)', 'Ruido(%)', 'H3', 'H5', 'H7', 'Status'])
                
                self.gravando = True
                ui.notify(f'Gravando dados em: {os.path.basename(self.caminho_arquivo)}', type='positive', icon='save')
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

                                # Grava os dados no .csv
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
                        self.status_msg = 'Rede com Anomalia.'
                        self.status_color = 'text-red-600'
                        self.flag_swell = True
                        self.flag_sag = False
                        self.flag_spike = False
                    elif "SAG DETECTADO" in msg:
                        self.status_msg = 'Rede com Anomalia.'
                        self.status_color = 'text-orange-600'
                        self.flag_sag = True
                        self.flag_swell = False
                        self.flag_spike = False
                    elif "SPIKE DETECTADO" in msg:
                        self.status_msg = 'Rede com Anomalia.'
                        self.status_color = 'text-pink-600'
                        self.flag_spike = True
                        self.flag_swell = False
                        self.flag_sag = False
                        self.flag_ruido = False
                    elif "DESVIO DE FREQUENCIA" in msg:
                        self.status_msg = 'Rede com Anomalia.'
                        self.status_color = 'text-indigo-600'
                        self.flag_freq = True
                    elif "SALTO DE FASE" in msg:
                        self.flag_fase = True
                    elif "DISTORCAO HARMONICA ELEVADA" in msg:
                        self.status_msg = 'Rede com Anomalia.'
                        self.status_color = 'text-red-600'
                        self.flag_thd = True
                    elif "RUIDO DE ALTA FREQUENCIA" in msg and self.flag_spike == False:
                        self.status_msg = 'Rede com Anomalia.'
                        self.status_color = 'text-orange-600'
                        self.flag_ruido = True
                    elif "REDE NORMAL" in msg and self.flag_freq == False and self.flag_fase == False and self.flag_thd == False and self.flag_ruido == False and self.flag_swell == False and self.flag_sag == False and self.flag_spike == False:
                        self.status_msg = "REDE NORMAL"
                        self.status_color = "text-green-600"
                        # Limpa as flags se a rede normalizou
                        self.flag_swell = False
                        self.flag_sag = False
                        self.flag_spike = False
                        self.flag_freq = False
                        self.flag_fase = False
                        self.flag_thd = False
                        self.flag_ruido = False

            except Exception:
                pass