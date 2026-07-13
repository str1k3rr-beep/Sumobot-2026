#pragma once

bool girar_grados(int lado, float grados);
bool moverPorTiempo(unsigned long duracionMs, bool (*condicionSalida)() = nullptr);
