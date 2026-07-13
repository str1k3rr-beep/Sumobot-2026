#include <Arduino.h>
#include <Adafruit_NeoPixel.h>
#include <Wire.h>
#include <Adafruit_LSM6DS3TRC.h>

#define PIN_LED 2
Adafruit_NeoPixel pixel(1, PIN_LED, NEO_GRB + NEO_KHZ800);

Adafruit_LSM6DS3TRC imu;
bool imuDisponible = false;

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

const bool INVERTIR_M1 = false;
const bool INVERTIR_M2 = false;

int umbrales[4] = {300, 300, 300, 300};

long tiempoInicioBorde = -1;

const int MAX_PERDIDO = 1;
const unsigned long TIEMPO_GIRO_360_MS = 2900;
int rivalPerdidoCount = 0;
int direccionGiroBusqueda = 1;

const int DISTANCIA_RIVAL_CM = 40;

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

int ultimaLecturaBoton = HIGH;
int estadoBotonEstable = HIGH;
unsigned long ultimoRebote = 0;

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

long medir_distancia_cm() {
  digitalWrite(TRIG_PIN, LOW);
  delayMicroseconds(2);
  digitalWrite(TRIG_PIN, HIGH);
  delayMicroseconds(10);
  digitalWrite(TRIG_PIN, LOW);

  long duracion = pulseIn(ECHO_PIN, HIGH, 8000);
  if (duracion == 0) return 999;

  return duracion * 0.0343 / 2;
}

long medir_distancia_mediana_cm() {
  long d1 = medir_distancia_cm();
  delay(5);
  long d2 = medir_distancia_cm();
  delay(5);
  long d3 = medir_distancia_cm();

  if (d1 > d2) { long t = d1; d1 = d2; d2 = t; }
  if (d2 > d3) { long t = d2; d2 = d3; d3 = t; }
  if (d1 > d2) { long t = d1; d1 = d2; d2 = t; }

  return d2;
}

bool rival_detectado() {
  return medir_distancia_mediana_cm() < DISTANCIA_RIVAL_CM;
}

float offsetGyroZ = 0.0;

void leerAceleracion(float &x, float &y, float &z) {
  sensors_event_t accel, gyro, temp;
  imu.getEvent(&accel, &gyro, &temp);
  x = accel.acceleration.x;
  y = accel.acceleration.y;
  z = accel.acceleration.z;
}

float offsetAccelX = 0.0;
float offsetAccelY = 0.0;
float offsetAccelZ = 0.0;

void calibrarOffsetAccel() {
  const int MUESTRAS = 200;
  float sumaX = 0.0;
  float sumaY = 0.0;
  float sumaZ = 0.0;

  for (int i = 0; i < MUESTRAS; i++) {
    float x, y, z;
    leerAceleracion(x, y, z);
    sumaX += x;
    sumaY += y;
    sumaZ += z;
    delay(5);
  }

  offsetAccelX = sumaX / MUESTRAS;
  offsetAccelY = sumaY / MUESTRAS;
  offsetAccelZ = sumaZ / MUESTRAS;
  Serial.print("Offset accel X: ");
  Serial.print(offsetAccelX, 2);
  Serial.print("  Y: ");
  Serial.print(offsetAccelY, 2);
  Serial.print("  Z: ");
  Serial.println(offsetAccelZ, 2);
}

enum Impacto { IMPACTO_NINGUNO, IMPACTO_LATERAL_IZQUIERDA, IMPACTO_LATERAL_DERECHA, IMPACTO_ATRAS, IMPACTO_FRENTE };

const float UMBRAL_IMPACTO = 2.5;

Impacto detectar_impacto() {
  float x, y, z;
  leerAceleracion(x, y, z);

  float desviacionX = x - offsetAccelX;
  float desviacionY = fabs(y - offsetAccelY);

  if (fabs(desviacionX) > UMBRAL_IMPACTO && fabs(desviacionX) > desviacionY) {
    if (desviacionX > 0) {
      return IMPACTO_LATERAL_IZQUIERDA;
    }
    return IMPACTO_LATERAL_DERECHA;
  }

  if (desviacionY > UMBRAL_IMPACTO) {
    if (rival_detectado()) {
      return IMPACTO_FRENTE;
    }
    return IMPACTO_ATRAS;
  }

  return IMPACTO_NINGUNO;
}

bool girar_grados(int lado, float grados);

bool reaccionar_impacto(Impacto impacto) {
  if (impacto == IMPACTO_LATERAL_IZQUIERDA) {
    Serial.println("IMPACTO LATERAL IZQUIERDA: girando hacia el golpe");
    return girar_grados(-1, 90);
  }

  if (impacto == IMPACTO_LATERAL_DERECHA) {
    Serial.println("IMPACTO LATERAL DERECHA: girando hacia el golpe");
    return girar_grados(1, 90);
  }

  if (impacto == IMPACTO_ATRAS) {
    Serial.println("IMPACTO ATRAS: girando para reencarar");
    return girar_grados(1, 150);
  }

  return false;
}

const float UMBRAL_LEVANTAMIENTO_Z = 9.10;
const unsigned long TIEMPO_CONFIRMACION_LEVANTAMIENTO = 1250;

unsigned long inicioPosibleLevantamiento = 0;

bool esta_nivelado() {
  float x, y, z;
  leerAceleracion(x, y, z);
  return z >= UMBRAL_LEVANTAMIENTO_Z;
}

bool detectar_levantamiento_sostenido() {
  if (esta_nivelado()) {
    inicioPosibleLevantamiento = 0;
    return false;
  }

  if (inicioPosibleLevantamiento == 0) {
    inicioPosibleLevantamiento = millis();
    return false;
  }

  return (millis() - inicioPosibleLevantamiento) > TIEMPO_CONFIRMACION_LEVANTAMIENTO;
}

const float UMBRAL_SALIDA_LEVANTAMIENTO_Z = 9.50;

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
    Serial.print("z durante escape: ");
    Serial.println(z, 2);
    if (z > UMBRAL_SALIDA_LEVANTAMIENTO_Z) {
      break;
    }
    if (millis() - inicio > 3000) {
      break;
    }
  }
  frenar();
  inicioPosibleLevantamiento = 0;
  return false;
}

float leerGyroZ_dps() {
  sensors_event_t accel, gyro, temp;
  imu.getEvent(&accel, &gyro, &temp);
  float gradosPorSeg = gyro.gyro.z * 180.0 / PI;
  return gradosPorSeg - offsetGyroZ;
}

void calibrarDriftGyro() {
  const int MUESTRAS = 200;
  float suma = 0.0;

  for (int i = 0; i < MUESTRAS; i++) {
    sensors_event_t accel, gyro, temp;
    imu.getEvent(&accel, &gyro, &temp);
    suma += gyro.gyro.z * 180.0 / PI;
    delay(5);
  }

  offsetGyroZ = suma / MUESTRAS;
  Serial.print("Offset gyro Z: ");
  Serial.println(offsetGyroZ);
}

const unsigned long TIEMPO_360_FALLBACK_MS = 2900;

bool girar_grados(int lado, float grados) {
  if (!imuDisponible) {
    if (lado == 1) girar_derecha(); else girar_izquierda();
    unsigned long inicioFallback = millis();
    unsigned long duracionFallback = (unsigned long)(TIEMPO_360_FALLBACK_MS * (grados / 360.0));
    while (millis() - inicioFallback < duracionFallback) {
      if (boton_presionado()) {
        frenar();
        return true;
      }
    }
    frenar();
    return false;
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

void leer_sensores(int lecturas[4]) {
  lecturas[0] = analogRead(SEN1);
  lecturas[1] = analogRead(SEN2);
  lecturas[2] = analogRead(SEN3);
  lecturas[3] = analogRead(SEN4);
}

enum Borde {
  BORDE_NINGUNO,
  BORDE_FRENTE,
  BORDE_ATRAS,
  BORDE_IZQUIERDA,
  BORDE_DERECHA,
  BORDE_FRENTE_IZQ,
  BORDE_EMPUJE_IZQUIERDA,
  BORDE_EMPUJE_DERECHA
};

const char* NOMBRES_BORDE[] = {"NINGUNO", "FRENTE", "ATRAS", "IZQUIERDA", "DERECHA", "FRENTE_IZQ", "EMPUJE_IZQUIERDA", "EMPUJE_DERECHA"};

void leer_sensores_bool(bool detectados[4]) {
  int lecturas[4];
  leer_sensores(lecturas);
  for (int i = 0; i < 4; i++) {
    detectados[i] = lecturas[i] < umbrales[i];
  }
}

Borde leer_borde_mejorado() {
  bool d1[4];
  leer_sensores_bool(d1);
  if (!(d1[0] || d1[1] || d1[2] || d1[3])) return BORDE_NINGUNO;

  bool d2[4];
  leer_sensores_bool(d2);

  bool detectados[4];
  for (int i = 0; i < 4; i++) {
    detectados[i] = d1[i] && d2[i];
  }
  if (!(detectados[0] || detectados[1] || detectados[2] || detectados[3])) return BORDE_NINGUNO;

  if (detectados[1] && detectados[3] && !detectados[0] && !detectados[2]) return BORDE_EMPUJE_IZQUIERDA;
  if (detectados[0] && detectados[2] && !detectados[1] && !detectados[3]) return BORDE_EMPUJE_DERECHA;

  if (!detectados[0] && !detectados[1] && (detectados[2] || detectados[3])) return BORDE_ATRAS;

  if (detectados[0] && detectados[1]) return BORDE_FRENTE;
  if (detectados[0] && detectados[2]) return BORDE_IZQUIERDA;
  if (detectados[0] && !detectados[2]) return BORDE_FRENTE_IZQ;
  if (detectados[1] || detectados[3]) return BORDE_DERECHA;
  if (detectados[2]) return BORDE_IZQUIERDA;

  return BORDE_NINGUNO;
}

bool bordeDespejado() {
  return leer_borde_mejorado() == BORDE_NINGUNO;
}

bool bordeDetectado() {
  return leer_borde_mejorado() != BORDE_NINGUNO;
}

bool moverPorTiempo(unsigned long duracionMs, bool (*condicionSalida)() = nullptr) {
  unsigned long inicio = millis();
  while (millis() - inicio < duracionMs) {
    if (boton_presionado()) return true;
    if (condicionSalida != nullptr && condicionSalida()) break;
  }
  return false;
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

    if (direccionGiroBusqueda == 1) girar_derecha(); else girar_izquierda();
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

void senalar_ronda(int ronda) {
  uint8_t r, g, b;
  switch (ronda) {
    case 1: r = 255; g = 100; b = 0; break;
    case 2: r = 0; g = 255; b = 100; break;
    case 3: r = 0; g = 100; b = 255; break;
    default: r = 0; g = 0; b = 0; break;
  }

  for (int i = 0; i < ronda; i++) {
    pixel.setPixelColor(0, pixel.Color(r, g, b));
    pixel.show();
    delay(300);
    pixel.setPixelColor(0, pixel.Color(0, 0, 0));
    pixel.show();
    delay(300);
  }
}

void inicio_ronda(int ronda) {
  unsigned long inicio;

  if (ronda == 1) {
    avanzar();
    inicio = millis();
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

void setup() {
  Serial.begin(115200);

  pinMode(SEN1, INPUT);
  pinMode(SEN2, INPUT);
  pinMode(SEN3, INPUT);
  pinMode(SEN4, INPUT);

  pinMode(TRIG_PIN, OUTPUT);
  pinMode(ECHO_PIN, INPUT);
  digitalWrite(TRIG_PIN, LOW);

  pinMode(BOOT_PIN, INPUT_PULLUP);

  pixel.begin();
  pixel.setPixelColor(0, pixel.Color(0, 0, 0));
  pixel.show();

  Wire.begin();
  Wire.setTimeOut(50);
  if (!imu.begin_I2C(0x6B)) {
    Serial.println("IMU no encontrado");
    imuDisponible = false;
  } else {
    imuDisponible = true;
    Serial.println("IMU listo, calibrando drift (no muevas el robot)...");
    calibrarDriftGyro();
    calibrarOffsetAccel();
    Serial.println("Calibracion de drift lista.");
  }

  randomSeed(micros());

  ledcSetup(CH_M1_A, PWM_FREQ, PWM_RES);
  ledcAttachPin(M1_A, CH_M1_A);
  ledcSetup(CH_M1_B, PWM_FREQ, PWM_RES);
  ledcAttachPin(M1_B, CH_M1_B);
  ledcSetup(CH_M2_A, PWM_FREQ, PWM_RES);
  ledcAttachPin(M2_A, CH_M2_A);
  ledcSetup(CH_M2_B, PWM_FREQ, PWM_RES);
  ledcAttachPin(M2_B, CH_M2_B);

  frenar();
  delay(1000);
}

enum EstadoJuego { ESPERANDO_INICIO, EN_COMBATE, PARTIDA_TERMINADA };

EstadoJuego estado = ESPERANDO_INICIO;
int ronda = 1;
bool blinkPendiente = true;

int escapesSeguidos = 0;
unsigned long tiempoUltimoEscape = 0;
const unsigned long VENTANA_LOOP_MS = 3000;
const int LIMITE_ESCAPES_LOOP = 3;

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

void loop() {
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
      rivalPerdidoCount = 0;
      direccionGiroBusqueda = 1;
      tiempoInicioBorde = -1;
      escapesSeguidos = 0;
      inicioPosibleLevantamiento = 0;
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

  static unsigned long tiempoUltimaLecturaIMU = 0;
  if (imuDisponible && (millis() - tiempoUltimaLecturaIMU >= 20)) {
    tiempoUltimaLecturaIMU = millis();

    if (detectar_levantamiento_sostenido()) {
      if (escapar_levantamiento()) {
        terminar_ronda_actual();
      }
      return;
    }

    Impacto impacto = detectar_impacto();
    if (impacto != IMPACTO_NINGUNO && impacto != IMPACTO_FRENTE) {
      Serial.print("IMPACTO: ");
      if (impacto == IMPACTO_LATERAL_IZQUIERDA) Serial.println("LATERAL_IZQUIERDA");
      else if (impacto == IMPACTO_LATERAL_DERECHA) Serial.println("LATERAL_DERECHA");
      else Serial.println("ATRAS");

      if (reaccionar_impacto(impacto)) {
        terminar_ronda_actual();
      }
      return;
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
      direccionGiroBusqueda = -direccionGiroBusqueda;
      escapesSeguidos = 0;
      tiempoInicioBorde = -1;
      return;
    }

    Serial.print("ESCAPANDO: ");
    Serial.println(NOMBRES_BORDE[borde]);
    if (maniobra_escape(borde)) {
      terminar_ronda_actual();
    }
    return;
  }

  tiempoInicioBorde = -1;

  if (buscar_y_atacar()) {
    terminar_ronda_actual();
  }
}
