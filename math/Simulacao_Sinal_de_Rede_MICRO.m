%% GERADOR DE SINAIS PARA EMULAÇÃO NO WOKWI (ESP32)
% Projeto: Analisador de Qualidade de Energia
% Descrição: Este script modela a rede elétrica de 220V e gera os arrays 
%            C++ que simulam o sinal lido pelo ADC do ESP32.
clc; close all; clear all;

%% 1. PARÂMETROS DO SISTEMA E AMOSTRAGEM
f_fundamental = 60;      % Frequência esperada da rede elétrica (Hz)
pontos_por_ciclo = 128;  % Amostras por ciclo (para a FFT)
amostras = pontos_por_ciclo; 

% Eixo do tempo para exatamente 1 ciclo (16.66 ms)
% Remove o último ponto para a onda conectar perfeitamente no loop infinito
t = linspace(0, 1/f_fundamental, amostras + 1);
t(end) = []; 

%% 2. MODELAGEM MATEMÁTICA DAS AMPLITUDES (Tensão de Pico)
A1 = 311; % Fundamental 60Hz (220V * sqrt(2))
A3 = 60;  % 3ª Harmônica (180Hz) - Causa aquecimento no neutro
A5 = 30;  % 5ª Harmônica (300Hz)
A7 = 15;  % 7ª Harmônica (420Hz)
A_Ruido = 10; % Ruído de Alta Frequência (Ex: 3600Hz de fontes chaveadas)

%% 3. GERAÇÃO DOS SINAIS DE TESTE (Domínio do Tempo)
% Cenário 1: Rede Perfeita
sinal_limpo = A1 * sin(2*pi * f_fundamental * t);

% Cenário 2: Distorção Harmônica Elevada (THD)
sinal_thd = sinal_limpo + ...
            A3 * sin(2*pi * (3*f_fundamental) * t) + ...
            A5 * sin(2*pi * (5*f_fundamental) * t) + ...
            A7 * sin(2*pi * (7*f_fundamental) * t);

% Cenário 3: Ruído Acoplado (EMI/RFI)
sinal_ruido = sinal_limpo + A_Ruido * sin(2*pi * (60*f_fundamental) * t);

%% 4. QUANTIZAÇÃO PARA O ADC DO ESP32 (12-bits)
% O circuito físico possui offset de 1.65V (Valor 2048 no ADC)
offset_adc = 2048;

% Função anônima para converter Tensão Real -> Leitura ADC com limites
converter_adc = @(sinal) max(min(round(sinal + offset_adc), 4095), 0);

adc_limpo = converter_adc(sinal_limpo);
adc_thd   = converter_adc(sinal_thd);
adc_ruido = converter_adc(sinal_ruido);

%% 5. Geração do Código C++ no Console
fprintf('\n// COPIE E COLE OS ARRAYS ABAIXO NO SEU SKETCH.INO (BLOCO 1)\n');
fprintf('// ====================================================================\n\n');

% Exporta Sinal Limpo
fprintf('const int sinal_rede_Limpo[%d]      = {', amostras);
fprintf('%d, ', adc_limpo(1:end-1)); fprintf('%d};\n', adc_limpo(end));

% Exporta Sinal com THD
fprintf('const int sinal_rede_THD_Alto[%d]   = {', amostras);
fprintf('%d, ', adc_thd(1:end-1)); fprintf('%d};\n', adc_thd(end));

% Exporta Sinal com Ruído
fprintf('const int sinal_rede_Ruido_Alto[%d] = {', amostras);
fprintf('%d, ', adc_ruido(1:end-1)); fprintf('%d};\n\n', adc_ruido(end));


%% 6. VALIDAÇÃO MATEMÁTICA DO ALGORITMO (PROVA REAL DA FFT)
% Esta seção prova que a lógica implementada em C++ no ESP32 está correta.
fprintf('// --- VALIDAÇÃO DA FFT (MATLAB vs ESP32) ---\n');

% Janelamento e FFT no sinal com THD
janela = hamming(amostras)';
vReal_windowed = sinal_thd .* janela;
vFFT = fft(vReal_windowed);

% Conversão para Magnitude e Normalização
vMag = abs(vFFT) * (2 / amostras); 

% Extração dos Bins de interesse (No MATLAB o índice começa em 1, logo Bin[1] é idx 2)
ampFund = vMag(2); % 60Hz
ampH3   = vMag(4); % 180Hz
ampH5   = vMag(6); % 300Hz
ampH7   = vMag(8); % 420Hz

% Cálculo do THD
thd_calculado = (sqrt(ampH3^2 + ampH5^2 + ampH7^2) / ampFund) * 100;

fprintf('// Fundamental (60Hz): %.2f V\n', ampFund);
fprintf('// THD Calculado:      %.2f %%\n', thd_calculado);
if thd_calculado > 5.0
    fprintf('// DIAGNÓSTICO:        ALERTA (THD > 5%%)\n');
end

%% 7. VISUALIZAÇÃO GRÁFICA
figure('Name', 'Análise de Sinais Gerados', 'Position', [100, 100, 900, 600]);

% Gráfico 1: Sinais no Tempo (Visão do Osciloscópio)
subplot(2,1,1);
hold on;
plot(t*1000, sinal_limpo, 'g', 'LineWidth', 2);
plot(t*1000, sinal_thd, 'r', 'LineWidth', 1.5);
plot(t*1000, sinal_ruido, 'b', 'LineWidth', 1);
hold off;
title('Sinais de Energia Simulados (Domínio do Tempo)');
xlabel('Tempo (ms)'); ylabel('Tensão (V)');
legend('Sinal Limpo', 'Sinal com THD', 'Sinal com Ruído EMI');
grid on;

% Gráfico 2: Espectro de Frequência do Sinal Distorcido (Visão da FFT)
subplot(2,1,2);
bins = 0:(amostras/2);
stem(bins, vMag(1:amostras/2 + 1), 'filled', 'MarkerFaceColor', 'm', 'Color', 'm');
title('Espectro de Magnitude da FFT (Sinal com THD)');
xlabel('Bins de Frequência'); ylabel('Amplitude (V)');
xlim([0 15]); % Limita a visão aos primeiros 15 harmônicos igual a interface do projeto
xticks(0:15);
grid on;