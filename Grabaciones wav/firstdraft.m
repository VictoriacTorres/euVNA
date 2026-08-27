[y,Fs] = audioread('Grabación Prueba 15-05-26.wav'); %primera columna canal izquierdo, segunda derecho
c_izq = y(:, 1);
c_der   = y(:, 2);
t = (0:length(y)-1) / Fs;

L=length(c_izq);
fft_izq=fft(c_izq);
fft_der=fft(c_der);

P2 = abs(fft_izq/L);
P1 = P2(1:floor(L/2)+1);
P1(2:end-1) = 2*P1(2:end-1);

f = Fs/L*(0:(L/2));
plot(f,P1,'LineWidth',3) 
title('Single-Sided Amplitude Spectrum of X(t)')
xlabel('f (Hz)')
ylabel('|P1(f)|')

%plot(Fs/L*(-L/2:L/2-1),abs(fftshift(fft_izq)),'LineWidth',3)
%title('fft Spectrum in the Positive and Negative Frequencies')
%xlabel('f (Hz)')
%ylabel('|fft(y)|')
%plot(t,y)
%xlabel('Time')
%ylabel('Audio Signal')