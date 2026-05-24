import pandas as pd
from weasyprint import HTML
import matplotlib

from nicegui import ui
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import base64
from io import BytesIO

def gerar_relatorio_pdf(caminho_csv):
        # Carregar dados
        df = pd.read_csv(caminho_csv, encoding='utf-8-sig')

        status_repetido = ""
        linhas_tabela = []
        for _, r in df.iterrows():
            status = r['Status']
            if status != status_repetido:
                status_repetido = status
                row_class = 'red' if status != 'REDE NORMAL' else ''
                linhas_tabela.append(
                    f"<tr>"
                    f"<td>{r['Timestamp']}</td>"
                    f"<td>{r['Vrms(V)']}</td>"
                    f"<td>{r['Freq(Hz)']}</td>"
                    f"<td>{r['THD(%)']}</td>"
                    f"<td>{r['Ruido(%)']}</td>"
                    f"<td class='{row_class}'>{status}</td>"
                    f"</tr>"
                )
        rows_html = "".join(linhas_tabela)

        # Cálculos consolidados
        resumo = {
            'inicio': df['Timestamp'].iloc[0],
            'fim': df['Timestamp'].iloc[-1],
            'vrms_media': df['Vrms(V)'].mean(),
            'freq_media': df['Freq(Hz)'].mean(),
            'thd_max': df['THD(%)'].max(),
            'ruido_max': df['Ruido(%)'].max(),
            'total_falhas': df[df['Status'] != 'REDE NORMAL'].shape[0]
        }

        # --- MOTOR DE INFERÊNCIA PARA O RELATÓRIO PDF ---
        sugestoes = []
        
        if df['Vrms(V)'].max() > 242:
            sugestoes.append("<b>Tensão (Swell):</b> Sobretensão detectada. Verifique os reguladores de tensão. Sugestão: usar um estabilizador ou filtro de linha para proteger os equipamentos conectados.")
        if df['Vrms(V)'].min() < 198:
            sugestoes.append("<b>Tensão (Sag):</b> Queda de tensão. Verifique sobrecarga na instalação elétrica. Sugestão: utilizar um no-break para garantir estabilidade.")
        if df['Freq(Hz)'].max() > 60.5 or df['Freq(Hz)'].min() < 59.5:
            sugestoes.append("<b>Frequência:</b> Instabilidade detectada (Desvio de 60Hz). Verifique a estabilidade do sistema elétrico. Sugestão: Monitorar a estabilidade da rede e considerar o uso de no-break para cargas críticas.")
        if df['Fase(Deg)'].abs().max() > 5.0:
            sugestoes.append("<b>Crítico (Fase):</b> Salto de fase ou centelhamento detectado. Possível falha de sincronismo elétrico. Sugestão: Verificar balanceamento das fases.")
        if df['THD(%)'].max() > 5.0:
            sugestoes.append(f"<b>Harmônicas:</b> Elevado ruído harmônico (THD Máx = {df['THD(%)'].max():.2f}%). Presença excessiva de harmônicas ímpares. Sugestão: Utilizar filtros harmônicos.")
        if df['Ruido(%)'].max() > 0.03:
            sugestoes.append("<b>Interferência EMI/RFI:</b> Ruído de alta frequência acoplado. Possível interferência eletromagnética. Sugestão: Utilizar filtros EMI/RFI.")

        if len(sugestoes) == 0:
            bloco_sugestoes = '<div class="sugestao-box ok"><b>REDE ESTÁVEL:</b> Qualidade de energia dentro dos parâmetros normativos durante a gravação. Nenhuma intervenção técnica requerida.</div>'
        else:
            itens = "".join([f'<div class="sugestao-box alerta">{s}</div>' for s in sugestoes])
            bloco_sugestoes = f'<div class="sugestoes-container">{itens}</div>'

        # Gerar Gráficos com Subplots
        fig, (ax1, ax2, ax3, ax4) = plt.subplots(4, 1, figsize=(10, 12), sharex=True)
        fig.suptitle('Análise da Variação da Tensão(RMS), Frequência, THD e Ruído', fontsize=14, fontweight='bold', color='#1976d2')

        # Eixo X comum
        eixo_x = range(len(df))

        # --- Gráfico 1: Tensão RMS ---
        ax1.plot(eixo_x, df['Vrms(V)'], color='#1976d2', linewidth=1.5, label='Vrms')
        ax1.axhline(y=242, color='red', linestyle='--', alpha=0.6, label='Limite Swell (+10%)')
        ax1.axhline(y=198, color='orange', linestyle='--', alpha=0.6, label='Limite Sag (-10%)')
        ax1.set_ylabel('Tensão (V)')
        ax1.legend(loc='upper right', fontsize=8)
        ax1.grid(True, alpha=0.3)

        # --- Gráfico 2: Frequência ---
        ax2.plot(eixo_x, df['Freq(Hz)'], color='#8e44ad', linewidth=1.5)
        ax2.axhline(y=60.5, color='red', linestyle='--', alpha=0.3)
        ax2.axhline(y=59.5, color='red', linestyle='--', alpha=0.3)
        ax2.set_ylabel('Frequência (Hz)')
        ax2.grid(True, alpha=0.3)

        # --- Gráfico 3: THD (Distorção) ---
        ax3.plot(eixo_x, df['THD(%)'], color='#c0392b', linewidth=1.5, label='THD Total')
        ax3.fill_between(eixo_x, df['THD(%)'], color='#c0392b', alpha=0.1) # Preenchimento suave embaixo da linha
        ax3.axhline(y=5.0, color='red', linestyle='--', alpha=0.6, label='Limite (5%)')
        ax3.set_ylabel('THD (%)')
        ax3.grid(True, alpha=0.3)

        # --- Grafico 4: Ruído ---
        ax4.plot(eixo_x, df['Ruido(%)'], color='#d35400', linewidth=1.5, label='Ruído EMI')
        ax4.fill_between(eixo_x, df['Ruido(%)'], color='#d35400', alpha=0.1) # Preenchimento suave embaixo da linha
        ax4.axhline(y=0.03, color='red', linestyle='--', alpha=0.6, label='Limite (0.03%)')
        ax4.set_ylabel('Ruído (%)')
        ax4.set_xlabel('Amostras Registradas ao Longo do Tempo')
        ax4.legend(loc='upper right', fontsize=8)

        # Ajusta o espaçamento para não sobrepor os textos
        plt.tight_layout()
        fig.subplots_adjust(top=0.92) # Dá espaço para o título principal

        # Salva na memória RAM
        buf = BytesIO()
        plt.savefig(buf, format='png', dpi=120, bbox_inches='tight')
        graph_base64 = base64.b64encode(buf.getvalue()).decode('utf-8')
        
        # Fechar a figura para liberar a memória RAM
        plt.close(fig)

        # Criar o HTML do Relatório
        html_content = f"""
        <html>
        <head>
            <style>
                @page {{ size: A4; margin: 20mm; }}
                body {{ font-family: times new roman; color: #333; }}
                .header {{ text-align: center; border-bottom: 2px solid #1976d2; padding-bottom: 10px; }}
                .stats-grid {{ display: table; width: 100%; margin: 20px 0; }}
                .stat-box {{ display: table-cell; padding: 15px; border: 1px solid #ddd; text-align: center; }}
                .stat-val {{ font-size: 18px; font-weight: bold; color: #1976d2; }}
                table {{ width: 100%; border-collapse: collapse; margin-top: 20px; }}
                th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; font-size: 10px; }}
                th {{ background-color: #f2f2f2; }}
                .red {{ color: red; font-weight: bold; }}
            </style>
        </head>
        <body>
            <div class="header">
                <h1>Relatório de Qualidade de Energia</h1>
                <p>Universidade Estadual do Maranhão</p>
                <p>Engenharia de Computação</p>
            </div>
            
            <h3>Resumo do Período</h3>
            <div class="stats-grid">
                <div class="stat-box">Início<br><span class="stat-val">{resumo['inicio']}</span></div>
                <div class="stat-box">Fim<br><span class="stat-val">{resumo['fim']}</span></div>
            </div>  
            <div class="stats-grid">
                <div class="stat-box">Vrms Médio<br><span class="stat-val">{resumo['vrms_media']:.2f} V</span></div>
                <div class="stat-box">Frequência<br><span class="stat-val">{resumo['freq_media']:.2f} Hz</span></div>
                <div class="stat-box">THD Máximo<br><span class="stat-val">{resumo['thd_max']:.2f} %</span></div>
                <div class="stat-box">Ruído Máximo<br><span class="stat-val">{resumo['ruido_max']:.2f} %</span></div>
                <div class="stat-box">Total de Anomalias<br><span class="stat-val">{resumo['total_falhas']}</span></div>
            </div>

            <h3>Log de Eventos e Anomalias</h3>
            <table>
                <thead>
                    <tr>
                        <th>Timestamp</th><th>Vrms</th><th>Frequência</th><th>THD</th><th>Ruído</th><th>Status</th>
                    </tr>
                </thead>
                <tbody>
                    {rows_html}
                </tbody>
            </table>

            <h3>Sistema Especialista: Sugestões de Intervenção</h3>
            {bloco_sugestoes}

            <h3>Análise Gráfica</h3>
            <div class="chart-container">
                <img src="data:image/png;base64,{graph_base64}" style="width: 100%;">
            </div>

        </body>
        </html>
        """

        # 1. Importa o módulo operacional do sistema
        import os

        # 2. Extrai apenas o nome do arquivo CSV (ex: "log_rede_2026-05-24_19-40-35.csv")
        nome_base_csv = os.path.basename(caminho_csv)
        nome_base_pdf = nome_base_csv.replace('.csv', '.pdf')

        # 3. Identifica a pasta onde este código está rodando (software/core/)
        diretorio_script = os.path.dirname(os.path.abspath(__file__))

        # 4. Constrói o caminho absoluto para a pasta de relatórios (subindo e entrando em /data/relatorios_pdf)
        pasta_pdfs = os.path.abspath(os.path.join(diretorio_script, '..', '..', 'data', 'relatorios_pdf'))

        # 5. Garante que a pasta 'relatorios_pdf' exista fisicamente no disco
        os.makedirs(pasta_pdfs, exist_ok=True)

        # 6. Combina a pasta com o nome do arquivo para gerar o caminho absoluto final do PDF
        output_pdf = os.path.join(pasta_pdfs, nome_base_pdf)

        # 7. Executa a conversão e escrita do arquivo no local correto
        HTML(string=html_content).write_pdf(output_pdf)
        
        # Notificação visual de sucesso para o usuário na interface
        ui.notify(f'Relatório PDF gerado em: data/relatorios_pdf/{nome_base_pdf}', type='positive', icon='picture_as_pdf')
        
        return output_pdf