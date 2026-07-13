#include <Arduino.h>
#include "config.h"
#include "maniobras.h"
#include "motores.h"
#include "boton.h"
#include "sensores_ir.h"
#include "ultrasonico.h"
#include "imu.h"
#include "movimiento.h"

long tiempoInicioBorde = -1;
int rivalPerdidoCount = 0;
int direccionGiroBusqueda = 1;

int sesgoDireccion = 0;
unsigned long tiempoSesgo = 0;
bool sesgoUsado = true;
const unsigned long DURACION_SESGO_BUSQUEDA_MS = 4000;

void maniobras_inicializar() {
  randomSeed(micros());
}

void resetear_estado_busqueda() {
  rivalPerdidoCount = 0;
  direccionGiroBusqueda = 1;
  tiempoInicioBorde = -1;
  sesgoDireccion = 0;
  sesgoUsado = true;
}

void resetear_tiempo_borde() {
  tiempoInicioBorde = -1;
}

void invertir_direccion_busqueda() {
  direccionGiroBusqueda = -direccionGiroBusqueda;
}

void marcar_sesgo_busqueda(int direccion) {
  sesgoDireccion = direccion;
  tiempoSesgo = millis();
  sesgoUsado = false;
}

bool hay_sesgo_valido() {
  return !sesgoUsado && (millis() - tiempoSesgo) < DURACION_SESGO_BUSQUEDA_MS;
}


bool maniobra_escape(Borde direccion) {
  if (direccion == BORDE_EMPUJE_IZQUIERDA) {
    avanzar();
    if (moverPorTiempo(DURACION_EMPUJE_AVANCE1_MS)) return true;
    girar_izquierda();
    if (moverPorTiempo(DURACION_EMPUJE_GIRO_MS)) return true;
    avanzar();
    if (moverPorTiempo(DURACION_EMPUJE_AVANCE2_MS)) return true;
    tiempoInicioBorde = -1;
    frenar();
    return false;
  }

  if (direccion == BORDE_EMPUJE_DERECHA) {
    avanzar();
    if (moverPorTiempo(DURACION_EMPUJE_AVANCE1_MS)) return true;
    girar_derecha();
    if (moverPorTiempo(DURACION_EMPUJE_GIRO_MS)) return true;
    avanzar();
    if (moverPorTiempo(DURACION_EMPUJE_AVANCE2_MS)) return true;
    tiempoInicioBorde = -1;
    frenar();
    return false;
  }

  if (direccion == BORDE_ATRAS) {
    avanzar();
    if (moverPorTiempo(DURACION_ESCAPE_ATRAS_MS, bordeDespejado)) return true;
    tiempoInicioBorde = -1;
    frenar();
    return false;
  }

  unsigned long ahora = millis();
  if (tiempoInicioBorde == -1) {
    tiempoInicioBorde = ahora;
  }
  unsigned long tiempoEnBorde = ahora - tiempoInicioBorde;

  if (tiempoEnBorde > UMBRAL_BORDE_SOSTENIDO_MS && !rival_detectado()) {

    if (direccion == BORDE_IZQUIERDA) {
      girar_derecha();
      if (moverPorTiempo(DURACION_GIRO_ALEJAR_MS, bordeDespejado)) return true;
      avanzar();
      if (moverPorTiempo(DURACION_AVANCE_TRAS_GIRO_MS, bordeDetectado)) return true;

    } else if (direccion == BORDE_DERECHA) {
      girar_izquierda();
      if (moverPorTiempo(DURACION_GIRO_ALEJAR_MS, bordeDespejado)) return true;
      avanzar();
      if (moverPorTiempo(DURACION_AVANCE_TRAS_GIRO_MS, bordeDetectado)) return true;

    } else {
      int lado = (random(2) == 0) ? 1 : -1;
      if (lado == 1) girar_derecha(); else girar_izquierda();
      if (moverPorTiempo(DURACION_GIRO_ALEATORIO_MS, bordeDespejado)) return true;
      avanzar();
      if (moverPorTiempo(DURACION_AVANCE_ALEATORIO_MS, bordeDetectado)) return true;
    }

    tiempoInicioBorde = -1;
    frenar();
    return false;
  }

  retroceder();
  if (moverPorTiempo(DURACION_RETROCESO_FRESCO_MS, bordeDetectado)) return true;
  frenar();

  if (direccion == BORDE_FRENTE || direccion == BORDE_FRENTE_IZQ) {
    girar_derecha();
    if (moverPorTiempo(DURACION_GIRO_FRENTE_MS, bordeDetectado)) return true;
  } else if (direccion == BORDE_IZQUIERDA) {
    girar_izquierda();
    if (moverPorTiempo(DURACION_GIRO_LATERAL_FRESCO_MS, bordeDetectado)) return true;
  } else if (direccion == BORDE_DERECHA) {
    girar_izquierda();
    if (moverPorTiempo(DURACION_GIRO_LATERAL_FRESCO_MS, bordeDetectado)) return true;
  }

  frenar();
  return false;
}

bool escapar_levantamiento() {
  Serial.println("LEVANTAMIENTO DETECTADO: escapando");
  girar_izquierda();
  unsigned long inicio = millis();
  while (true) {
    if (boton_presionado()) {
      frenar();
      return true;
    }
    float x, y, z;
    leerAceleracion(x, y, z);
    if (z > UMBRAL_SALIDA_LEVANTAMIENTO_Z) {
      break;
    }
    if (millis() - inicio > 3000) {
      break;
    }
  }
  frenar();
  resetear_deteccion_levantamiento();
  return false;
}

const unsigned long DURACION_EMPUJE_SOSTENIDO_MS = 800;
const unsigned long INTERVALO_MUESTRA_DISTANCIA_MS = 400;
const long PROGRESO_MINIMO_CM = 3;
const unsigned long DURACION_RETROCESO_ATASCADO_MS = 200;
const float GRADOS_REPOSICION_ATASCADO = 30;

bool reaccionar_impacto_frente() {
  Serial.println("IMPACTO FRENTE: empuje sostenido");
  marcar_impacto_frente_reciente();

  long distanciaReferencia = medir_distancia_mediana_cm();
  avanzar();

  unsigned long inicio = millis();
  unsigned long ultimaMuestraDistancia = inicio;

  while (millis() - inicio < DURACION_EMPUJE_SOSTENIDO_MS) {
    if (boton_presionado()) {
      frenar();
      return true;
    }
    if (bordeDetectado()) {
      break;
    }

    if (millis() - ultimaMuestraDistancia >= INTERVALO_MUESTRA_DISTANCIA_MS) {
      ultimaMuestraDistancia = millis();
      long distanciaActual = medir_distancia_mediana_cm();

      if (distanciaReferencia - distanciaActual < PROGRESO_MINIMO_CM) {
        Serial.println("EMPUJE ATASCADO: reposicionando");
        retroceder();
        if (moverPorTiempo(DURACION_RETROCESO_ATASCADO_MS)) return true;
        int lado = (random(2) == 0) ? 1 : -1;
        if (girar_grados(lado, GRADOS_REPOSICION_ATASCADO)) return true;
        frenar();
        return false;
      }

      distanciaReferencia = distanciaActual;
    }
  }

  frenar();
  return false;
}

bool reaccionar_impacto(Impacto impacto) {
  if (impacto == IMPACTO_LATERAL_IZQUIERDA) {
    Serial.println("IMPACTO LATERAL IZQUIERDA: girando hacia el golpe");
    marcar_sesgo_busqueda(-1);
    return girar_grados(-1, 90);
  }

  if (impacto == IMPACTO_LATERAL_DERECHA) {
    Serial.println("IMPACTO LATERAL DERECHA: girando hacia el golpe");
    marcar_sesgo_busqueda(1);
    return girar_grados(1, 90);
  }

  if (impacto == IMPACTO_ATRAS) {
    Serial.println("IMPACTO ATRAS: girando para reencarar");
    return girar_grados(1, 150);
  }

  if (impacto == IMPACTO_FRENTE) {
    return reaccionar_impacto_frente();
  }

  return false;
}

bool escapar_impactos_repetidos() {
  Serial.println("IMPACTOS REPETIDOS: maniobra de emergencia");
  retroceder();
  if (moverPorTiempo(DURACION_EMERGENCIA_IMPACTO_RETROCESO_MS, bordeDetectado)) return true;
  frenar();

  int lado = (random(2) == 0) ? 1 : -1;
  if (girar_grados(lado, GRADOS_EMERGENCIA_IMPACTO)) return true;

  frenar();
  return false;
}

bool buscar_y_atacar() {
  if (boton_presionado()) return true;

  if (rival_detectado()) {
    rivalPerdidoCount = 0;
    avanzar();
    if (moverPorTiempo(DURACION_AVANCE_RIVAL_MS, bordeDetectado)) return true;

  } else {
    rivalPerdidoCount++;

    if (rivalPerdidoCount < MAX_PERDIDO) {
      avanzar();
      if (moverPorTiempo(DURACION_AVANCE_PRIMER_INTENTO_MS, bordeDetectado)) return true;
      return false;
    }

    int direccionEfectiva = direccionGiroBusqueda;
    if (hay_sesgo_valido()) {
      direccionEfectiva = sesgoDireccion;
      sesgoUsado = true;
      Serial.println("BUSQUEDA: usando sesgo de ultimo impacto");
    }

    if (direccionEfectiva == 1) girar_derecha(); else girar_izquierda();
    unsigned long inicio = millis();
    while (millis() - inicio < TIEMPO_GIRO_360_MS) {
      if (boton_presionado()) return true;
      if (rival_detectado()) {
        rivalPerdidoCount = 0;
        return false;
      }
      if (leer_borde_mejorado() != BORDE_NINGUNO) return false;
    }
    direccionGiroBusqueda = -direccionGiroBusqueda;
  }

  return false;
}

void inicio_ronda(int ronda) {
  if (ronda == 1) {
    avanzar();
    unsigned long inicio = millis();
    while (millis() - inicio < 300) {
      if (leer_borde_mejorado() != BORDE_NINGUNO) break;
      if (rival_detectado()) {
        avanzar();
        break;
      }
    }

  } else if (ronda == 2) {
    girar_grados(1, 45);

  } else if (ronda == 3) {
    girar_grados(-1, 120);
  }

  frenar();
}
