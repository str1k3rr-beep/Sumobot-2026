#pragma once

enum Impacto { IMPACTO_NINGUNO, IMPACTO_LATERAL_IZQUIERDA, IMPACTO_LATERAL_DERECHA, IMPACTO_ATRAS, IMPACTO_FRENTE };

extern bool imuDisponible;

void imu_inicializar();
void leerAceleracion(float &x, float &y, float &z);
float leerGyroZ_dps();
Impacto detectar_impacto();
bool esta_nivelado();
bool detectar_levantamiento_sostenido();
void resetear_deteccion_levantamiento();
void marcar_impacto_frente_reciente();
bool debe_muestrear_rapido();
unsigned int obtener_fallos_i2c();
