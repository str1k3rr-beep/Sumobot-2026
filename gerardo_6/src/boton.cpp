#include <Arduino.h>
#include "config.h"
#include "boton.h"

int ultimaLecturaBoton = HIGH;
int estadoBotonEstable = HIGH;
unsigned long ultimoRebote = 0;

void boton_inicializar() {
  pinMode(BOOT_PIN, INPUT_PULLUP);
}

bool boton_presionado() {
  int lectura = digitalRead(BOOT_PIN);

  if (lectura != ultimaLecturaBoton) {
    ultimoRebote = millis();
  }

  bool disparo = false;
  if ((millis() - ultimoRebote) > DEBOUNCE_MS) {
    if (lectura != estadoBotonEstable) {
      estadoBotonEstable = lectura;
      if (estadoBotonEstable == LOW) {
        disparo = true;
      }
    }
  }

  ultimaLecturaBoton = lectura;
  return disparo;
}
