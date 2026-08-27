/* 
 * File:   newmain.c
 * Author: Brian
 *
 * Created on May 30, 2023, 00:15 PM
 */


#include <xc.h>                     //Library for compiler
#include <stdlib.h>
#include <p18f4550.h>               //Library for PIC
#include "ADF4351.c"
#include "lcd.c"          //Library for PIC

//CON ESTE ORDEN DE CONFIGURACION FUNCIONA RB5..... (P 48M)
#pragma config PLLDIV = 5, CPUDIV = OSC1_PLL2, USBDIV = 2
#pragma config FOSC = HSPLL_HS, FCMEN = OFF, IESO = OFF
#pragma config PWRT = OFF, BOR = OFF, VREGEN = OFF
#pragma config WDT = OFF, WDTPS = 32768
#pragma config MCLRE = ON, LPT1OSC = OFF, PBADEN = OFF
#pragma config STVREN = ON, LVP = OFF, ICPRT = OFF, XINST = OFF

#define _XTAL_FREQ 48000000


void set_registers(void);
//void delay1Seg(void);
//void delayHalfSeg(void);
//void delay100mSeg(void);

//float a, ma;
float resKilo, resMega, frecEnd, frecInit, retardo;

void main (void) {
    set_registers();
    
    //a = 150;
    //ma=0;
    //set_frec(a,ma);
    
    frecInit =500;
    frecEnd = 501;
    resMega=0;
    resKilo=1;
    retardo=100;
    
    while (1) {
       set_barrido(frecInit, frecEnd, resMega, resKilo, retardo); 
         
    }
}
  
void set_registers(void)
{
    
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
    TRISCbits.TRISC0 = 0;
    TRISCbits.TRISC1 = 0;
    TRISCbits.TRISC2 = 0;
    TRISAbits.TRISA5 = 0;
    
        
    //Init Para SPI
    CE = 1;
    DATA_S = 1;
    LE = 1;
    CLK = 0;
    __delay_ms(10);
    //set_frec_values(0);
}

/*   
void delay1Seg(void)
{
    int i;
    for (i=0;i<100;i++)
    {
        __delay_ms(10);
    }
}

void delayHalfSeg(void)
{
    int i;
    for (i=0;i<50;i++)
    {
        __delay_ms(10);
    }
}

void delay100mSeg(void)
{
    int i;
    for (i=0;i<10;i++)
    {
        __delay_ms(10);
    }
}
*/