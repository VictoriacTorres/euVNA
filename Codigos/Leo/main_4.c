/*
 * File:   ADF4351.c
 *
 * Project: microVNA
 *
 * Author: Leonardo David Vazquez
 *
 * Date:  17/ 10 / 2024
 *
 * Version: 0.1
 */

#include <xc.h>                     //Library for compiler
#include <stdlib.h>
#include <p18f4550.h>               //Library for PIC
#include <math.h>

//#include "ADF4351.c"
//#include "lcd.c"          //Library for PIC

//CON ESTE ORDEN DE CONFIGURACION FUNCIONA RB5..... (P 48M)
#pragma config PLLDIV = 5, CPUDIV = OSC1_PLL2, USBDIV = 2
#pragma config FOSC = HSPLL_HS, FCMEN = OFF, IESO = OFF
#pragma config PWRT = OFF, BOR = OFF, VREGEN = OFF
#pragma config WDT = OFF, WDTPS = 32768
#pragma config MCLRE = ON, LPT1OSC = OFF, PBADEN = OFF
#pragma config STVREN = ON, LVP = OFF, ICPRT = OFF, XINST = OFF

#define _XTAL_FREQ 48000000

//Definiciones
#define LED1 LATDbits.LATD0 //PIN_D0 (pin38)
#define LED2 LATDbits.LATD1 //PIN_D1 (pin39)

#define CLK1 LATDbits.LATD7 //PIN_D7 (pin5))
#define DATA_S1 LATDbits.LATD6 //PIN_D6 (pin4))
#define LE1 LATDbits.LATD5 //PIN_D5 (pin3)
#define CE1 LATDbits.LATD4 //PIN_D4 (pin2)---------------------------
#define bittest1(D,i) ( ( (D) & ( ( (unsigned long) 1 << (i) ) ) ) &&  ( ( (unsigned long) 1 << (i) ) ) )

#define CLK2 LATCbits.LATC0 //PIN_D3 (pin41)
#define DATA_S2 LATCbits.LATC1 //PIN_D2 (pin40)
#define LE2 LATCbits.LATC2 //PIN_C2 (pin 36)
#define CE2 LATAbits.LATA5 //PIN_C1 (pin35)--------------------------
#define bittest2(D,i) ( ( (D) & ( ( (unsigned long) 1 << (i) ) ) ) &&  ( ( (unsigned long) 1 << (i) ) ) )


static const unsigned long FREC_INIT1[1][6]={{ 0x9600000, 0x8000011, 0x1028E42, 0x4B3, 0xB0403C, 0x580005}};// >275 300MHz
static const unsigned long FREC_INIT2[1][6]={{ 0x9600020, 0x80000C9, 0x1028E42, 0x4B3, 0xB0403C, 0x580005}};// >275 300MHz + 10 kHz
static unsigned long FREC_1[1][6];  // Primer conjunto
static unsigned long FREC_2[1][6];  // Segundo conjunto


void titilar(int led){
    
            if (led == 1) {

                LED1 = 1;
                for (int m = 0; m <= 1; m++) {  
                    __delay_ms(10);
                }
                LED1 = 0;
                }
            else if (led == 2) {

                LED2 = 1;
                for (int m = 0; m <= 1; m++) {  
                    __delay_ms(10);
                }
                LED2 = 0;
               } 
    
}



void set_frec_values_1(int initFrec)
{
      //moficado, ajusto los registros para MOD = 1000, pfd = 0.5, R = 10, T activo 
      //static const unsigned long FREC_INIT1[1][6]={{ 0x9600000, 0x8000011, 0x1028E42, 0x4B3, 0xB0403C, 0x580005}};// >275 300MHz
     
     CE1 = 0;        //CE Select device

     for (int i = 0; i <= 5; i++)           // para 6 registros
     {
         LE1 = 0;
         for (int m = 0; m <= 31; m++)      //para 32 bits
         {
             CLK1 = 0;
             DATA_S1 = bittest1(FREC_1[initFrec][5-i],31-m);
             CLK1 = 1;
         }
         CLK1 = 0;
         DATA_S1 = 1;
         LE1 = 1;
     }
     CE1 = 1;        //CE Deselect device
     
     LE1 = 0;
     __delay_ms(1);
     LE1 = 1;
     titilar(1);
}

void set_frec_values_2(int initFrec)
{
      //moficado, ajusto los registros para MOD = 1000, pfd = 0.5, R = 10, T activo 
      //static const unsigned long FREC_INIT2[1][6]={{ 0x9600020, 0x80000C9, 0x1028E42, 0x4B3, 0xB0403C, 0x580005}};// >275 300MHz + 10 kHz
      
     CE2 = 0;        //CE Select device

     for (int i = 0; i <= 5; i++)           // para 6 registros
     {
         LE2 = 0;
         for (int m = 0; m <= 31; m++)      //para 32 bits
         {
             CLK2 = 0;
             DATA_S2 = bittest2(FREC_2[initFrec][5-i],31-m);
             CLK2 = 1;
         }
         CLK2 = 0;
         DATA_S2 = 1;
         LE2 = 1;
     }
     CE2 = 1;        //CE Deselect device
     
     LE2 = 0;
     __delay_ms(1);
     LE2 = 1;
    titilar(2);
}

// Función para inicializar el UART
void UART_Init(unsigned long baudrate) {
    unsigned int x;
    x = (_XTAL_FREQ - baudrate * 64) / (baudrate * 64);  // Cálculo del baud rate para BRGH = 0
    
    if (x > 255) {
        x = (_XTAL_FREQ - baudrate * 16) / (baudrate * 16);  // Cálculo del baud rate para BRGH = 1
        BRGH = 1;  // Alta velocidad
    } else {
        BRGH = 0;  // Baja velocidad
    }
    
    SPBRG = x;      // Asignar valor calculado a SPBRG
    SYNC = 0;       // Modo asíncrono
    SPEN = 1;       // Habilitar puerto serie (RX/TX)
    
    TXEN = 1;       // Habilitar transmisión
    CREN = 1;       // Habilitar recepción
    
    TX9 = 0;        // Modo de 8 bits
    RX9 = 0;        // Modo de 8 bits
}


// Función para recibir un solo carácter
// Función para recibir un solo carácter con manejo de errores
char UART_Read() {
    while (!RCIF);  // Esperar hasta que se reciba un dato
    return RCREG;  // Retornar el dato recibido
}

// Función para transmitir un solo carácter (byte)
void UART_Write(char data) {
    while (!TXIF);  // Esperar hasta que el buffer esté vacío
    TXREG = data;   // Cargar el registro de transmisión con el dato
}

// Función para transmitir un registro de 32 bits a través del UART
void UART_Write_32bits(unsigned long valor) {
    for (int i = 3; i >= 0; i--) {  // Enviar de byte más significativo a menos significativo
        UART_Write((valor >> (i * 8)) & 0xFF);  // Enviar byte por byte
    }
}

// Función para transmitir los registros almacenados en el conjunto 1 o 2
void UART_Write_Registers(char setID) {
    if (setID == 0x01) {
        // Transmitir el conjunto 1
        for (int i = 0; i < 6; i++) {
            UART_Write_32bits(FREC_1[0][i]);
            
        }
                // Transmitir el conjunto 2
        for (int i = 0; i < 6; i++) {
            UART_Write_32bits(FREC_2[0][i]);
            
        }
        
    } 
}
// Función para transmitir una cadena de texto
void UART_Write_Text(char* text) {
    int i;
    for (i = 0; text[i] != '\0'; i++) {
        UART_Write(text[i]);
    }
}


// Función para obtener los parámetros div, frac y mod según la frecuencia de salida
void obtener_parametros(double f_out, int* div, int* frac, int* mod) {
    // Asignar FRAC y MOD fijos para todos los casos, ya que f_out es siempre entero
    *frac = 0;
    *mod = 2;

    // Asignar divisor basado en el rango de f_out
    if (f_out >= 300.0 && f_out <= 550.0) {
        *div = 8;
    } else if (f_out > 550.0 && f_out <= 1100.0) {
        *div = 4;
    } else if (f_out > 1100.0 && f_out <= 2200.0) {
        *div = 2;
    } else if (f_out > 2200.0 && f_out <= 3000.0) {
        *div = 1;
    }
}



// Función para obtener los parámetros div, frac y mod según la frecuencia de salida
void obtener_parametros2(double f_out, int* div, int* frac, int* mod) {
    //double fraccion;

    if (f_out >= 300.0 && f_out <= 550.0) {
        *div = 8;
        *mod = 125;  // MOD estándar para este rango
        *frac = 2;
    } else if (f_out > 550.0 && f_out <= 1100.0) {
        *div = 4;
        *mod = 125;  // MOD estándar para este rango
        *frac = 1;
    } else if (f_out > 1100.0 && f_out <= 2200.0) {
        *div = 2;
        *mod = 250;  // MOD estándar para este rango
        *frac = 1;
    } else if (f_out > 2200.0 && f_out <= 3000.0) {
        *div = 1;
        *mod = 500;  // MOD estándar para este rango
        *frac = 1;
    } else {
        return;  // Salir si la frecuencia no está en el rango permitido
    }

    // Calcular la parte fraccionaria de la frecuencia
    //fraccion = f_out - floor(f_out);  // Obtener la parte fraccionaria

    // Calcular FRAC basado en la parte fraccionaria y el valor de MOD
    //*frac = (int)(fraccion * (*mod));  // Multiplicamos la parte fraccionaria por MOD
}




// Función para calcular el valor INT basado en la ecuación
int calcular_int(double f_out, double f_pfd, int div, int frac, int mod) {
    return (int)((f_out * div / f_pfd) - ((double)frac / (double)mod));
}

// Función para determinar el valor del Registro 1 según MOD y prescaler
unsigned long calcular_registro1(int mod, int prescaler_8_9) {
    int control_bits = 0b001;
    int prescaler_bit = (prescaler_8_9) ? 1 : 0;
    int phase_adjust_bit = 0;
    int phase_value = 0x001;

    return ((unsigned long)phase_adjust_bit << 28) | ((unsigned long)prescaler_bit << 27) |
           ((unsigned long)phase_value << 15) | ((unsigned long)mod << 3) | control_bits;
}

// Función para obtener el valor del Registro 4 basado en DIV
unsigned long obtener_registro4(int div) {
    switch (div) {
        case 1: return 0x80403C;
        case 2: return 0x90403C;
        case 4: return 0xA0403C;
        case 8: return 0xB0403C;
        default: return 0;  // En caso de error
    }
}

// Función para calcular los registros de FREC_1 y programar el ADF4351
void cargar_freq1(double f_out) {
    double f_pfd = 0.5;  // PFD en MHz
    int prescaler_8_9 = 1;
    int div, frac, mod;

    obtener_parametros(f_out, &div, &frac, &mod);
    int n_int = calcular_int(f_out, f_pfd, div, frac, mod);

    // Registro 0: INT y FRAC
    FREC_1[0][0] = ((unsigned long)n_int << 15) | ((unsigned long)frac << 3) | 0x0;

    // Registro 1: MOD, prescaler, fase
    FREC_1[0][1] = calcular_registro1(mod, prescaler_8_9);

    // Registro 2: Prescaler y otros controles
    //FREC_1[0][2] = ((unsigned long)prescaler_8_9 << 28) | 0x28E42;

    // Registro 3: Cargas y feedback
    //FREC_1[0][3] = 0x004B3;

    // Registro 4: Depende de DIV
    FREC_1[0][4] = obtener_registro4(div);

    // Registro 5: Configuración fija
    //FREC_1[0][5] = 0x580005;

    set_frec_values_1(0);  // Programar el sintetizador 1
}

// Función para calcular los registros de FREC_2 y programar el ADF4351
void cargar_freq2(double f_out) {
    double f_pfd = 0.5;  // PFD en MHz
    int prescaler_8_9 = 1;
    int div, frac, mod;
    //double f_out = (double)f_out2+(double)0.001;
    obtener_parametros2(f_out, &div, &frac, &mod);
    int n_int = calcular_int(f_out, f_pfd, div, frac, mod);

    // Registro 0: INT y FRAC
    FREC_2[0][0] = ((unsigned long)n_int << 15) | ((unsigned long)frac << 3) | 0x0;

    // Registro 1: MOD, prescaler, fase
    FREC_2[0][1] = calcular_registro1(mod, prescaler_8_9);

    // Registro 2: Prescaler y otros controles
    //FREC_2[0][2] = ((unsigned long)prescaler_8_9 << 28) | 0x28E42;

    // Registro 3: Cargas y feedback
    //FREC_2[0][3] = 0x004B3;

    // Registro 4: Depende de DIV
    FREC_2[0][4] = obtener_registro4(div);

    // Registro 5: Configuración fija
    //FREC_2[0][5] = 0x580005;

    set_frec_values_2(0);  // Programar el sintetizador 2
}




void set_registers(void);
void indicators(void);



void main (void) {
    UART_Init(9600);  // Inicializar UART a 9600 baudios
    set_registers();
    indicators();
    
    while(1){
        
        char setID = UART_Read();  // Leer el ID del conjunto
            if (setID == 0x01) {
                // Leer dos bytes de UART para formar la frecuencia
            //unsigned char freq =  UART_Read();
            unsigned char freq_high = UART_Read();  // Leer el byte alto
            unsigned char freq_low = UART_Read();   // Leer el byte bajo

            // Combinar los dos bytes en un entero de 16 bits
            unsigned int freq = (freq_high << 8) | freq_low;
            
            // Verificar si la frecuencia está en el rango permitido (300 a 3000 MHz)
            //__delay_ms(10);
              // Llamar a las funciones con la frecuencia leída
            if (freq >= 300 && freq <= 3000) {
                double f_out = (double)freq;  // Convertir a double para usar en cargar_freq1 y cargar_freq2
            
                // Llamar a las funciones con la frecuencia leída
                cargar_freq1(f_out);
                cargar_freq2(f_out);  // Usar una pequeña diferencia de 0.001 para el otro canal
            }

            for (int m = 0; m <= 5; m++) {  
                __delay_ms(10);
            }
            
            }
        //UART_Write_Registers(setID);
            
        
        
        
    }
}

   
  
void set_registers(void)
{
            for (int i = 0; i < 6; i++) {
            FREC_1[0][i] = FREC_INIT1[0][i];
        }   
                    for (int i = 0; i < 6; i++) {
            FREC_2[0][i] = FREC_INIT2[0][i];
        }   
    /*Inicialización de variables*/
    SPPCON  = 0     ;   //disable SPP
    ADCON0  = 0     ;   //disable ADC function
    CVRCON  = 0     ;   //more disables
    SSPCON1 = 0     ;   //disable SPI functionality
    CCP1CON = 0     ;   //disable both ccp modules
    ADCON1  = 0x0F  ;

    //Para SPI
    SSPSTAT = 0b00000000;  //0x00 De acuerdo a la hoja de datos
    SSPCON1 = 0b00110001;  // De acuerdo a la hoja de datos

    //Seteo de los TRIS para el SPI del generador.
    //como salidas para enviar información.
    TRISDbits.TRISD7 = 0;
    TRISDbits.TRISD6 = 0;
    TRISDbits.TRISD5 = 0;
    TRISDbits.TRISD4 = 0;

    TRISCbits.TRISC0 = 0;
    TRISCbits.TRISC1 = 0;
    TRISCbits.TRISC2 = 0;
    TRISAbits.TRISA5 = 0;

        
    //Init Para SPI 1
    CE1 = 1;
    DATA_S1 = 1;
    LE1 = 1;
    CLK1 = 0;
    __delay_ms(10);
    set_frec_values_1(0);
    //Init Para SPI 2
    CE2 = 1;
    DATA_S2 = 1;
    LE2 = 1;
    CLK2 = 0;
    __delay_ms(10);
    set_frec_values_2(0);
}

void indicators(void){
    TRISDbits.TRISD0 = 0;
    TRISDbits.TRISD1 = 0;
    
    titilar(1);
    titilar(2);
}