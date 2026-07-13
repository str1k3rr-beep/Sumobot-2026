#include <Arduino.h>

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
  arrancar_motores(-1.0, 1.0);
}

void girar_derecha() {
  arrancar_motores(1.0, -1.0);
}

long medir_distancia_cm() {
  digitalWrite(TRIG_PIN, LOW);
  delayMicroseconds(2);
  digitalWrite(TRIG_PIN, HIGH);
  delayMicroseconds(10);
  digitalWrite(TRIG_PIN, LOW);

  long duracion = pulseIn(ECHO_PIN, HIGH, 30000);
  if (duracion == 0) return 999;

  return duracion * 0.0343 / 2;
}

bool rival_detectado() {
  return medir_distancia_cm() < 40;
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
  BORDE_IZQUIERDA,
  BORDE_DERECHA,
  BORDE_FRENTE_IZQ,
  BORDE_EMPUJE_IZQUIERDA,
  BORDE_EMPUJE_DERECHA
};

const char* NOMBRES_BORDE[] = {"NINGUNO", "FRENTE", "IZQUIERDA", "DERECHA", "FRENTE_IZQ", "EMPUJE_IZQUIERDA", "EMPUJE_DERECHA"};

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

  if (detectados[0] && detectados[1]) return BORDE_FRENTE;
  if (detectados[0] && detectados[2]) return BORDE_IZQUIERDA;
  if (detectados[0] && !detectados[2]) return BORDE_FRENTE_IZQ;
  if (detectados[1] || detectados[3]) return BORDE_DERECHA;
  if (detectados[2]) return BORDE_IZQUIERDA;

  return BORDE_NINGUNO;
}

bool maniobra_escape(Borde direccion) {
  unsigned long inicio;

  if (direccion == BORDE_EMPUJE_IZQUIERDA) {
    arrancar_motores(-1.0, 1.0);
    inicio = millis();
    while (millis() - inicio < 350) {
      if (boton_presionado()) return true;
    }
    arrancar_motores(1.0, 1.0);
    inicio = millis();
    while (millis() - inicio < 350) {
      if (boton_presionado()) return true;
    }
    arrancar_motores(-1.0, 1.0);
    inicio = millis();
    while (millis() - inicio < 300) {
      if (boton_presionado()) return true;
    }
    tiempoInicioBorde = -1;
    frenar();
    return false;
  }

  if (direccion == BORDE_EMPUJE_DERECHA) {
    arrancar_motores(-1.0, 1.0);
    inicio = millis();
    while (millis() - inicio < 350) {
      if (boton_presionado()) return true;
    }
    arrancar_motores(-1.0, -1.0);
    inicio = millis();
    while (millis() - inicio < 350) {
      if (boton_presionado()) return true;
    }
    arrancar_motores(-1.0, 1.0);
    inicio = millis();
    while (millis() - inicio < 300) {
      if (boton_presionado()) return true;
    }
    tiempoInicioBorde = -1;
    frenar();
    return false;
  }

  unsigned long ahora = millis();
  if (tiempoInicioBorde == -1) {
    tiempoInicioBorde = ahora;
  }
  unsigned long tiempoEnBorde = ahora - tiempoInicioBorde;

  if (tiempoEnBorde > 200 && !rival_detectado()) {

    if (direccion == BORDE_IZQUIERDA) {
      arrancar_motores(-1.0, -1.0);
      inicio = millis();
      while (millis() - inicio < 300) {
        if (boton_presionado()) return true;
        if (leer_borde_mejorado() == BORDE_NINGUNO) break;
      }
      arrancar_motores(-1.0, 1.0);
      inicio = millis();
      while (millis() - inicio < 250) {
        if (boton_presionado()) return true;
        if (leer_borde_mejorado() != BORDE_NINGUNO) break;
      }

    } else if (direccion == BORDE_DERECHA) {
      arrancar_motores(1.0, 1.0);
      inicio = millis();
      while (millis() - inicio < 300) {
        if (boton_presionado()) return true;
        if (leer_borde_mejorado() == BORDE_NINGUNO) break;
      }
      arrancar_motores(-1.0, 1.0);
      inicio = millis();
      while (millis() - inicio < 250) {
        if (boton_presionado()) return true;
        if (leer_borde_mejorado() != BORDE_NINGUNO) break;
      }

    } else {
      int lado = (random(2) == 0) ? 1 : -1;
      arrancar_motores(-1.0 * lado, -1.0 * lado);
      inicio = millis();
      while (millis() - inicio < 350) {
        if (boton_presionado()) return true;
        if (leer_borde_mejorado() == BORDE_NINGUNO) break;
      }
      arrancar_motores(-1.0, 1.0);
      inicio = millis();
      while (millis() - inicio < 200) {
        if (boton_presionado()) return true;
        if (leer_borde_mejorado() != BORDE_NINGUNO) break;
      }
    }

    tiempoInicioBorde = -1;
    frenar();
    return false;
  }

  arrancar_motores(1.0, -1.0);
  inicio = millis();
  while (millis() - inicio < 150) {
    if (boton_presionado()) return true;
    if (leer_borde_mejorado() != BORDE_NINGUNO) break;
  }
  frenar();

  if (direccion == BORDE_FRENTE || direccion == BORDE_FRENTE_IZQ) {
    arrancar_motores(-1.0, -1.0);
    inicio = millis();
    while (millis() - inicio < 450) {
      if (boton_presionado()) return true;
      if (leer_borde_mejorado() != BORDE_NINGUNO) break;
    }
  } else if (direccion == BORDE_IZQUIERDA) {
    arrancar_motores(1.0, 1.0);
    inicio = millis();
    while (millis() - inicio < 300) {
      if (boton_presionado()) return true;
      if (leer_borde_mejorado() != BORDE_NINGUNO) break;
    }
  } else if (direccion == BORDE_DERECHA) {
    arrancar_motores(-1.0, -1.0);
    inicio = millis();
    while (millis() - inicio < 300) {
      if (boton_presionado()) return true;
      if (leer_borde_mejorado() != BORDE_NINGUNO) break;
    }
  }

  frenar();
  return false;
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

bool activo = false;
unsigned long tiempoUltimoPrint = 0;
const unsigned long INTERVALO_PRINT = 100;

void loop() {
  if (boton_presionado()) {
    activo = !activo;
    if (activo) {
      Serial.println("ACTIVO");
    } else {
      frenar();
      tiempoInicioBorde = -1;
      Serial.println("DETENIDO");
    }
  }

  if (!activo) {
    return;
  }

  Borde borde = leer_borde_mejorado();

  if (borde != BORDE_NINGUNO) {
    Serial.print("ESCAPANDO: ");
    Serial.println(NOMBRES_BORDE[borde]);
    if (maniobra_escape(borde)) {
      activo = false;
      frenar();
      Serial.println("DETENIDO (boton durante escape)");
    }
    return;
  }

  tiempoInicioBorde = -1;

  if (millis() - tiempoUltimoPrint < INTERVALO_PRINT) {
    return;
  }
  tiempoUltimoPrint = millis();

  int ir[4];
  leer_sensores(ir);
  long distancia = medir_distancia_cm();

  Serial.print(ir[0]); Serial.print("  ");
  Serial.print(ir[1]); Serial.print("  ");
  Serial.print(ir[2]); Serial.print("  ");
  Serial.print(ir[3]); Serial.print("  dist=");
  Serial.println(distancia);
}
