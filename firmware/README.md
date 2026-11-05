# El firmware de OpenIPC para la SC10W

**Todo lo de esta carpeta es de [OpenIPC](https://openipc.org)**
([github.com/OpenIPC/firmware](https://github.com/OpenIPC/firmware)). No lo
compilamos ni lo modificamos. Es una copia de su compilación para el
Hi3518EV200, la que se grabó en la cámara del tutorial y anduvo. Está acá
para que el tutorial se pueda seguir igual cuando OpenIPC publique otra
release, y para que se sepa exactamente qué se probó.

Si querés lo más nuevo, bajalo de OpenIPC y armá la imagen con
`armar_imagen.py` (el [Paso 7](../README.md#paso-7-bajar-openipc-y-armar-la-imagen)
del tutorial).

## Los archivos

| Archivo | Qué es | De dónde sale |
|---|---|---|
| `openipc-sc10w-16mb.bin` | **La imagen entera** de 16 MB, lista para copiar a la microSD (como `openipc.bin`) y grabar con `instalar.py` | Armada con `armar_imagen.py` y las tres piezas de abajo |
| `u-boot-hi3518ev200-universal.bin` | El U-Boot de OpenIPC para el Hi3518EV200 | `u-boot-hi3518ev200-universal.bin` de la release |
| `uImage.hi3518ev200` | El kernel Linux 4.9.37 | Adentro de `openipc.hi3518ev200-nor-ultimate.tgz` |
| `rootfs.squashfs.hi3518ev200` | El sistema (busybox, Majestic, los módulos de video y del WiFi MT7601U) | Adentro de `openipc.hi3518ev200-nor-ultimate.tgz` |

- **Release:** `latest` de
  [github.com/OpenIPC/firmware/releases](https://github.com/OpenIPC/firmware/releases/tag/latest),
  tal como estaba el **4 de noviembre de 2026**. Variante **ultimate**, para
  flash NOR de 16 MB.
- **Las piezas, sin tocar:** sus MD5 (`MD5SUMS`) son los mismos que los
  `.md5sum` que publica OpenIPC.
- **La imagen:** CRC32 `05f1243a`, SHA-256 en `SHA256SUMS`.

Para verificar lo que bajaste:

```bash
shasum -a 256 -c SHA256SUMS          # macOS
sha256sum -c SHA256SUMS              # Linux
certutil -hashfile openipc-sc10w-16mb.bin SHA256    # Windows
```

## La imagen por dentro

| Desde | Tamaño | Partición | Qué va |
|---|---|---|---|
| 0x000000 | 256K | boot | `u-boot-hi3518ev200-universal.bin` (133603 bytes) |
| 0x040000 | 64K | env | vacío (0xFF): OpenIPC escribe su configuración |
| 0x050000 | 3072K | kernel | `uImage.hi3518ev200` (1841037 bytes) |
| 0x350000 | 10240K | rootfs | `rootfs.squashfs.hi3518ev200` (7098368 bytes) |
| 0xD50000 | el resto | rootfs_data | vacío (0xFF): OpenIPC lo formatea al primer arranque |

Es el layout de 16 MB de OpenIPC (`mtdpartsnor16m`). El U-Boot arranca con
el de 8 MB hasta que se corre `run setnor16m`, una sola vez: `instalar.py
--openipc` lo hace solo.

**Solo para la Orvibo SC10W** (Hi3518EV200 con flash de 16 MB). En otra
cámara con el mismo procesador puede andar, pero no está probado: el
sensor, el WiFi y la flash cambian de modelo a modelo.

## Licencias

- **El sistema de OpenIPC** (sus scripts, su configuración, su forma de
  armar el firmware): MIT.
- **Linux y U-Boot:** GPL-2.0. Su código fuente, con los cambios de OpenIPC,
  lo publica OpenIPC: la receta de todo en
  [github.com/OpenIPC/firmware](https://github.com/OpenIPC/firmware), el
  kernel en [github.com/OpenIPC/linux](https://github.com/OpenIPC/linux) y
  el U-Boot en sus repositorios `u-boot-*` (el Hi3518EV200 es de la familia
  del Hi3516CV200:
  [github.com/OpenIPC/u-boot-hi3516cv200](https://github.com/OpenIPC/u-boot-hi3516cv200)).
  Nosotros no lo cambiamos: el código de estos binarios es el de ellos.
- **Busybox y el resto de los paquetes** del rootfs: cada uno con la suya
  (GPL, LGPL, BSD...), compilados por Buildroot.
- **Majestic** (`/usr/bin/majestic`, el programa que comprime y sirve el
  video): software cerrado de OpenIPC, distribuido solo en binario bajo la
  [Prosperity Public License 3.0.0](https://prosperitylicense.com/versions/3.0.0):
  libre para uso **no comercial**. Para uso comercial hay que hablar con
  OpenIPC ([openipc.org/business](https://openipc.org/business)).
- **Los drivers y bibliotecas de video de HiSilicon** que trae el rootfs: de
  HiSilicon, como los publica OpenIPC.

Más en [`../CREDITOS.md`](../CREDITOS.md).
