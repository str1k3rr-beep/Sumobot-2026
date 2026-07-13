#include <Arduino.h>
#include "config.h"
#include "estado_juego.h"
#include "boton.h"
#include "motores.h"
#include "sensores_ir.h"
#include "imu.h"
#include "led.h"
#include "maniobras.h"
#include "movimiento.h"

enum EstadoJuego { ESPERANDO_INICIO, EN_COMBATE, PARTIDA_TERMINADA };

EstadoJuego estado = ESPERANDO_INICIO;
int ronda = 1;
bool blinkPendiente = true;

int escapesSeguidos = 0;
unsigned long tiempoUltimoEscape = 0;

int impactosSeguidos = 0;
unsigned long tiempoUltimoImpacto = 0;

unsigned long tiempoUltimaLecturaIMU = 0;

void estado_juego_inicializar() {
  estado = ESPERANDO_INICIO;
  ronda = 1;
  blinkPendiente = true;
  escapesSeguidos = 0;
  impactosSeguidos = 0;
}

void terminar_ronda_actual() {
  frenar();
  Serial.print("Ronda ");
  Serial.print(ronda);
  Serial.println(" terminada.");

  ronda++;
  if (ronda > 3) {
    estado = PARTIDA_TERMINADA;
    Serial.println("Partida completa.");
  } else {
    estado = ESPERANDO_INICIO;
    blinkPendiente = true;
  }
}

void actualizar_juego() {
  if (estado == PARTIDA_TERMINADA) {
    return;
  }

  if (estado == ESPERANDO_INICIO) {
    if (blinkPendiente) {
      Serial.print("=== RONDA ");
      Serial.print(ronda);
      Serial.println(" ===");
      senalar_ronda(ronda);
      blinkPendiente = false;
    }

    if (boton_presionado()) {
      resetear_estado_busqueda();
      resetear_deteccion_levantamiento();
      escapesSeguidos = 0;
      impactosSeguidos = 0;
      inicio_ronda(ronda);
      estado = EN_COMBATE;
      Serial.println("ACTIVO");
    }
    return;
  }

  if (boton_presionado()) {
    terminar_ronda_actual();
    return;
  }

  if (imuDisponible) {
    unsigned long intervaloIMU = debe_muestrear_rapido() ? 5 : 20;

    if (millis() - tiempoUltimaLecturaIMU >= intervaloIMU) {
      tiempoUltimaLecturaIMU = millis();

      if (detectar_levantamiento_sostenido()) {
        if (escapar_levantamiento()) {
          terminar_ronda_actual();
        }
        return;
      }

      Impacto impacto = detectar_impacto();
      if (impacto != IMPACTO_NINGUNO) {
        Serial.print("IMPACTO: ");
        if (impacto == IMPACTO_LATERAL_IZQUIERDA) Serial.println("LATERAL_IZQUIERDA");
        else if (impacto == IMPACTO_LATERAL_DERECHA) Serial.println("LATERAL_DERECHA");
        else if (impacto == IMPACTO_ATRAS) Serial.println("ATRAS");
        else Serial.println("FRENTE");

        unsigned long ahoraImpacto = millis();
        if (ahoraImpacto - tiempoUltimoImpacto < VENTANA_IMPACTOS_MS) {
          impactosSeguidos++;
        } else {
          impactosSeguidos = 1;
        }
        tiempoUltimoImpacto = ahoraImpacto;

        if (impactosSeguidos >= LIMITE_IMPACTOS_LOOP) {
          if (escapar_impactos_repetidos()) {
            terminar_ronda_actual();
          }
          impactosSeguidos = 0;
          return;
        }

        if (reaccionar_impacto(impacto)) {
          terminar_ronda_actual();
        }
        return;
      }
    }
  }

  Borde borde = leer_borde_mejorado();

  if (borde != BORDE_NINGUNO) {
    unsigned long ahora = millis();
    if (ahora - tiempoUltimoEscape < VENTANA_LOOP_MS) {
      escapesSeguidos++;
    } else {
      escapesSeguidos = 1;
    }
    tiempoUltimoEscape = ahora;

    if (escapesSeguidos >= LIMITE_ESCAPES_LOOP) {
      Serial.println("BUCLE DETECTADO: maniobra de emergencia");
      retroceder();
      if (moverPorTiempo(DURACION_EMERGENCIA_RETROCESO_MS)) {
        terminar_ronda_actual();
        return;
      }
      frenar();
      invertir_direccion_busqueda();
      escapesSeguidos = 0;
      resetear_tiempo_borde();
      return;
    }

    Serial.print("ESCAPANDO: ");
    Serial.println(NOMBRES_BORDE[borde]);
    if (maniobra_escape(borde)) {
      terminar_ronda_actual();
    }
    return;
  }

  resetear_tiempo_borde();

  if (buscar_y_atacar()) {
    terminar_ronda_actual();
  }
}
