#include <Arduino.h>
#include "boton.h"
#include "motores.h"
#include "sensores_ir.h"
#include "ultrasonico.h"
#include "imu.h"
#include "led.h"
#include "maniobras.h"
#include "estado_juego.h"

void setup() {
  Serial.begin(115200);

  boton_inicializar();
  sensores_ir_inicializar();
  ultrasonico_inicializar();
  led_inicializar();
  imu_inicializar();
  motores_inicializar();
  maniobras_inicializar();
  estado_juego_inicializar();

  delay(1000);
}

void loop() {
  actualizar_juego();
}
