#!/usr/bin/env python3
"""
armar_imagen.py - arma la imagen de 16 MB de OpenIPC para la flash de la
camara, con las tres piezas que publica OpenIPC.

    python3 armar_imagen.py \\
        --uboot u-boot-hi3518ev200-universal.bin \\
        --kernel uImage.hi3518ev200 \\
        --rootfs rootfs.squashfs.hi3518ev200 \\
        --salida openipc.bin

Usa el layout de 16 MB de OpenIPC ("mtdpartsnor16m"), con todo lo que no se
usa en 0xFF (lo que tiene una flash borrada):

    0x000000  256K   boot         U-Boot de OpenIPC
    0x040000   64K   env          vacio: OpenIPC escribe el suyo al arrancar
    0x050000  3072K  kernel       uImage
    0x350000 10240K  rootfs       squashfs
    0xD50000  resto  rootfs_data  vacio: OpenIPC lo formatea al arrancar

Al final dice el CRC32 de la imagen. Es el que tiene que dar el "crc32" de
U-Boot cuando la cargue de la microSD; instalar.py lo calcula solo.
"""
import argparse
import hashlib
import sys
import zlib

FLASH = 16 << 20
PARTES = [  # nombre, desde, tamano maximo
    ("uboot", 0x000000, 256 << 10),
    ("kernel", 0x050000, 3072 << 10),
    ("rootfs", 0x350000, 10240 << 10),
]


def main():
    p = argparse.ArgumentParser(description="Arma la imagen de 16 MB de OpenIPC para la SC10W.")
    p.add_argument("--uboot", required=True)
    p.add_argument("--kernel", required=True)
    p.add_argument("--rootfs", required=True)
    p.add_argument("--salida", default="openipc.bin")
    a = p.parse_args()

    img = bytearray(b"\xff" * FLASH)
    for nombre, desde, maximo in PARTES:
        datos = open(getattr(a, nombre), "rb").read()
        if len(datos) > maximo:
            sys.exit(f"{nombre} tiene {len(datos)} bytes y su particion {maximo}: no entra")
        img[desde:desde + len(datos)] = datos
        print(f"  0x{desde:06x}  {nombre:7s} {len(datos):8d} bytes de {maximo}")
    if img[0x050000:0x050004] != b"\x27\x05\x19\x56":
        sys.exit("El kernel no empieza con la marca de un uImage (27 05 19 56): no es el archivo correcto")
    if img[0x350000:0x350004] != b"hsqs":
        sys.exit("El rootfs no empieza con la marca de un squashfs (hsqs): no es el archivo correcto")
    open(a.salida, "wb").write(img)
    print(f"{a.salida}: {len(img)} bytes")
    print(f"  CRC32   {zlib.crc32(img):08x}   (lo que tiene que decir el crc32 de U-Boot)")
    print(f"  SHA-256 {hashlib.sha256(img).hexdigest()}")


if __name__ == "__main__":
    main()
