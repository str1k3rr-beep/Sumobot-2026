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

const bool INVERTIR_M1 = false;
const bool INVERTIR_M2 = false;

int umbrales[4] = {300, 300, 300, 300};

bool corriendo = false;
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

void establecerMotor(int pinA, int pinB, float valor) {
  valor = constrain(valor, -1.0, 1.0);
  int duty = (int)(fabs(valor) * 255);

  if (valor > 0) {
    ledcWrite(pinA, duty);
    ledcWrite(pinB, 0);
  } else if (valor < 0) {
    ledcWrite(pinA, 0);
    ledcWrite(pinB, duty);
  } else {
    ledcWrite(pinA, 0);
    ledcWrite(pinB, 0);
  }
}

void arrancar_motores(float m1, float m2) {
  float valorM1 = INVERTIR_M1 ? -m1 : m1;
  float valorM2 = INVERTIR_M2 ? m2 : -m2;
  establecerMotor(M1_A, M1_B, valorM1);
  establecerMotor(M2_A, M2_B, valorM2);
}

void frenar() {
  arrancar_motores(0.0, 0.0);
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

  ledcAttach(M1_A, PWM_FREQ, PWM_RES);
  ledcAttach(M1_B, PWM_FREQ, PWM_RES);
  ledcAttach(M2_A, PWM_FREQ, PWM_RES);
  ledcAttach(M2_B, PWM_FREQ, PWM_RES);

  frenar();
  delay(1000);
}

unsigned long tiempoUltimoPrint = 0;
const unsigned long INTERVALO_PRINT = 100;

void loop() {
  if (boton_presionado()) {
    corriendo = !corriendo;
    if (corriendo) {
      Serial.println("INICIANDO");
    } else {
      frenar();
      Serial.println("DETENIDO");
    }
  }

  if (!corriendo) {
    return;
  }

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
