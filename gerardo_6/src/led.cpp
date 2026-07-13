#include <Arduino.h>
#include <Adafruit_NeoPixel.h>
#include "config.h"
#include "led.h"

Adafruit_NeoPixel pixel(1, PIN_LED, NEO_GRB + NEO_KHZ800);

void led_inicializar() {
  pixel.begin();
  pixel.setPixelColor(0, pixel.Color(0, 0, 0));
  pixel.show();
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
