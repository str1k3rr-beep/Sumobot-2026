#pragma once

#define SEN1 36
#define SEN2 39
#define SEN3 34
#define SEN4 35

#define M1_A 12
#define M1_B 14
#define M2_A 13
#define M2_B 15

#define TRIG_PIN 25
#define ECHO_PIN 26

#define BOOT_PIN 0
#define DEBOUNCE_MS 50

#define PWM_FREQ 20000
#define PWM_RES 8

#define CH_M1_A 0
#define CH_M1_B 1
#define CH_M2_A 2
#define CH_M2_B 3

#define PIN_LED 2

const bool INVERTIR_M1 = false;
const bool INVERTIR_M2 = false;

const int DISTANCIA_RIVAL_CM = 40;

const int MAX_PERDIDO = 1;
const unsigned long TIEMPO_GIRO_360_MS = 2900;
const unsigned long TIEMPO_360_FALLBACK_MS = 2900;

const unsigned long DURACION_EMPUJE_AVANCE1_MS = 250;
const unsigned long DURACION_EMPUJE_GIRO_MS = 250;
const unsigned long DURACION_EMPUJE_AVANCE2_MS = 200;
const unsigned long DURACION_ESCAPE_ATRAS_MS = 300;

const unsigned long UMBRAL_BORDE_SOSTENIDO_MS = 200;
const unsigned long DURACION_GIRO_ALEJAR_MS = 200;
const unsigned long DURACION_AVANCE_TRAS_GIRO_MS = 150;
const unsigned long DURACION_GIRO_ALEATORIO_MS = 250;
const unsigned long DURACION_AVANCE_ALEATORIO_MS = 100;

const unsigned long DURACION_RETROCESO_FRESCO_MS = 50;
const unsigned long DURACION_GIRO_FRENTE_MS = 350;
const unsigned long DURACION_GIRO_LATERAL_FRESCO_MS = 200;

const unsigned long DURACION_AVANCE_RIVAL_MS = 50;
const unsigned long DURACION_AVANCE_PRIMER_INTENTO_MS = 0;

const unsigned long DURACION_EMERGENCIA_RETROCESO_MS = 400;

const unsigned long VENTANA_LOOP_MS = 3000;
const int LIMITE_ESCAPES_LOOP = 3;

const unsigned long VENTANA_IMPACTOS_MS = 3000;
const int LIMITE_IMPACTOS_LOOP = 3;
const unsigned long DURACION_EMERGENCIA_IMPACTO_RETROCESO_MS = 350;
const float GRADOS_EMERGENCIA_IMPACTO = 180;

const float UMBRAL_IMPACTO = 2.5;
const float UMBRAL_LEVANTAMIENTO_Z = 9.10;
const float UMBRAL_SALIDA_LEVANTAMIENTO_Z = 9.50;
const unsigned long TIEMPO_CONFIRMACION_LEVANTAMIENTO = 1250;
