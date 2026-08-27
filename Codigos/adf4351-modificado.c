/*
 * File:   ADF4351.c
 *
 * Project: GlucoLac
 *
 * Author: LAC-073 - Exequiel
 *
 * Date:  25 / 04 / 2018
 *
 * Version: 0.1
 *          Definición de funciones
 *          Funciones terminadas. Funciona en RS232. (Probar SPI).
 *          Funcion SPI de inicialización funcionando. Error en barrido.
 *          Funciona Barrido.
 * Version: 0.2
 *          Agregado de tiempo de establecimiento entre generado de freq y medicion
 * 
 */
#define _XTAL_FREQ 48000000 //The speed of your internal(or)external oscillator

#include <xc.h>                     //Library for compiler
//#include <plib/usart.h>             //Library for UART
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
//#include <plib/adc.h>
#include "math.h"

//Definiciones
#define CLK LATCbits.LATC0 //PIN_C0
#define DATA_S LATCbits.LATC1 //PIN_C1
#define LE LATCbits.LATC2 //PIN_C2
#define CE LATAbits.LATA5 //PIN_C4 -/A5---------------------------
#define bittest(D,i) ( ( (D) & ( ( (unsigned long) 1 << (i) ) ) ) &&  ( ( (unsigned long) 1 << (i) ) ) )

//Definicion de variables
//float divisor; //modificado original
float divisor =0.5; //modificado, lo seteo ahora y listo
unsigned long init;

float FrecInstant;
//unsigned int vecADC; //Int aca es de 16 bites

/*
 *
 */
void set_frec_values(int initFrec)
{

/* Modificado original, solo ajusto los registros
      static const unsigned long FREC_INIT[3][6]={{ 0xD20000, 0x8008321, 0x4E42, 0x4B3, 0x950024, 0x580005}, // <2200 2.1 GHz -->  MOD = 100 ; INT = 210 ; FRAC = 0 ; R = 1  DIV 2. PFD =  5MHz
                                      { 0x708000, 0x8008321, 0x4E42, 0x4B3, 0x850024, 0x580005}, // >2200 2.1 GHz -->  MOD = 100 ; INT = 210 ; FRAC = 0 ; R = 1  DIV 1. PFD =  10MHz
                                      { 0xC80000, 0x8008321, 0x4E42, 0x4B3, 0xA50024, 0x580005}};// <1100 1GHz    -->  MOD = 100 ; INT = 400 ; FRAC = 0 ;  DIV 4. PFD =  2.5MHz

*/ 
//moficado, ajusto los registros para MOD = 1000, pfd = 0.5, R = 10, T activo 
static const unsigned long FREC_INIT[3][6]={{ 0x10680000, 0x8009F41, 0x1028E42, 0x4B3, 0x904024, 0x580005}, //<2.2 2.1 GHz--> 0: INT=8400; 1: MOD=1000,FRAC=0; 2: R=10, Tactivo; 4:DIV=2 
                                      { 0x8FC0000, 0x8009F41, 0x1028E42, 0x4B3, 0x804024, 0x580005}, // >2.2 2.3GHz--> 0: INT=4600; 1: MOD=1000,FRAC=0; ; 2: R=10, T activo; 4: DIV 1. 
                                      { 0xFA00000, 0x8009F41, 0x1028E42, 0x4B3, 0xA04024, 0x580005}};// <1.1 1GHz--> 0: INT=8000; 1: MOD=1000,FRAC=0; 2: R=10, T activo; 4: DIV 4
        
     CE = 0;        //CE Select device

     for (int i = 0; i <= 5; i++)           // para 6 registros
     {
         LE = 0;
         for (int m = 0; m <= 31; m++)      //para 32 bits
         {
             CLK = 0;
             DATA_S = bittest(FREC_INIT[initFrec][5-i],31-m);
             CLK = 1;
         }
         CLK = 0;
         DATA_S = 1;
         LE = 1;
     }
     CE = 1;        //CE Deselect device
     
     LE = 0;
     __delay_ms(1);
     LE = 1;
}

/*
 *
 */
void set_frec(float frec)
{
    unsigned long intt, frac, register_0;
    float intt_f;
    if (frec == 1100.0)
    {
        //divisor = 5;    //modificado original
        //divisor = 0.5;  //modificado,  no haria falta
        set_frec_values(0);
    }
    if (frec == 2200.0)
    {
        //divisor = 10;      //modificado original
        //divisor = 0.5;     //modificado,  no haria falta
        set_frec_values(1);
    }

    intt_f = (frec / divisor);
    intt = floor(intt_f);
    //frac = (100 / divisor) * (frec - divisor * intt);//modificado original, tiene el MOD en 100
    frac = (1000 / divisor) * (frec - divisor * intt); //modificado con el ajuste de MOD a 1000
    //register_0 = "" ;
    register_0 = 8 * frac + 32768 * intt ;

    CE = 0;         //CE Select device
    LE = 0;         // LE LOW
    for (int m=0;m<=31;m++)   //for 32 bits
    {
        CLK = 0;
        DATA_S = bittest(register_0,31-m);
        CLK = 1;
    }
    CLK = 0;
    DATA_S = 1;
    LE = 1;         //LE HIGH
    CE = 1;         //CE Deselect device
    LE = 0;
    __delay_ms(1);
    LE = 1;         //LE high
}

/*
 *
 */
void set_barrido(float frecInit, float frecEnd, float res)
{
    init = 1;

    FrecInstant = frecInit;

    //divisor = 10 ; //modificaod original
    //divisor = 0.5; // modificado, no haria falta

    if (frecInit < 1100.0)
    {
          //divisor = 2.5; //modificado original
    	  //divisor = 0.5; // modificado, no haria falta
          init = 2 ;
    }
    else if (frecInit < 2200.0 )
    {
          //divisor = 5;   //modificado original
    	  //divisor = 0.5; // modificado, no haria falta
          init = 0 ;
    }
    set_frec_values(init);
    while (FrecInstant <= frecEnd)
    {
       // vecADC = 0 ;

        set_frec(FrecInstant);

        __delay_ms(1); 
  
        //ConvertADC();

        //while(BusyADC());

        //vecADC = ReadADC() ;

        //char aInt[30];
        //memset(aInt[0],0,30);
        //sprintf(aInt,"%4.2f,%04u\n",FrecInstant,vecADC);
        //sprintf(aInt,"%lu",vecADC);
        FrecInstant = FrecInstant + res;

        //putsUSART(aInt);

    }

    //putsUSART("FIN Datos\n");

    __delay_ms(10);
}
