# Créditos

## OpenIPC

**El firmware que se instala en la cámara es de [OpenIPC](https://openipc.org)**,
un proyecto libre que hace firmware abierto para cámaras IP:
[github.com/OpenIPC](https://github.com/OpenIPC). Sin su trabajo esta cámara
seguiría atada a una nube. Si te sirvió, mirá cómo apoyarlos en
[openipc.org](https://openipc.org).

Lo que hay de ellos en este repositorio está en [`firmware/`](firmware/), sin
modificar (la imagen de 16 MB es solo sus tres piezas puestas en su lugar):

| Qué | Licencia | Código fuente |
|---|---|---|
| El sistema de OpenIPC (Buildroot, scripts, configuración) | MIT | [OpenIPC/firmware](https://github.com/OpenIPC/firmware) |
| Linux 4.9.37 | GPL-2.0 | [OpenIPC/linux](https://github.com/OpenIPC/linux) |
| U-Boot | GPL-2.0 | los `u-boot-*` de [github.com/OpenIPC](https://github.com/OpenIPC) |
| Busybox y los demás paquetes del rootfs | los suyos (GPL, LGPL, BSD...) | vía [OpenIPC/firmware](https://github.com/OpenIPC/firmware) |
| Majestic, el streamer de video | [Prosperity Public License 3.0.0](https://prosperitylicense.com/versions/3.0.0): libre para uso no comercial | cerrado, de OpenIPC |
| Drivers y bibliotecas de video de HiSilicon | de HiSilicon | cerrados |

**Majestic** se usa y se redistribuye acá en las condiciones de su licencia:
para uso no comercial. Para uso comercial, ver
[openipc.org/business](https://openipc.org/business).

## Este repositorio

- **El tutorial, los scripts (`sc10w.py`, `volcar.py`, `armar_imagen.py`,
  `instalar.py`, `fake_uboot.py`) y las fotos:** Charlie Gallo, 2026,
  licencia MIT ([`LICENSE`](LICENSE)).
- **Hecho con [P4OS](https://github.com/charliejgallo/P4OS)**, que se usó
  como herramienta de campo para abrir la consola, copiar la flash e
  instalar OpenIPC la primera vez. `fake_uboot.py` viene de sus
  herramientas de prueba.
- **pyserial** ([github.com/pyserial/pyserial](https://github.com/pyserial/pyserial),
  BSD-3-Clause), la única librería que usan los scripts. No está incluida:
  se instala con pip.

## Marcas

Orvibo, HiSilicon, Macronix, OmniVision y MediaTek son marcas de sus
dueños. Este proyecto no tiene relación con ninguno de ellos. El firmware de
fábrica de la cámara **no** está en este repositorio: cada uno copia el suyo
con `volcar.py`.
