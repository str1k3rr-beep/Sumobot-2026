#include <Arduino.h>
#include "config.h"
#include "movimiento.h"
#include "motores.h"
#include "boton.h"
#include "imu.h"

bool moverPorTiempo(unsigned long duracionMs, bool (*condicionSalida)()) {
  unsigned long inicio = millis();
  while (millis() - inicio < duracionMs) {
    if (boton_presionado()) return true;
    if (condicionSalida != nullptr && condicionSalida()) break;
  }
  return false;
}

bool girar_grados(int lado, float grados) {
  if (!imuDisponible) {
    if (lado == 1) girar_derecha(); else girar_izquierda();
    unsigned long duracionFallback = (unsigned long)(TIEMPO_360_FALLBACK_MS * (grados / 360.0));
    bool interrumpido = moverPorTiempo(duracionFallback);
    frenar();
    return interrumpido;
  }

  if (lado == 1) girar_derecha(); else girar_izquierda();

  float acumulado = 0.0;
  unsigned long anterior = millis();

  while (fabs(acumulado) < grados) {
    if (boton_presionado()) {
      frenar();
      return true;
    }
    unsigned long ahora = millis();
    float deltaSeg = (ahora - anterior) / 1000.0;
    anterior = ahora;
    acumulado += leerGyroZ_dps() * deltaSeg;
    delay(2);
  }

  frenar();
  return false;
}
