#include <Arduino.h>
#include "config.h"
#include "motores.h"

void establecerMotor(int canalA, int canalB, float valor) {
  valor = constrain(valor, -1.0, 1.0);
  int duty = (int)(fabs(valor) * 255);

  if (valor > 0) {
    ledcWrite(canalA, duty);
    ledcWrite(canalB, 0);
  } else if (valor < 0) {
    ledcWrite(canalA, 0);
    ledcWrite(canalB, duty);
  } else {
    ledcWrite(canalA, 0);
    ledcWrite(canalB, 0);
  }
}

void motores_inicializar() {
  ledcSetup(CH_M1_A, PWM_FREQ, PWM_RES);
  ledcAttachPin(M1_A, CH_M1_A);
  ledcSetup(CH_M1_B, PWM_FREQ, PWM_RES);
  ledcAttachPin(M1_B, CH_M1_B);
  ledcSetup(CH_M2_A, PWM_FREQ, PWM_RES);
  ledcAttachPin(M2_A, CH_M2_A);
  ledcSetup(CH_M2_B, PWM_FREQ, PWM_RES);
  ledcAttachPin(M2_B, CH_M2_B);

  frenar();
}

void arrancar_motores(float m1, float m2) {
  float valorM1 = INVERTIR_M1 ? -m1 : m1;
  float valorM2 = INVERTIR_M2 ? m2 : -m2;
  establecerMotor(CH_M2_A, CH_M2_B, valorM1);
  establecerMotor(CH_M1_A, CH_M1_B, valorM2);
}

void frenar() {
  arrancar_motores(0.0, 0.0);
}

void avanzar() {
  arrancar_motores(1.0, 1.0);
}

void retroceder() {
  arrancar_motores(-1.0, -1.0);
}

void girar_izquierda() {
  arrancar_motores(1.0, -1.0);
}

void girar_derecha() {
  arrancar_motores(-1.0, 1.0);
}
