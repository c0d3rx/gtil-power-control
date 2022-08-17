#include <stdlib.h>
#include <stdio.h>
#include <string.h>
#include <ArduinoRS485.h> // ArduinoModbus depends on the ArduinoRS485 library
#include <ArduinoModbus.h>

const byte TRIAC_PIN = 9;
const byte ZC_EI_PIN = 2;

unsigned long topMicroseconds = 9800; // 10000 micros is between zero crossings
int prescaler = 8;
byte prescalerBits = _BV(CS11); // 8

void zeroCrossing() {
  TCNT1 = 0; // reset the timer counter
}

void setup() {

  static RS485Class rs485(Serial, -1, -1, -1) ;


  attachInterrupt(digitalPinToInterrupt(ZC_EI_PIN), zeroCrossing, RISING);

  pinMode(TRIAC_PIN, OUTPUT);
  uint32_t topPeriod = ((F_CPU / 1000000)* topMicroseconds) / prescaler ;
  Serial.println(topPeriod);
  ICR1 = topPeriod;  
  // WGM mode 14 - Fast PWM w/TOP=ICR1 
  TCCR1A = _BV(WGM11) | _BV(COM1A0) | _BV(COM1A1);
  TCCR1B = _BV(WGM13) | _BV(WGM12) | prescalerBits;
  
  OCR1A = topPeriod + 1; // full off

  // start the Modbus RTU server, with (slave) id 1
  if (!ModbusRTUServer.begin(rs485, 1, 9600)) {
    Serial.println("Failed to start Modbus RTU Server!");
    while (1);
  }
  
  ModbusRTUServer.configureHoldingRegisters(0x00, 2);  


}

void loop() {
  
    long rawValue;

    // poll for Modbus RTU requests
    int avail = ModbusRTUServer.poll();
    if (avail){
      rawValue = ModbusRTUServer.holdingRegisterRead(0);
      uint32_t period = ((F_CPU / 1000000)* rawValue) / prescaler ;
      OCR1A = period;
    }

    
  
}
