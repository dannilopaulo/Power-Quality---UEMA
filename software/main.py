from nicegui import ui
from core.comunicacao import SupervisorioPowerQuality
from core.especialista import motor_de_inferencia
from ui.layout import construir_interface

# 1. Instancia o Cérebro de Comunicação
sup = SupervisorioPowerQuality()

# 2. Constrói a Interface
el = construir_interface(sup)

CORES_STATUS = 'text-gray-500 text-red-600 text-orange-600 text-green-600 text-pink-600 text-indigo-600'

# 3. Função orquestradora
def atualizar_graficos():
    if sup.conectado:
        # Puxa os dados atualizados de `sup` e injeta em `el`
        el.grafico_onda.options['series'][0]['data'] = list(sup.historico['0'])
        el.grafico_onda.update()
        el.grafico_fft.options['series'][0]['data'] = sup.fft_data
        el.grafico_fft.update()

        el.lbl_rms.set_text(sup.vrms_val)
        el.lbl_freq.set_text(sup.freq_val)
        el.lbl_fase.set_text(sup.fase_val)
        el.lbl_thd.set_text(sup.thd_val)
        el.lbl_ruido.set_text(sup.ruido_val)
        el.lbl_h3.set_text(sup.h3_val)
        el.lbl_h5.set_text(sup.h5_val)
        el.lbl_h7.set_text(sup.h7_val)
        
        el.lbl_status.set_text(sup.status_msg)
        el.lbl_status.classes(remove=CORES_STATUS, add=sup.status_color)
        
        el.lbl_sugestoes.set_content(motor_de_inferencia(sup))

# 4. Inicia o Relógio do Frontend
ui.timer(0.016, atualizar_graficos)

# 5. Roda o Servidor
ui.run(title='Power Quality - UEMA', port=8080)