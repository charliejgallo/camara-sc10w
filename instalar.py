#!/usr/bin/env python3
"""
instalar.py - graba una imagen de 16 MB en la flash de la camara desde su
propia microSD, por la consola de U-Boot, verificando cada paso.

Sirve para las dos cosas:

    # OpenIPC (la imagen de armar_imagen.py, copiada a la microSD como openipc.bin)
    python3 instalar.py --puerto /dev/cu.usbserial-110 --imagen openipc.bin --openipc

    # volver a fabrica (el volcado de volcar.py, copiado a la microSD como fabrica.bin)
    python3 instalar.py --puerto /dev/cu.usbserial-110 --imagen fabrica.bin

--imagen es el MISMO archivo que esta en la microSD (con el mismo nombre). El
script calcula su CRC32 para saber que tiene que leer la camara.

Lo que hace:
1. Frena el arranque: prender la camara mientras manda teclas.
2. Mira la microSD (mmcinfo, fatls) y que el archivo este, con su tamano.
3. Lo carga a la RAM (fatload a 0x82000000) y compara el crc32 de la camara
   con el de la imagen. Si no coincide, para: no se toco nada.
4. Pide que escribas GRABAR. Recien ahi borra la flash (sf erase) y graba
   (sf write).
5. Verifica:
   - pone la RAM en ceros;
   - lee la flash de vuelta (sf read);
   - otra vez el crc32.
   Si no coincide, repite el borrado y la grabacion (tres veces como mucho)
   sin reiniciar: mientras U-Boot siga en el prompt, la camara se puede
   salvar.
6. reset. Con --openipc, frena tambien el U-Boot nuevo de OpenIPC y corre
   "run setnor16m" (fija el layout de 16 MB, lo guarda y reinicia), y espera
   el login de OpenIPC.
"""
import argparse
import os
import sys
import time
import zlib

from sc10w import Consola

RAM = 0x82000000


def paso(t):
    print(f"\n== {t}")


def main():
    p = argparse.ArgumentParser(description="Graba una imagen desde la microSD de la camara, verificando todo.")
    p.add_argument("--puerto", required=True)
    p.add_argument("--imagen", required=True, help="el archivo, igual al que esta en la microSD")
    p.add_argument("--nombre-en-sd", help="si en la microSD tiene otro nombre")
    p.add_argument("--openipc", action="store_true", help="despues, run setnor16m en el U-Boot de OpenIPC")
    p.add_argument("--ya-frenada", action="store_true")
    p.add_argument("--si", action="store_true", help="no preguntar antes de grabar (cuidado)")
    a = p.parse_args()

    img = open(a.imagen, "rb").read()
    n = len(img)
    if n % 0x10000 or n > 16 << 20:
        sys.exit(f"La imagen tiene {n} bytes: tiene que ser multiplo de 64 KB y de 16 MB como mucho")
    quiere = zlib.crc32(img)
    nombre = a.nombre_en_sd or os.path.basename(a.imagen)
    print(f"{nombre}: {n} bytes, CRC32 {quiere:08x}")

    registro = open(f"instalar-{time.strftime('%Y%m%d-%H%M%S')}-consola.txt", "wb")
    c = Consola(a.puerto, registro=registro)
    try:
        paso("1. Frenar el arranque")
        if a.ya_frenada:
            if not c.esperar_prompt():
                sys.exit("No veo el prompt: sacale --ya-frenada y prende la camara")
        else:
            c.frenar()
        if not any("U-Boot" in l for l in c.comando("version")):
            sys.exit("Eso no es U-Boot (no contesto a version): no sigo")
        print(f"Frenada en \"{c.prompt}\"")

        paso("2. La microSD")
        for l in c.comando("mmcinfo", espera=10):
            print("  " + l)
        lista = c.comando(f"fatls mmc 0", espera=10)
        for l in lista:
            print("  " + l)
        if not any(l.split()[-1:] == [nombre] and l.split()[0] == str(n) for l in lista if l.split()):
            sys.exit(f"No veo {nombre} de {n} bytes en la microSD (FAT32, una particion, en la raiz)")

        paso("3. A la RAM, y el CRC32")
        c.comando(f"mw.b 0x{RAM:x} 0xff 0x{n:x}")
        for l in c.comando(f"fatload mmc 0 0x{RAM:x} {nombre}", espera=120):
            print("  " + l)
        tiene = c.crc32(RAM, n)
        print(f"  la camara dice {tiene:08x}, la imagen es {quiere:08x}")
        if tiene != quiere:
            sys.exit("No coinciden: la imagen no llego bien a la RAM. No se toco la flash.")

        paso("4. Grabar")
        print("Esto BORRA la flash de la camara y graba la imagen.")
        if not a.si and input("Escribi GRABAR para seguir: ").strip() != "GRABAR":
            sys.exit("Cancelado: no se toco la flash.")
        for l in c.comando("sf probe 0", espera=10):
            print("  " + l)
        bien = False
        for intento in range(1, 4):
            if intento > 1:
                print(f"  intento {intento}: la imagen otra vez a la RAM")
                c.comando(f"fatload mmc 0 0x{RAM:x} {nombre}", espera=120)
                if c.crc32(RAM, n) != quiere:
                    continue
            t = time.time()
            c.comando(f"sf erase 0x0 0x{n:x}", espera=180)
            print(f"  borrada en {time.time() - t:.0f} s")
            t = time.time()
            c.comando(f"sf write 0x{RAM:x} 0x0 0x{n:x}", espera=180)
            print(f"  grabada en {time.time() - t:.0f} s")

            paso("5. Verificar")
            c.comando(f"mw.b 0x{RAM:x} 0x00 0x{n:x}")
            c.comando(f"sf read 0x{RAM:x} 0x0 0x{n:x}", espera=120)
            tiene = c.crc32(RAM, n)
            print(f"  la flash dice {tiene:08x}, la imagen es {quiere:08x}")
            if tiene == quiere:
                bien = True
                break
            print("  NO coincide: NO reiniciar la camara. Se repite.")
        if not bien:
            sys.exit("La flash no quedo bien despues de 3 intentos. NO desenchufes la camara: "
                     "U-Boot sigue en la RAM y se puede volver a intentar (instalar.py --ya-frenada).")

        paso("6. Reiniciar")
        c.ser.write(b"reset\r")
        if not a.openipc:
            print("Listo. La camara arranca con la imagen grabada.")
            return 0
        c.prompt = None
        c.frenar(segundos=120, aviso="Frenando el U-Boot de OpenIPC, que arranca solo (no toques nada)...")
        print(f"Frenado en \"{c.prompt}\": run setnor16m (layout de 16 MB, lo guarda y reinicia)")
        c.ser.write(b"run setnor16m\r")
        vio = []
        fin = time.time() + 240
        while time.time() < fin and not any("login" in l for l in vio[-3:] + [c.linea]):
            c._leer(1, vio.append)
        if any("login" in l for l in vio[-3:] + [c.linea]):
            print("Arranco OpenIPC: entra con usuario root, acepta el aviso con \"I Agree\" y elegi tu clave (Paso 10).")
            return 0
        print("No vi el login de OpenIPC en 4 minutos: mira la consola (" + registro.name + ").")
        return 1
    except RuntimeError as e:
        print(f"\n{e}")
        return 1
    finally:
        c.cerrar()
        registro.close()


if __name__ == "__main__":
    sys.exit(main())
