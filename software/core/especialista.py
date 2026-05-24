# --- REGRAS DO SISTEMA ESPECIALISTA ---
def motor_de_inferencia(sup):
    if not sup.conectado: return '<span class="text-gray-500">Aguardando comunicação com a placa...</span>'
    
    sugestoes = []
    
    # 1. Análise de Amplitude
    if sup.flag_swell:
        sugestoes.append("⚠️ <b>TENSÃO (SWELL):</b> Sobretensão detectada. Verifique os reguladores de tensão. Sugestão: usar um estabilizador ou filtro de linha para proteger os equipamentos conectados.")
    if sup.flag_sag:
        sugestoes.append("⚠️ <b>TENSÃO (SAG):</b> Queda de tensão. Verifique sobrecarga na instalação elétrica. Sugestão: utilizar um no-break para garantir estabilidade.")
    if sup.flag_spike:
        sugestoes.append("⚠️ <b>TRANSIENTE (SPIKE):</b> Pico de tensão detectado. Risco de dano a equipamentos sensíveis. Sugestão: Instalar DPS (Dispositivo de Proteção contra Surtos) para desviar picos e aterramento adequado.")
        
    # 2. Análise de Sincronismo
    if sup.flag_freq:
        sugestoes.append("⚠️ <b>FREQUÊNCIA:</b> Instabilidade detectada (Desvio de 60Hz). Verifique a estabilidade do sistema elétrico. Sugestão: Monitorar a estabilidade da rede e considerar o uso de no-break para cargas críticas.")
    if sup.flag_fase:
        sugestoes.append("❌ <b>CRÍTICO (FASE):</b> Salto de fase ou centelhamento detectado. Possível falha de sincronismo elétrico. Sugestão: Verificar balanceamento das fases.")
        
    # 3. Análise de DSP (Harmônicas e Ruído)
    if sup.flag_thd:
        sugestoes.append(f"⚠️ <b>HARMÔNICAS:</b> Elevado ruído harmônico (THD = {sup.thd_val}%). Presença excessiva de harmônicas ímpares. Sugestão: Utilizar filtros harmônicos.")
    if sup.flag_ruido:
        sugestoes.append("⚠️ <b>INTERFERÊNCIA EMI/RFI:</b> Ruído de alta frequência acoplado. Possível interferência eletromagnética. Sugestão: Utilizar filtros EMI/RFI (Interferência Eletromagnética/Interferência de Radiofrequência).")

    # Conclusão
    if len(sugestoes) == 0:
        return '<div class="text-green-700 font-bold">✅ REDE ESTÁVEL: Qualidade de energia dentro dos parâmetros normativos. Nenhuma intervenção de manutenção requerida no momento.</div>'
    else:
        return '<div class="text-red-700 flex flex-col gap-2">' + ''.join([f'<div>{s}</div>' for s in sugestoes]) + '</div>'