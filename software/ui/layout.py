from nicegui import ui
from core.relatorio import gerar_relatorio_pdf

class ElementosUI:
    pass

def construir_interface(sup):
    ui.query('.q-page').classes('bg-zinc-800')
    el = ElementosUI()
    
    with ui.header().classes('bg-zinc-900 items-center justify-between shadow-md'):
        ui.label('ANALISADOR DE QUALIDADE DE ENERGIA - UEMA').classes('text-h6 text-bold p-2')
        with ui.row().classes('items-center bg-white/10 p-2 rounded-lg gap-4'):
            sel_baud = ui.select(options=[9600, 115200], value=115200, label='Velocidade').props('dark dense standout')
            sel_porta = ui.select(options=sup.listar_portas()+['- - - - -'], value='- - - - -', label='Porta').props('dark dense standout')
            ui.button('CONECTAR', on_click=lambda: sup.conectar(sel_porta.value, sel_baud.value)).bind_visibility_from(sup, 'conectado', backward=lambda x: not x).props('color=green-7')
            ui.button('DESCONECTAR', on_click=sup.desconectar).bind_visibility_from(sup, 'conectado').props('color=red-7')
            ui.button(on_click=sup.alternar_gravacao).bind_text_from(sup, 'gravando', backward=lambda g: 'PARAR LOG' if g else 'GRAVAR LOG').bind_visibility_from(sup, 'gravando', backward=lambda g: 'color=red-9 icon=stop' if g else 'color=blue-8 icon=save')
            ui.button('GERAR PDF', on_click=lambda: gerar_relatorio_pdf(sup.caminho_arquivo)).bind_visibility_from(sup, 'gravando', backward=lambda g: not g and sup.caminho_arquivo != "").props('color=grey-9 icon=picture_as_pdf')

    with ui.column().classes('bg-zinc-800 w-full max-w-7xl mx-auto p-4 gap-6'):
        with ui.row().classes('w-full gap-4'):
            with ui.card().classes('bg-zinc-900 flex-grow p-4 shadow-sm border-l-4 border-blue-600 items-center justify-center'):
                ui.label('DIAGNÓSTICO GERAL DA REDE').classes('text-xs font-bold text-gray-400 uppercase')
                el.lbl_status = ui.label('AGUARDANDO').classes('text-white text-2xl font-bold mt-2 text-center')

        with ui.row().classes('w-full gap-4'):
            with ui.card().classes('bg-zinc-900 flex-grow p-4 shadow-sm items-center justify-center border-l-4 border-purple-600'):
                ui.label('MONITORAMENTO DE HARMÔNICAS CRÍTICAS').classes('text-xs font-bold text-gray-400 uppercase mb-2')
                with ui.row().classes('w-full justify-around'):
                    with ui.column().classes('items-center'):
                        ui.label('3ª (180Hz)').classes('text-sm font-bold text-purple-700')
                        el.lbl_h3 = ui.label('0.0').classes('text-xl font-mono text-white')
                    with ui.column().classes('items-center'):
                        ui.label('5ª (300Hz)').classes('text-sm font-bold text-purple-700')
                        el.lbl_h5 = ui.label('0.0').classes('text-xl font-mono text-white')
                    with ui.column().classes('items-center'):
                        ui.label('7ª (420Hz)').classes('text-sm font-bold text-purple-700')
                        el.lbl_h7 = ui.label('0.0').classes('text-xl font-mono text-white')

        with ui.card().classes('w-full p-4 shadow-sm border-l-4 border-yellow-500 bg-yellow-50'):
            ui.label('SISTEMA ESPECIALISTA - SUGESTÕES DE INTERVENÇÃO TÉCNICA').classes('text-sm font-bold text-yellow-900 uppercase tracking-wider mb-2')
            el.lbl_sugestoes = ui.html('<span class="text-gray-500">Aguardando análise de dados...</span>').classes('text-base')

        with ui.row().classes('w-full grid grid-cols-5 gap-4'):
            def criar_card_metrica(titulo, cor_texto):
                with ui.card().classes('bg-zinc-900 items-center p-4 shadow-sm'):
                    ui.label(titulo).classes('text-xs font-bold text-gray-400 uppercase tracking-wider text-center')
                    return ui.label('--').classes(f'text-3xl font-mono {cor_texto} mt-2')

            el.lbl_rms = criar_card_metrica('Tensão RMS', 'text-blue-700')
            el.lbl_freq = criar_card_metrica('Frequência (Hz)', 'text-indigo-700')
            el.lbl_fase = criar_card_metrica('Salto Fase (°)', 'text-pink-700')
            el.lbl_thd = criar_card_metrica('THD Total (%)', 'text-red-700')
            el.lbl_ruido = criar_card_metrica('Ruído EMI (%)', 'text-orange-700')

        with ui.row().classes('w-full gap-4 flex-wrap'):
            with ui.column().classes('flex-grow w-2/3 gap-4'):
                with ui.card().classes('bg-zinc-900 w-full p-4 shadow-sm'):
                    ui.label('DOMÍNIO DO TEMPO (Osciloscópio)').classes('text-bold text-blue-9 text-caption')
                    el.grafico_onda = ui.echart({'animation': False, 'xAxis': {'type': 'category', 'show': False}, 'yAxis': {'type': 'value', 'min': -450, 'max': 450}, 'series': [{'data': [], 'type': 'line', 'smooth': True, 'symbol': 'none', 'areaStyle': {}, 'color': '#1976d2'}], 'grid': {'top': 10, 'bottom': 10, 'left': 45, 'right': 10}}).classes('h-40 w-full')
                with ui.card().classes('bg-zinc-900 w-full p-4 shadow-sm'):
                    ui.label('ESPECTRO DE FREQUÊNCIAS').classes('text-bold text-purple-9 text-caption')
                    el.grafico_fft = ui.echart({'animation': False, 'xAxis': {'type': 'category', 'data': sup.fft_labels, 'axisLabel': {'fontSize': 10, 'rotate': 0}}, 'yAxis': {'type': 'value', 'name': 'Mag'}, 'series': [{'type': 'bar', 'data': [], 'color': '#9c27b0', 'barWidth': '50%'}], 'grid': {'top': 30, 'bottom': 20, 'left': 45, 'right': 10}}).classes('h-40 w-full')

            with ui.column().classes('w-1/4 min-w-[250px] gap-4'):
                with ui.card().classes('bg-zinc-900 w-full p-4 shadow-sm'):
                    ui.label('PAINEL DE SIMULAÇÃO').classes('text-bold text-gray-400 text-subtitle2 mb-4 text-center')
                    with ui.column().classes('w-full gap-3'):
                        ui.label('Formas de Onda (Base):').classes('text-xs text-gray-500 font-bold')
                        ui.button('Sinal Limpo', on_click=lambda: sup.enviar('D', 2, 1)).props('outline color=blue size=sm w-full')
                        ui.button('THD Alto', on_click=lambda: sup.enviar('D', 4, 1)).props('outline color=red size=sm w-full')
                        ui.button('Ruído EMI Alto', on_click=lambda: sup.enviar('D', 12, 1)).props('outline color=orange size=sm w-full')
                        ui.separator()
                        ui.label('Injeção de Distúrbios:').classes('text-xs text-gray-500 font-bold')
                        ui.button('Gerar Swell', on_click=lambda: sup.enviar('D', 13, 1)).props('outline color=indigo size=sm w-full')
                        ui.button('Gerar Sag', on_click=lambda: sup.enviar('D', 14, 1)).props('outline color=indigo size=sm w-full')
                        ui.button('Gerar Spike', on_click=lambda: sup.enviar('D', 26, 1)).props('outline color=indigo size=sm w-full')
                        ui.separator()
                        def reset_sinal():
                            sup.enviar('D', 27, 1)
                            sup.flag_swell = sup.flag_sag = sup.flag_spike = sup.flag_freq = sup.flag_fase = sup.flag_thd = sup.flag_ruido = False
                        ui.button('RESETAR SINAL', on_click=reset_sinal).props('color=red icon=refresh w-full')
    return el