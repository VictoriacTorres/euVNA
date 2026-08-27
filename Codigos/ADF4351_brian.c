/*
 * File:   ADF4351.c
 *
 * Project: GlucoLac
 *
 * Author: LAC-073 - Exequiel
 *
 * Date:  25 / 04 / 2018
 *                                            
 * 
 */
#define _XTAL_FREQ 48000000 //The speed of your internal(or)external oscillator

#include <xc.h>                     //Library for compiler
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "math.h"

//Definiciones
#define CLK LATCbits.LATC0 //PIN_C0
#define DATA_S LATCbits.LATC1 //PIN_C1
#define LE LATCbits.LATC2 //PIN_C2
#define CE LATAbits.LATA5 //PIN_C4 -/A5---------------------------
#define bittest(D,i) ( ( (D) & ( ( (unsigned long) 1 << (i) ) ) ) &&  ( ( (unsigned long) 1 << (i) ) ) )

//Definicion de variables
float invpfd = 2; //modificado, lo seteo ahora y listo
float divi = 1;
unsigned long init;
float FrecInstant;
/*
 *
 */
void set_frec_values(int initFrec)
{
      //moficado, ajusto los registros para MOD = 1000, pfd = 0.5, R = 10, T activo 
      static const unsigned long FREC_INIT[5][6]={{ 0x10680000, 0x8009F41, 0x1028E42, 0x4B3, 0x904024, 0x580005}, //<2.2 2.1 GHz--> 0: INT=8400; 1: MOD=1000,FRAC=0; 2: R=10, Tactivo; 4:DIV=2 
                                      { 0x8FC0000, 0x8009F41, 0x1028E42, 0x4B3, 0x804024, 0x580005}, // >2.2 2.3GHz--> 0: INT=4600; 1: MOD=1000,FRAC=0; ; 2: R=10, T activo; 4: DIV 1. 
                                      { 0xFA00000, 0x8009F41, 0x1028E42, 0x4B3, 0xA04024, 0x580005},// <1.1 1GHz--> 0: INT=8000; 1: MOD=1000,FRAC=0; 2: R=10, T activo;  4: DIV 4
                                      { 0xFA00000, 0x8009F41, 0x1028E42, 0x4B3, 0xB04024, 0x580005},// <550 500MHz--> 0: INT=8000; 1: MOD=1000,FRAC=0; 2: R=10, T activo;  4: DIV 8
                                      { 0xFA00000, 0x8009F41, 0x1028E42, 0x4B3, 0xC04024, 0x580005}};// <275 250MHz--> 0: INT=8000; 1: MOD=1000,FRAC=0; 2: R=10, T activo;  4: DIV 16
      
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
void set_frec(float frec, float mfrec)
{
    unsigned long intt, register_0,frac;
    float intt_f, intt_mf, intmf;
    
    if (frec < 275.0)
    {
        divi =16;
        set_frec_values(4);
    }
    if ((frec < 550.0) && (frec >= 275.0))
    {
        divi =8;
        set_frec_values(3);
    }
    if ((frec < 1100.0) && (frec >= 550.0))
    {
        divi =4;
        set_frec_values(2);
    }
    if ((frec < 2200.0) && (frec >= 1100.0) )
    {
        divi = 2;
        set_frec_values(0);
    }
    
    if (frec >= 2200.0) 
    {
        divi =1;
        set_frec_values(1);
    }
       
    //con el divisor en 1000, no necesitaria calcular la fraccion de frec, porque siempre va a ser 0
    intt_f = (frec *invpfd * divi );// divisor es 0.5;
    intt_mf = (mfrec *invpfd * divi );//ok
    intmf = floor(intt_mf/1000);//
    intt = floor(intt_f + intmf);//ok
    intmf = floor(intt_mf/1000);// 
    frac =((invpfd * mfrec * divi) - (intmf*1000)); //modificado con el ajuste de MOD a 1000

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
void set_barrido(float frecInit, float frecEnd, float res, float resK, float retardo)
{
    init = 1;

    FrecInstant = frecInit;
    float FrecKilo = 0;
    if (frecInit < 275.0)
    {
          divi = 16;
          init = 4 ;
    }
    else if (frecInit < 550.0)
    {
          divi = 8;
          init = 3 ;
    }
    else if (frecInit < 1100.0 )
    {
          divi = 4;
          init = 2 ;
    }
    else if (frecInit < 2200.0 )
    {
          divi = 2;
          init = 0 ;
    }

    set_frec_values(init);
    while (FrecInstant < frecEnd) 
    {
        set_frec(FrecInstant,FrecKilo);
        for (int i=0;i<retardo;i++)
        {
            __delay_ms(1);
        }
        FrecKilo = FrecKilo + resK;
        if (FrecKilo == 1000.0)
        {
            FrecInstant = FrecInstant + res +  1.0;
        }
        else
        { 
            FrecInstant = FrecInstant + res;
        }
    }
    set_frec(FrecInstant,FrecKilo);
    __delay_ms(10);
 
}
