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
void salidas (float resolucion, float frecuencia, float mresolucion, float mfrecuencia );
void delay1Seg(void);
void delayHalfSeg(void);
void delay100mSeg(void);

float a, res,liminf,limsup,mres,ma;


void main (void) {
    set_registers();
    set_lcd();
    
    lcd_start();
    res = 100;
    a = 2300;
    mres=0;
    ma=0;
    liminf =651;
    limsup=4299;
    lcd_clear();
    lcd_cursor(1,1);
    lcd_print("Res = 100M 0K");
    lcd_cursor(2,1);
    lcd_print("Frec = 2100M 0K ");
    led = 1;
    
    while (1) {
        
        while ((boton == 1) && (clkk == 1)){ // 0 para el pulsador, 1 para el encoder
        }
        if (boton ==0){
            delayHalfSeg();
            //__delay_ms(500);
            if ((boton ==0) && (res == 100) && (mres == 0)){
                res =1000;
                mres=0;
                liminf=2000;
                limsup=3000;
                salidas(res,a,mres,ma);
            
            }
            else if ((boton == 0) && (res == 1000) && (mres == 0)){
                res = 0;
                mres=1;
                liminf=550.001;
                limsup=4399.999;
                salidas(res,a,mres,ma);
                
            }
            else if ((boton ==0)&&(res == 1) && (mres == 0)){
                res =10;
                mres=0;
                liminf=560;
                limsup=4390;
                salidas(res,a,mres,ma);
            }
            else if ((boton ==0)&&(res == 10) && (mres == 0)){
                res =100;
                mres=0;
                liminf=651;
                limsup=4299;
                salidas(res,a,mres,ma);
            }

	    else if ((boton ==0)&&(res == 0) && (mres == 100)){
                res =1;
                mres=0;
                liminf=551;
                limsup=4399;
                salidas(res,a,mres,ma);
            }
	    else if ((boton ==0)&&(res == 0) && (mres == 10)){
                res =0;
                mres=100;
                liminf=550.1;
                limsup=4399.9;
                salidas(res,a,mres,ma);
            }
            else if ((boton ==0)&&(res == 0) && (mres == 1)){
                res =0;
                mres=10;
                liminf=550.01;
                limsup=4399.99;
                salidas(res,a,mres,ma);
            }
   	             
        }    
        
        
            if (clkk == 0) {
                if (dt == 0){//giro izquierda, clkk =0 dt=0
                    if (a>=liminf){  // 
                         a = a-res;
                         ma = ma-mres;
                                               
                         if (ma < 0){
                             ma=1000+ma;
                             a=a-1;
                         }
                         
                         //set_barrido(a, a , 100);
                         set_frec(a,ma);//hay que modificar set_frec
                        if (led == 0){
                                led = 1;
                                salidas(res,a,mres,ma);
                                delay1Seg();
                                //__delay_ms(1000);
                        }
                        else if (led == 1){
                                led = 0;
                                salidas(res,a,mres,ma);
                                delay1Seg();
                                //__delay_ms(1000);
                                                         
                        }
                    }
                    else {
                        delay100mSeg();
                        //__delay_ms(100);
                    }
                }
            }
            if (clkk == 0 ){                 
                if  (dt == 1){        //giro derecha, clkk =0 dt=1
                    if (a<=limsup) {  // 
                        a = a+res;
                        ma = ma+mres;
                        
                        
                        if (ma > 999){
                             ma=ma-1000;
                             a=a+1;
                         }
                                                 
                        //set_barrido(a, a , 100);
                        set_frec(a,ma);
                        if (led == 0){
                                led = 1;
                                salidas(res,a,mres,ma);
                                delay1Seg();
                                //__delay_ms(1000);
                        }
                        else if (led == 1){
                                led = 0;
                                salidas(res,a,mres,ma);
                                delay1Seg();
                                //__delay_ms(1000);
                        }
                    }
                    else {
                        delayHalfSeg();
                        //__delay_ms(100);
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

void salidas (float resolucion,float frecuencia, float mresolucion, float mfrecuencia ){
    char f[5],r[5],rr[3],ff[3];
    
   /* if (mresolucion ==0){
        rr[0] = ' ';
        rr[1] = ' ';
        rr[2] = ' ';
    }
    else if (mresolucion ==1){
        rr[0] = '0';
        rr[1] = '0';
        rr[2] = '1';
    }
    else if (mresolucion ==10){
        rr[0] = '0';
        rr[1] = '1';
        rr[2] = ' ';
    }
    else if (mresolucion ==100){
        rr[0] = '1';
        rr[1] = ' ';
        rr[2] = ' ';
    }*/
    
    
          
    lcd_clear();
    lcd_cursor(1,1);
    
    itoa(r,resolucion,10);    
    itoa(rr,mresolucion,10); 
    lcd_print("Res = ");
    lcd_print(r);
    lcd_print("M ");
    lcd_print(rr);
    lcd_print("K ");
    
    lcd_cursor(2,1);
    itoa(f,frecuencia,10);
    itoa(ff,mfrecuencia,10);
    lcd_print("Frec = ");
    lcd_print(f);
    lcd_print("M");
    lcd_print(ff);
    lcd_print("K");
    
}


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