// Firmware Supervisório - Analisador de Qualidade de Energia (Power Quality)
// Plataforma: ESP32 | Protocolo Serial: "TIPO:PINO:VALOR\n"

#include <Arduino.h>
#include "arduinoFFT.h"

// ==============================================================================
// 1. DADOS DE SIMULAÇÃO (VETORES DE ONDA)
// ==============================================================================
const int sinal_rede_Limpo[128]      = {2048, 2063, 2078, 2094, 2109, 2124, 2138, 2153, 2167, 2181, 2195, 2208, 2221, 2233, 2245, 2257, 2268, 2278, 2288, 2298, 2307, 2315, 2322, 2329, 2335, 2341, 2346, 2350, 2353, 2356, 2358, 2359, 2359, 2359, 2358, 2356, 2353, 2350, 2346, 2341, 2335, 2329, 2322, 2315, 2307, 2298, 2288, 2278, 2268, 2257, 2245, 2233, 2221, 2208, 2195, 2181, 2167, 2153, 2138, 2124, 2109, 2094, 2078, 2063, 2048, 2033, 2018, 2002, 1987, 1972, 1958, 1943, 1929, 1915, 1901, 1888, 1875, 1863, 1851, 1839, 1828, 1818, 1808, 1798, 1789, 1781, 1774, 1767, 1761, 1755, 1750, 1746, 1743, 1740, 1738, 1737, 1737, 1737, 1738, 1740, 1743, 1746, 1750, 1755, 1761, 1767, 1774, 1781, 1789, 1798, 1808, 1818, 1828, 1839, 1851, 1863, 1875, 1888, 1901, 1915, 1929, 1943, 1958, 1972, 1987, 2002, 2018, 2033};
const int sinal_rede_THD_Alto[128]   = {2048, 2084, 2120, 2152, 2182, 2207, 2228, 2244, 2256, 2264, 2269, 2272, 2273, 2274, 2275, 2276, 2279, 2282, 2287, 2292, 2297, 2303, 2308, 2312, 2315, 2317, 2318, 2318, 2317, 2316, 2315, 2314, 2314, 2314, 2315, 2316, 2317, 2318, 2318, 2317, 2315, 2312, 2308, 2303, 2297, 2292, 2287, 2282, 2279, 2276, 2275, 2274, 2273, 2272, 2269, 2264, 2256, 2244, 2228, 2207, 2182, 2152, 2120, 2084, 2048, 2012, 1976, 1944, 1914, 1889, 1868, 1852, 1840, 1832, 1827, 1824, 1823, 1822, 1821, 1820, 1817, 1814, 1809, 1804, 1799, 1793, 1788, 1784, 1781, 1779, 1778, 1778, 1779, 1780, 1781, 1782, 1782, 1782, 1781, 1780, 1779, 1778, 1778, 1779, 1781, 1784, 1788, 1793, 1799, 1804, 1809, 1814, 1817, 1820, 1821, 1822, 1823, 1824, 1827, 1832, 1840, 1852, 1868, 1889, 1914, 1944, 1976, 2012};
const int sinal_rede_Ruido_Alto[128] = {2048, 2065, 2075, 2099, 2102, 2132, 2129, 2163, 2157, 2191, 2185, 2216, 2214, 2239, 2241, 2259, 2268, 2276, 2292, 2292, 2314, 2306, 2332, 2319, 2345, 2331, 2355, 2341, 2360, 2350, 2361, 2357, 2359, 2361, 2354, 2361, 2346, 2358, 2336, 2351, 2325, 2339, 2313, 2323, 2300, 2303, 2285, 2280, 2268, 2255, 2249, 2228, 2228, 2200, 2204, 2171, 2177, 2143, 2148, 2115, 2116, 2088, 2082, 2061, 2048, 2035, 2014, 2008, 1980, 1981, 1948, 1953, 1919, 1925, 1892, 1896, 1868, 1868, 1847, 1841, 1828, 1816, 1811, 1793, 1796, 1773, 1783, 1757, 1771, 1745, 1760, 1738, 1750, 1735, 1742, 1735, 1737, 1739, 1735, 1746, 1736, 1755, 1741, 1765, 1751, 1777, 1764, 1790, 1782, 1804, 1804, 1820, 1828, 1837, 1855, 1857, 1882, 1880, 1911, 1905, 1939, 1933, 1967, 1964, 1994, 1997, 2021, 2031};
const int sinal_zero[128]            = {0}; // Usado para zerar a onda quando nenhum botão está ativo

const int TOTAL_PONTOS = 128;
int indice = 0;

// Flags de Controle do Simulador
bool Botao_sinal_rede_Limpo = false;
bool Botao_sinal_rede_THD_Alto = false;
bool Botao_sinal_rede_Ruido_Alto = false;
bool Botao_teste_AumentarRMS = false;
bool Botao_teste_DiminuirRMS = false;
bool Botao_teste_spike = false;
bool Botao_reset_sinal = false;

// ==============================================================================
// 2. PARÂMETROS DO SISTEMA E LIMITES NORMATIVOS
// ==============================================================================
const int AMOSTRAS_POR_CICLO = 128;
const float FATOR_CONVERSAO  = 1.0;
const int OFFSET_ADC         = 2048;   // Ponto central do conversor ADC de 12-bits (1.65V)
const float V_NOMINAL        = 220.0;  // Tensão nominal fase-neutro

// Limites de distúrbios de amplitude
const float LIMITE_SWELL = V_NOMINAL * 1.10; // Sobretensão > 242V
const float LIMITE_SAG   = V_NOMINAL * 0.90; // Queda de tensão < 198V
const float LIMITE_SPIKE = 450.0;            // Transiente instantâneo máximo seguro

// Variáveis acumuladoras para cálculo RMS contínuo
long somaQuadrados = 0;
int contadorAmostras = 0;

// ==============================================================================
// 3. CONFIGURAÇÕES: ZERO CROSSING E FFT
// ==============================================================================
const int PINO_ZCD = 34; // Pino receptor da interrupção (Input-Only Pin no ESP32)

// Variáveis voláteis são alocadas na RAM principal, obrigatório para Interrupções (ISR)
volatile unsigned long tempoUltimoZero = 0;
volatile unsigned long periodoAtual = 0;
volatile bool novaLeituraZCD = false;

// Função chamada automaticamente pelo Hardware quando a onda cruza o Zero
void IRAM_ATTR detectaZeroCrossing() {
  unsigned long tempoAgora = micros();
  periodoAtual = tempoAgora - tempoUltimoZero;
  tempoUltimoZero = tempoAgora;
  novaLeituraZCD = true; 
}

// Inicialização das matrizes e instância do algoritmo de Fourier (FFT)
const uint16_t amostrasFFT = 128; // Obrigatório ser potência de 2
double vReal[amostrasFFT];        // Vetor da parte real (Amostras da onda)
double vImag[amostrasFFT];        // Vetor da parte imaginária
ArduinoFFT<double> FFT = ArduinoFFT<double>(vReal, vImag, amostrasFFT, 7680.0); // Fs = 128 amostras * 60Hz

// Constantes do Temporizador
unsigned long tempoUltimaAmostra = 0;
const unsigned long INTERVALO_AMOSTRAGEM = 3000; // Microssegundos // Valor de 3000 para simulação mais fluida.

// ==============================================================================
// 4. SETUP DO MICROCONTROLADOR
// ==============================================================================
void setup() {
  Serial.begin(115200);
  Serial.setTimeout(5); 

  // Configuração dos Pinos de Saída (LEDs / Alertas Físicos)
  int amarelos[] = {2, 4, 12, 13, 14, 26, 27};
  for (int p : amarelos) pinMode(p, OUTPUT);

  int verdes[] = {15, 18, 19, 21, 22};
  for (int p : verdes) pinMode(p, OUTPUT);

  // Configuração do detector de cruzamento por zero
  pinMode(PINO_ZCD, INPUT_PULLUP);
  attachInterrupt(digitalPinToInterrupt(PINO_ZCD), detectaZeroCrossing, RISING);
  
  // Força leitura de 0 a 4095
  // analogReadResolution(12); // Usado apenas na leitura real do sinal que entra no pino
}

// ==============================================================================
// 5. LOOP PRINCIPAL (AQUISIÇÃO E PROCESSAMENTO)
// ==============================================================================
void loop() {

  // Um temporizador (timer) não-bloqueante para garantir que o analogRead aconteça 
  //a cada 130 microssegundos (1/7680 segundos).
  unsigned long tempoAtual = micros();

  // Só executa a leitura se passaram exatos 130 microssegundos
  if (tempoAtual - tempoUltimaAmostra >= INTERVALO_AMOSTRAGEM) {
    tempoUltimaAmostra = tempoAtual;

    // ----------------------------------------------------------------------------
    // BLOCO A: DETECÇÃO DE SINCRONISMO E FREQUÊNCIA (Via Interrupção)
    // ----------------------------------------------------------------------------
    if (novaLeituraZCD) {
      // Congela interrupções momentaneamente para evitar corrupção dos dados
      noInterrupts();
      unsigned long periodoLocal = periodoAtual;
      novaLeituraZCD = false;
      interrupts();

      // Calcula Frequência Real (f = 1/T)
      float frequenciaReal = 1000000.0 / periodoLocal;

      // Calcula Desvio de Fase (Comparado ao período ideal de 16.66ms para 60Hz)
      long erroTempo = periodoLocal - 16666; 
      float erroFaseGraus = ((float)erroTempo / 16666.0) * 360.0;

      // Transmite métricas via Serial para a Interface Gráfica
      Serial.print("Freq:");
      Serial.println(frequenciaReal, 2);
      Serial.print("Fase:");
      Serial.println(erroFaseGraus, 1);

      // Alertas de Sincronismo
      if (frequenciaReal > 60.5 || frequenciaReal < 59.5) {
        Serial.println("ALERTA: DESVIO DE FREQUENCIA");
      }
      if (abs(erroFaseGraus) > 5.0) { 
        Serial.println("ALERTA: SALTO DE FASE");
      }
    }

    // ----------------------------------------------------------------------------
    // BLOCO B: MÁQUINA DE ESTADOS DO SIMULADOR (Injeção de Anomalias)
    // ----------------------------------------------------------------------------
    int leituraBrutaADC = sinal_zero[indice]; // analogRead(PINO_TENSAO);
    int valorOnda = leituraBrutaADC; // Valor padrão liso (zero)

    // Seleciona a base da onda conforme botões ativos no Painel
    if (Botao_sinal_rede_Limpo)      { valorOnda = sinal_rede_Limpo[indice] - OFFSET_ADC; }
    if (Botao_sinal_rede_THD_Alto)   { valorOnda = sinal_rede_THD_Alto[indice] - OFFSET_ADC; }
    if (Botao_sinal_rede_Ruido_Alto) { valorOnda = sinal_rede_Ruido_Alto[indice] - OFFSET_ADC; }

    // Injeção de anomalias de amplitude sobre a onda selecionada
    if (Botao_teste_AumentarRMS) { valorOnda *= 1.2; } // Simula Swell
    if (Botao_teste_DiminuirRMS) { valorOnda *= 0.8; } // Simula Sag

    // Injeção de anomalia de transiente ultra-rápido
    if (Botao_teste_spike) {
      // Altera bruscamente a amplitude de apenas um ponto aleatório da onda
      if (indice == 32) { valorOnda *= 1.5; } 
    }

    // ----------------------------------------------------------------------------
    // BLOCO C: AQUISIÇÃO ANALÓGICA E RMS
    // ----------------------------------------------------------------------------
    // Armazena a amostra atual no vetor real para processamento futuro da FFT
    vReal[contadorAmostras] = valorOnda;

    float tensaoInstantanea = abs(valorOnda * FATOR_CONVERSAO);

    // Detecção de Transientes (Deve ser calculada amostra por amostra)
    if (tensaoInstantanea > LIMITE_SPIKE) {
      Serial.println("ALERTA: SPIKE DETECTADO! Risco de surto.");
    }

    // Acumulação de energia para cálculo do valor Quadrático Médio
    somaQuadrados += (valorOnda * valorOnda); 
    contadorAmostras++;

    // ----------------------------------------------------------------------------
    // BLOCO D: FECHAMENTO DE CICLO (Análise da Janela Completa)
    // ----------------------------------------------------------------------------
    if (contadorAmostras >= AMOSTRAS_POR_CICLO) {
      
      // 1. CÁLCULO RMS E VERIFICAÇÃO DOS RESULTADOS
      float mediaQuadrados = (float)somaQuadrados / AMOSTRAS_POR_CICLO;
      float tensaoRms = sqrt(mediaQuadrados) * FATOR_CONVERSAO;

      if (tensaoRms > LIMITE_SWELL) {
        Serial.println("SWELL DETECTADO");
        digitalWrite(2, 1); digitalWrite(4, 0); digitalWrite(12, 0);
      } else if (tensaoRms < LIMITE_SAG) {
        Serial.println("SAG DETECTADO");
        digitalWrite(2, 0); digitalWrite(4, 1); digitalWrite(12, 0); 
      } else {
        Serial.println("REDE NORMAL");
        digitalWrite(2, 0); digitalWrite(4, 0); digitalWrite(12, 1);
      }
      
      Serial.print("Vrms:");
      Serial.println(tensaoRms);

      // Zera os acumuladores de amplitude para o próximo ciclo elétrico
      somaQuadrados = 0;
      contadorAmostras = 0;

      // 2. PROCESSAMENTO DIGITAL DE SINAIS (FFT)
      // Limpa a parte imaginária para evitar lixo de memória na transformada
      for (int i = 0; i < amostrasFFT; i++) { vImag[i] = 0.0; }

      FFT.windowing(FFT_WIN_TYP_HAMMING, FFT_FORWARD); 
      FFT.compute(FFT_FORWARD);                        
      FFT.complexToMagnitude();                        

      // 3. ANÁLISE DE DISTORÇÃO HARMÔNICA (THD - 3ª, 5ª e 7ª ordem)
      double ampFundamental = vReal[1]; // Frequência Fundamental (60Hz)
      double ampHarm3 = vReal[3];       // 180 Hz
      double ampHarm5 = vReal[5];       // 300 Hz
      double ampHarm7 = vReal[7];       // 420 Hz

      float somaHarmonicasQuad = (ampHarm3 * ampHarm3) + (ampHarm5 * ampHarm5) + (ampHarm7 * ampHarm7);
      float thdPercentual = (sqrt(somaHarmonicasQuad) / ampFundamental) * 100.0;

      Serial.print("THD:");
      Serial.println(thdPercentual, 1);

      if (thdPercentual > 5.0) { 
        Serial.println("ALERTA: DISTORCAO HARMONICA ELEVADA");
      }

      // 4. ANÁLISE DE ESPECTRO SUPERIOR (RUÍDO EMI/RFI)
      double energiaRuidoAltaFreq = 0.0; 
      
      // Varre os espectros superiores isolando a energia residual
      for (int i = 15; i < (amostrasFFT / 2); i++) {
        energiaRuidoAltaFreq += vReal[i] * vReal[i]; 
      }

      // Calcula a magnitude linear do ruído (Corrigido para usar a raiz quadrada)
      float ruidoLinearRMS = sqrt(energiaRuidoAltaFreq);

      Serial.print("RuidoFFT:");
      Serial.println(ruidoLinearRMS / vReal[1], 3); // Relação Ruído/Fundamental para o Python

      // Alerta baseado na energia RMS do ruído comparada a 3% da fundamental
      if ((ruidoLinearRMS / vReal[1]) > 0.03) { 
        Serial.println("ALERTA: RUIDO DE ALTA FREQUENCIA");
      }

      // 5. TRANSMISSÃO DO ESPECTRO PARA A INTERFACE
      // Vamos transmitir as magnitudes do Bin 1 (60Hz) até o Bin 15 (900Hz)
      Serial.print("FFT:");
      for (int i = 1; i <= 15; i++) {
        Serial.print(vReal[i]/64, 1); // Envia com 1 casa decimal
        if (i < 15) Serial.print(","); // Separa por vírgula
      }
      Serial.println(); // Quebra a linha no final
    }
    
    // ----------------------------------------------------------------------------
    // BLOCO E: COMUNICAÇÃO SUPERVISÓRIA
    // ----------------------------------------------------------------------------
    Serial.print("A:0:");
    Serial.println(valorOnda);

    // Atualiza o ponteiro da simulação
    indice++;
    if (indice >= TOTAL_PONTOS) { indice = 0; }

    // 1. RECPÇÃO DE COMANDOS DA INTERFACE (PYTHON)
    if (Serial.available() > 0) {
      String msg = Serial.readStringUntil('\n');
      int sep1 = msg.indexOf(':');
      int sep2 = msg.lastIndexOf(':');

      if (sep1 != -1 && sep2 != -1) {
        char tipo = msg.charAt(0);
        int pino = msg.substring(sep1 + 1, sep2).toInt();
        int valor = msg.substring(sep2 + 1).toInt();

        // Mapeamento Lógico dos Botões de Simulação da Interface
        if (tipo == 'D') {
          if (pino == 2)  { Botao_sinal_rede_Limpo = (valor == 1); Botao_sinal_rede_THD_Alto = false; Botao_sinal_rede_Ruido_Alto = false; Botao_reset_sinal = false; }
          if (pino == 4)  { Botao_sinal_rede_THD_Alto = (valor == 1); Botao_sinal_rede_Limpo = false; Botao_sinal_rede_Ruido_Alto = false; Botao_reset_sinal = false; }
          if (pino == 12) { Botao_sinal_rede_Ruido_Alto = (valor == 1); Botao_sinal_rede_Limpo = false; Botao_sinal_rede_THD_Alto = false; Botao_reset_sinal = false; }
          
          if (pino == 13) { Botao_teste_AumentarRMS = (valor == 1); Botao_teste_DiminuirRMS = false; Botao_teste_spike = false; }
          if (pino == 14) { Botao_teste_DiminuirRMS = (valor == 1); Botao_teste_AumentarRMS = false; Botao_teste_spike = false; }
          if (pino == 26) { Botao_teste_spike = (valor == 1); Botao_teste_AumentarRMS = false; Botao_teste_DiminuirRMS = false; }
          
          if (pino == 27 && valor == 1) { 
            // Botão Reset (Zera tudo)
            Botao_teste_AumentarRMS = false; Botao_teste_DiminuirRMS = false; Botao_teste_spike = false;
          }
        }
      }
    }
    
  }
}