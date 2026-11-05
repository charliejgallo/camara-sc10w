#!/usr/bin/env python3
"""
volcar.py - copia la flash entera de la camara a un archivo, por su consola,
antes de tocar nada. Solo lee: no manda ningun comando que escriba en la
flash.

    python3 volcar.py --puerto /dev/cu.usbserial-110            (macOS)
    python3 volcar.py --puerto /dev/ttyUSB0                     (Linux)
    python3 volcar.py --puerto COM5                             (Windows)

Opciones:
    --salida volcado.bin     el archivo (por defecto sc10w-<fecha>.bin)
    --desde 0x0 --largo 16M  un pedazo de la flash
    --ram 0x82000000         la RAM de la camara donde se copia cada pedazo
    --comparar otro.bin      al terminar, compara byte por byte con otro volcado
    --ya-frenada             la camara ya esta en el prompt de U-Boot

Como funciona:
1. Frena el arranque (hay que prender la camara mientras manda teclas).
2. Le pregunta a U-Boot por la flash ("sf probe 0").
3. De a 64 KB:
   - "sf read" a la RAM;
   - "crc32" de la camara;
   - "md.l", que imprime esa RAM en hexadecimal y aca se vuelve a bytes;
   - compara el CRC32 de lo recibido con el de la camara.
   Si no coincide, repite solo las partes de 4 KB que vinieron mal.

A 115200 baudios, md.l saca unos 2,6 KB por segundo: 16 MB tardan ~100
minutos. Al final deja la camara frenada en el prompt; desenchufarla y
enchufarla la arranca normal.
"""
import argparse
import datetime
import hashlib
import os
import sys
import time
import zlib

from sc10w import Consola, tamano

PEDAZO = 64 * 1024


def main():
    p = argparse.ArgumentParser(description="Copia la flash de la camara por la consola de U-Boot (solo lee).")
    p.add_argument("--puerto", required=True)
    p.add_argument("--salida")
    p.add_argument("--desde", default="0")
    p.add_argument("--largo", default="0", help="0: hasta el final de la flash")
    p.add_argument("--ram", default="0x82000000")
    p.add_argument("--comparar")
    p.add_argument("--ya-frenada", action="store_true")
    a = p.parse_args()

    fecha = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
    salida = a.salida or f"sc10w-{fecha}.bin"
    registro = open(os.path.splitext(salida)[0] + "-consola.txt", "wb")
    c = Consola(a.puerto, registro=registro)
    ram = int(a.ram, 0)
    try:
        if a.ya_frenada:
            if not c.esperar_prompt():
                sys.exit("No veo el prompt: sacale --ya-frenada y prende la camara")
        else:
            c.frenar()
        print(f"Frenada en \"{c.prompt}\"")
        version = [l for l in c.comando("version") if "U-Boot" in l]
        if not version:
            sys.exit("Eso no es U-Boot (no contesto a version): no sigo")
        print(version[0].strip())
        c.comando("printenv")
        flash = 0
        for l in c.comando("sf probe 0"):
            print(l)
            if "KiB" in l:
                flash = int(l.split()[0]) * 1024
        desde, largo = tamano(a.desde), tamano(a.largo)
        if not largo:
            if not flash:
                sys.exit("No se sabe el tamano de la flash: indicalo con --largo")
            largo = flash - desde
        print(f"Leyendo {largo // 1024} KB desde 0x{desde:x}, de a 64 KB, por 0x{ram:08x}")

        datos = bytearray()
        t0 = time.time()
        for o in range(0, largo, PEDAZO):
            n = min(PEDAZO, largo - o)
            c.comando(f"sf read 0x{ram:x} 0x{desde + o:x} 0x{n:x}")
            datos += c.leer_verificado(ram, n)
            hecho = o + n
            t = time.time() - t0
            falta = t / hecho * (largo - hecho)
            print(f"\r  {hecho // 1024:6d} / {largo // 1024} KB  {hecho * 100 // largo:3d} %  "
                  f"{hecho / 1024 / max(t, 0.1):5.1f} KB/s  faltan {falta / 60:5.1f} min", end="", flush=True)
        print()
        open(salida + ".part", "wb").write(datos)
        os.replace(salida + ".part", salida)
        sha = hashlib.sha256(datos).hexdigest()
        print(f"Guardado {salida}: {len(datos)} bytes, CRC32 {zlib.crc32(datos):08x}, SHA-256 {sha}")
        print(f"La consola entera quedo en {registro.name}")
        if a.comparar:
            otro = open(a.comparar, "rb").read()
            if otro == datos:
                print(f"IGUAL byte por byte a {a.comparar}")
            else:
                dif = sum(x != y for x, y in zip(otro, datos)) + abs(len(otro) - len(datos))
                print(f"DISTINTO de {a.comparar}: {dif} bytes")
                return 1
        print("La camara queda frenada en U-Boot. Para que arranque: desenchufala y enchufala.")
        return 0
    except RuntimeError as e:
        print(f"\n{e}")
        return 1
    finally:
        c.cerrar()
        registro.close()


if __name__ == "__main__":
    sys.exit(main())
