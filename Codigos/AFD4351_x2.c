/*
 * File:   ADF4351.c
 *
 * Project: microVNA
 *
 * Author: Leonardo David Vazquez
 *
 * Date:  09 / 09 / 2024
 *
 * Version: 0.1
 *          Definición de funciones (Ver GlucoLAC)
 *          Configurado para 2 generadores
 */

#define _XTAL_FREQ 48000000 //The speed of your internal(or)external oscillator

#include <xc.h>                     //Library for compiler
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "math.h"

//Definiciones
#define CLK1 LATCbits.LATC0 //PIN_C0
#define DATA_S1 LATCbits.LATC1 //PIN_C1
#define LE1 LATCbits.LATC2 //PIN_C2
#define CE1 LATAbits.LATA5 //PIN_/A5---------------------------
#define bittest1(D,i) ( ( (D) & ( ( (unsigned long) 1 << (i) ) ) ) &&  ( ( (unsigned long) 1 << (i) ) ) )

#define CLK2 LATDbits.LATD2 //PIN_D2
#define DATA_S2 LATDbits.LATD3 //PIN_D3
#define LE2 LATCbits.LATC6 //PIN_C6
#define CE2 LATCbits.LATC7 //PIN_C7 
#define bittest2(D,i) ( ( (D) & ( ( (unsigned long) 1 << (i) ) ) ) &&  ( ( (unsigned long) 1 << (i) ) ) )

//Definicion de variables
float invpfd = 2; //modificado, lo seteo ahora y listo
float divi = 1;
unsigned long init;
float FrecInstant;

//// LEO 

void set_frec_values_1(int initFrec)
{
      //moficado, ajusto los registros para MOD = 1000, pfd = 0.5, R = 10, T activo 
      static const unsigned long FREC_INIT[1][6]={{ 0x9600000, 0x8000011, 0x1028E42, 0x4B3, 0xB0403C, 0x580005}};// >275 300MHz
      
     CE1 = 0;        //CE Select device

     for (int i = 0; i <= 5; i++)           // para 6 registros
     {
         LE1 = 0;
         for (int m = 0; m <= 31; m++)      //para 32 bits
         {
             CLK1 = 0;
             DATA_S1 = bittest1(FREC_INIT[initFrec][5-i],31-m);
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
}

void set_frec_values_2(int initFrec)
{
      //moficado, ajusto los registros para MOD = 1000, pfd = 0.5, R = 10, T activo 
      static const unsigned long FREC_INIT[1][6]={{ 0x9600020, 0x80000C9, 0x1028E42, 0x4B3, 0xB0403C, 0x580005}};// >275 300MHz + 10 kHz
      
     CE1 = 0;        //CE Select device

     for (int i = 0; i <= 5; i++)           // para 6 registros
     {
         LE2 = 0;
         for (int m = 0; m <= 31; m++)      //para 32 bits
         {
             CLK2 = 0;
             DATA_S2 = bittest2(FREC_INIT[initFrec][5-i],31-m);
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
}

