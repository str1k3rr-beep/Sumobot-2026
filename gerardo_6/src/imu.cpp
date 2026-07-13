#include <Arduino.h>
#include <Wire.h>
#include <Adafruit_LSM6DS3TRC.h>
#include "config.h"
#include "imu.h"
#include "ultrasonico.h"

Adafruit_LSM6DS3TRC imu;
bool imuDisponible = false;

float offsetGyroZ = 0.0;
float offsetAccelX = 0.0;
float offsetAccelY = 0.0;
float offsetAccelZ = 0.0;

unsigned long inicioPosibleLevantamiento = 0;

float ultimoAccelX = 0.0;
float ultimoAccelY = 0.0;
float ultimoAccelZ = 9.8;
float ultimoGyroZ = 0.0;
unsigned int fallosI2C = 0;

const float MAGNITUD_ACCEL_MIN_PLAUSIBLE = 2.0;
const float MAGNITUD_ACCEL_MAX_PLAUSIBLE = 40.0;
const float GYRO_DPS_MAX_PLAUSIBLE = 2000.0;

void leerAceleracion(float &x, float &y, float &z) {
  sensors_event_t accel, gyro, temp;
  imu.getEvent(&accel, &gyro, &temp);

  float nx = accel.acceleration.x;
  float ny = accel.acceleration.y;
  float nz = accel.acceleration.z;
  float magnitud = sqrt(nx * nx + ny * ny + nz * nz);

  if (magnitud < MAGNITUD_ACCEL_MIN_PLAUSIBLE || magnitud > MAGNITUD_ACCEL_MAX_PLAUSIBLE) {
    fallosI2C++;
  } else {
    ultimoAccelX = nx;
    ultimoAccelY = ny;
    ultimoAccelZ = nz;
  }

  x = ultimoAccelX;
  y = ultimoAccelY;
  z = ultimoAccelZ;
}

float leerGyroZ_dps() {
  sensors_event_t accel, gyro, temp;
  imu.getEvent(&accel, &gyro, &temp);

  float nuevoGyroZ = gyro.gyro.z * 180.0 / PI;

  if (fabs(nuevoGyroZ) > GYRO_DPS_MAX_PLAUSIBLE) {
    fallosI2C++;
  } else {
    ultimoGyroZ = nuevoGyroZ;
  }

  return ultimoGyroZ - offsetGyroZ;
}

unsigned int obtener_fallos_i2c() {
  return fallosI2C;
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

void imu_inicializar() {
  Wire.begin();
  Wire.setTimeOut(50);

  if (!imu.begin_I2C(0x6B)) {
    Serial.println("IMU no encontrado");
    imuDisponible = false;
    return;
  }

  imuDisponible = true;
  Serial.println("IMU listo, calibrando drift (no muevas el robot)...");
  calibrarDriftGyro();
  calibrarOffsetAccel();
  Serial.println("Calibracion de drift lista.");
}

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

void resetear_deteccion_levantamiento() {
  inicioPosibleLevantamiento = 0;
}

unsigned long tiempoMarcaImpactoFrente = 0;
const unsigned long DURACION_PRIORIDAD_LEVANTAMIENTO_MS = 2000;

void marcar_impacto_frente_reciente() {
  tiempoMarcaImpactoFrente = millis();
}

bool debe_muestrear_rapido() {
  return (millis() - tiempoMarcaImpactoFrente) < DURACION_PRIORIDAD_LEVANTAMIENTO_MS;
}
