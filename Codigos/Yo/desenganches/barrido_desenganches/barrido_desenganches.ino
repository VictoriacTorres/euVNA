#include <SPI.h>

//-------------------- Pines --------------------

#define PIN_LE1   10
#define PIN_CE1    9

//-------------------- Constantes del PLL --------------------
const double REF_FREQ = 10000000.0;      // 10 MHz
const uint16_t R_COUNTER = 10;
const int pinAnalogicoLD= A0;
const int UMBRAL = 300; //(aprox 1.5V)
const bool REF_DOUBLER = false;
const bool REF_DIV2 = true;

const uint16_t MOD = 1000;
const uint16_t PHASE = 1;

//-------------------- Declaración de registros --------------------

uint32_t reg[6];

//----------------Escritura de registros----------------------------------

void writeRegister1(uint32_t value)   //le estoy pasando una variable local que va a ser el valor del registro
{
    digitalWrite(PIN_LE1, LOW);

    SPI.transfer((value >> 24) & 0xFF);
    SPI.transfer((value >> 16) & 0xFF);
    SPI.transfer((value >> 8) & 0xFF);
    SPI.transfer(value & 0xFF); // toma cada byte desplazando y multiplicando por FF

    digitalWrite(PIN_LE1, HIGH); //transfiere los datos internamente
    delayMicroseconds(2); // 
    digitalWrite(PIN_LE1, LOW); // cierra la "compuerta de carga"
}

//--------------------------------------------------
void updateADF1()
{
    for (int i = 5; i >= 0; i--) {
        writeRegister1(reg[i]);
    }
}
//--------------------------------------------------
// Armo los 6 registros para una frecuencia dada en MHz.
//--------------------------------------------------
void calcularRegistros(double MHz)
{
    uint8_t rf_div_sel;
    uint8_t rf_div;

    if (MHz >= 2200) {
        rf_div_sel = 0;
        rf_div = 1;
    } else if (MHz >= 1100) {
        rf_div_sel = 1;
        rf_div = 2;
    } else if (MHz >= 550) {
        rf_div_sel = 2;
        rf_div = 4;
    } else if (MHz >= 275) {
        rf_div_sel = 3;
        rf_div = 8;
    } else {
        rf_div_sel = 4;
        rf_div = 16;
    }

    double fpfd = REF_FREQ;

    if (REF_DOUBLER)
        fpfd *= 2.0;

    if (REF_DIV2)
        fpfd /= 2.0;

    fpfd /= R_COUNTER;

    double fvco = MHz * 1000000.0 * rf_div;

    double N = fvco / fpfd;

    uint16_t INT = floor(N); // toma la parte entera hacia abajo
    uint16_t FRAC = round((N - INT) * MOD);

    if (FRAC >= MOD) {
        INT++;
        FRAC = 0;
    }

    //---------------- R0 ----------------

    reg[0] = 0;
    reg[0] |= ((uint32_t)INT) << 15;
    reg[0] |= ((uint32_t)FRAC) << 3;

    //---------------- R1 ----------------

    reg[1] = 0;
    reg[1] |= (1UL << 27);            // Prescaler = 8/9
    reg[1] |= ((uint32_t)PHASE) << 15;
    reg[1] |= ((uint32_t)MOD) << 3;
    reg[1] |= 1;

    //---------------- R2 ----------------

    reg[2] = 0;

    if (REF_DOUBLER)
        reg[2] |= (1UL << 25);

    if (REF_DIV2)
        reg[2] |= (1UL << 24);

    reg[2] |= ((uint32_t)R_COUNTER << 14);
    reg[2] |= (15UL << 9);   // Charge Pump = 5.00 mA
    reg[2] |= (1UL << 6);    // PD Polarity = Positive
    //reg[2] |= (1UL << 13);   // divider select value de R4 double buffered
    reg[2] |= 2;

    //---------------- R3 ----------------

    reg[3] = 0x008004B3; // para fast lock

    //---------------- R4 ----------------

    reg[4] = 0;
    reg[4] |= (1UL << 23);                    // Feedback fundamental
    reg[4] |= ((uint32_t)rf_div_sel << 20);   // RF Divider
    reg[4] |= (20UL << 12);                   // Band Select Divider 80UL para enganche rapido, 20 para lento
    reg[4] |= (1UL << 5);                     // RF Output Enable
    reg[4] |= (3UL << 3);                     // +5 dBm
    reg[4] |= 4;

    //---------------- R5 ----------------

    reg[5] = 0x00580005;
}
//--------------------------------------------------
void setFrequency1(double MHz)
{
    calcularRegistros(MHz);
    updateADF1();
}

//--------------------------------------------------
// Protocolo serial: se le manda una línea de texto con la frecuencia en
// MHz para ADF1 (ej: "870.000000\n"). El Arduino setea ADF1 y responde con una
// línea "OK <frecuencia>" cuando terminó.
//--------------------------------------------------

char bufferEntrada[32];
uint8_t idxBuffer = 0;

void procesarComando(char *cmd)
{
    double f = atof(cmd);

    if (f <= 0.0) {
        Serial.print("ERROR frecuencia invalida: ");
        Serial.println(cmd);
        return;
    }

    setFrequency1(f);


    Serial.print("OK ");
    Serial.println(f, 6); // con 6 decimales
}

void setup()
{
    pinMode(PIN_LE1, OUTPUT); //configura pines como salidas
    pinMode(PIN_CE1, OUTPUT);

    SPI.begin();
    SPI.beginTransaction(SPISettings(1000000, MSBFIRST, SPI_MODE0));

    Serial.begin(115200);
    delay(100);

    Serial.println("READY");
}

void loop()
{
    while (Serial.available()) {
        char c = Serial.read();

        if (c == '\n') {
            bufferEntrada[idxBuffer] = '\0';
            procesarComando(bufferEntrada);

            delay(20);
            int valorleido = analogRead(pinAnalogicoLD);

            if (valorleido < UMBRAL) {
                Serial.print("Unlocked");
                Serial.println(bufferEntrada);
            }

            idxBuffer = 0;
        } else if (idxBuffer < sizeof(bufferEntrada) - 1) {
            bufferEntrada[idxBuffer++] = c;
        }
        // si se llena el buffer sin '\n', se ignoran caracteres de más
        // hasta el próximo salto de línea (evita overflow)
        
    }
}
