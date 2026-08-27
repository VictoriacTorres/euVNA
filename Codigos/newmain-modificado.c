/* 
 * File:   newmain.c
 * Author: brian
 *
 * Created on September 30, 2021, 00:15 PM
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

//led y pulsador
#define ledout TRISBbits.TRISB0
#define led PORTBbits.RB0
//#define botonin TRISDbits.TRISD7 // pulsaodr
//#define boton PORTDbits.RD7 // pulsador

// panel enoder TRIS
#define botonin TRISBbits.TRISB3 // pulsador econder activo bajo
#define dtin TRISBbits.TRISB4 //
#define clkin TRISBbits.TRISB5 //

//Encoder puertos
#define boton PORTBbits.RB3 //pulsador encoder activo bajo
#define dt PORTBbits.RB4 //
#define clkk PORTBbits.RB5 //

void set_registers(void);
void salidas (float resolucion, float frecuencia );

float a, res,liminf,limsup;


void main (void) {
    set_registers();
    set_lcd();
    
    lcd_start();
    res = 100;
    a = 2100;
    liminf =1100;
    limsup=2900;
    lcd_clear();
    lcd_cursor(1,1);
    lcd_print("Res = 100 ");
    lcd_cursor(2,1);
    lcd_print("Frec = 2100 ");
    led = 1;
    
    while (1) {
        
        while ((boton == 1) && (clkk == 1)){ // 0 para el pulsador, 1 para el encoder
        }
        if (boton ==0){
            __delay_ms(500);
            if ((boton ==0) && (res == 100)){
                res =1000;
                liminf=2000;
                limsup=2000;
                salidas(res,a);
            
            }
            else if ((boton == 0) && (res == 1000)){
                res = 0.001;
                liminf=1000.001;
                limsup=2999.999;
                salidas(res,a);
                
            }
            else if ((boton ==0)&&(res == 1)){
                res =10;
                liminf=1010;
                limsup=2990;
                salidas(res,a);
            }
            else if ((boton ==0)&&(res == 10)){
                res =100;
                liminf=1100;
                limsup=2900;
                salidas(res,a);
            }

	    else if ((boton ==0)&&(res == 0.1)){
                res =1;
                liminf=1001;
                limsup=2999;
                salidas(res,a);
            }
	    else if ((boton ==0)&&(res == 0.01)){
                res =0.1;
                liminf=1000.1;
                limsup=2999.9;
                salidas(res,a);
            }
            else if ((boton ==0)&&(res == 0.001)){
                res =0.01;
                liminf=1000.01;
                limsup=2999.99;
                salidas(res,a);
            }
   	   
           
        }    
            
            if (clkk == 0) {
                if (dt == 0){//giro izquierda, clkk =0 dt=0
                    if (a>=liminf){  // 
                         a = a-res;
                         set_barrido(a, a , 100);
                        if (led == 0){
                                led = 1;
                                salidas(res,a);
                                __delay_ms(1000);
                        }
                        else if (led == 1){
                                led = 0;
                                salidas(res,a);
                                __delay_ms(1000);
                                                         
                        }
                    }
                    else {
                        __delay_ms(100);
                    }
                }
            }
            if (clkk == 0 ){                 
                if  (dt == 1){        //giro derecha, clkk =0 dt=1
                    if (a<=limsup) {  // 
                        a = a+res;
                        set_barrido(a, a , 100);
                        if (led == 0){
                                led = 1;
                                salidas(res,a);
                                __delay_ms(1000);
                        }
                        else if (led == 1){
                                led = 0;
                                salidas(res,a);
                                __delay_ms(1000);
                        }
                    }
                    else {
                        __delay_ms(100);
                    }
                }
            }
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
    
    //Para encoder y el led
    ledout = 0;
    botonin = 1;
    dtin = 1;
    clkin= 1;
    
    //Init Para SPI
    CE = 1;
    DATA_S = 1;
    LE = 1;
    CLK = 0;
    __delay_ms(10);
    set_frec_values(0);
}

void salidas (float resolucion, float frecuencia ){
    char f[5],r[5];
    lcd_clear();
    lcd_cursor(1,1);
    itoa(r,resolucion,10);
    lcd_print("Res = ");
    lcd_print(r);
    lcd_cursor(2,1);
    itoa(f,frecuencia,10);
    lcd_print("Frec = ");
    lcd_print(f);
}
