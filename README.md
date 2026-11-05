# OpenIPC en la cámara Orvibo SC10W, paso a paso

Cómo sacarle el firmware de nube china a una cámara WiFi barata, una
**Orvibo SC10W** (la que viene en algunos kits de alarma genéricos, FCC ID
`2ACLPSC10W`), y ponerle **[OpenIPC](https://openipc.org)**: video por RTSP en
tu red, una página web propia, grabación en la microSD y nada de nubes.

Hace falta un **adaptador USB-serie común** (de los de 2 o 3 dólares), un
soldador y una computadora con **Python**. Los cuatro scripts de este repositorio
hacen el trabajo delicado y verifican cada paso, así que no hay que tipear
comandos de U-Boot a mano.

![OpenIPC andando en la SC10W: su página web con el video en vivo (H264, 1280×720, 25 fps)](img/openipc-video-en-vivo.jpg)

> **Probado** en una SC10W real el 4 y 5 de noviembre de 2026, de punta a
> punta: copia de la flash dos veces (iguales), instalación de OpenIPC y
> arranque. Los scripts, además, se probaron enteros (copia, instalación y
> vuelta a fábrica) contra `fake_uboot.py`, un U-Boot de mentira que imita
> al de esta cámara.

### Qué hay en este repositorio

| Qué | Dónde |
|---|---|
| Este tutorial | `README.md` |
| Los scripts | `sc10w.py`, `volcar.py`, `armar_imagen.py`, `instalar.py`, `fake_uboot.py` |
| El firmware de OpenIPC para esta cámara, listo para grabar, y sus tres piezas | [`firmware/`](firmware/) |
| Las fotos | `img/` |
| De quién es cada cosa, y las licencias | [`CREDITOS.md`](CREDITOS.md) |

**El firmware es de [OpenIPC](https://openipc.org)**, no nuestro: acá hay
una copia de su compilación para este procesador, para que el tutorial se
pueda seguir aunque cambie su release. Los detalles y las licencias, en
[`firmware/README.md`](firmware/README.md) y [`CREDITOS.md`](CREDITOS.md).

---

## Índice

- [Antes de empezar](#antes-de-empezar)
  - [Lo que vas a lograr](#lo-que-vas-a-lograr)
  - [Los riesgos, y la red de seguridad](#los-riesgos-y-la-red-de-seguridad)
  - [Qué hay adentro de la cámara](#qué-hay-adentro-de-la-cámara)
  - [Materiales](#materiales)
  - [El software](#el-software)
- [Paso 1: abrir la cámara y encontrar la consola](#paso-1-abrir-la-cámara-y-encontrar-la-consola)
- [Paso 2: soldar y conectar el adaptador](#paso-2-soldar-y-conectar-el-adaptador)
- [Paso 3: encontrar el puerto en tu computadora](#paso-3-encontrar-el-puerto-en-tu-computadora)
- [Paso 4: mirar la consola](#paso-4-mirar-la-consola)
- [Paso 5: frenar el arranque (y por qué cuesta)](#paso-5-frenar-el-arranque-y-por-qué-cuesta)
- [Paso 6: la copia de seguridad de la flash](#paso-6-la-copia-de-seguridad-de-la-flash)
- [Paso 7: bajar OpenIPC y armar la imagen](#paso-7-bajar-openipc-y-armar-la-imagen)
- [Paso 8: preparar la microSD](#paso-8-preparar-la-microsd)
- [Paso 9: instalar OpenIPC](#paso-9-instalar-openipc)
- [Paso 10: el primer arranque y la configuración](#paso-10-el-primer-arranque-y-la-configuración)
- [Por qué tarda tanto en arrancar](#por-qué-tarda-tanto-en-arrancar)
- [Volver al firmware de fábrica](#volver-al-firmware-de-fábrica)
- [Problemas y soluciones](#problemas-y-soluciones)
- [Detalles técnicos](#detalles-técnicos)
- [Probar los scripts sin la cámara](#probar-los-scripts-sin-la-cámara)
- [Cómo se hizo](#cómo-se-hizo)
- [Créditos y licencias](#créditos-y-licencias)

---

## Antes de empezar

### Lo que vas a lograr

| Con el firmware de fábrica | Con OpenIPC |
|---|---|
| Solo anda con la app del fabricante y su nube (Danale) | Video por **RTSP** en tu red, para VLC, Frigate, Home Assistant, cualquier grabador |
| El video sale de tu casa hacia servidores ajenos | No sale nada de tu red si no querés |
| Sin acceso a la configuración | Página web propia, SSH, configuración completa |
| Firmware de 2018, sin actualizaciones | Linux 4.9 y OpenIPC, que se sigue actualizando |

Tiempo total: unas **4 horas**, casi todas esperando. La copia de seguridad
tarda ~100 minutos y conviene hacerla dos veces. La instalación en sí son
unos 5 minutos.

### Los riesgos, y la red de seguridad

- **Abrir la cámara y soldarle cables anula la garantía.**
- **La instalación borra el firmware de fábrica.** Por eso el Paso 6 hace
  primero una copia exacta de la flash entera, y la verifica. Con esa copia
  se puede volver a fábrica cuando quieras
  ([Volver al firmware de fábrica](#volver-al-firmware-de-fábrica)).
- **Si se corta la luz justo mientras graba**, la cámara puede quedar sin
  arrancar. No es el fin: con una pinza SOIC8 y un programador CH341A
  (~5 dólares) se graba la flash directamente, aunque la cámara no
  arranque. Y la ROM del chip HiSilicon acepta un U-Boot por la consola
  serie: eso usa la herramienta `burn` de OpenIPC.
- **El script de instalación no graba nada** hasta que:
  - comprobó que la imagen llegó intacta a la memoria de la cámara (por
    CRC32);
  - y vos escribiste `GRABAR`.

  Después de grabar, vuelve a leer la flash y la compara. Si algo no
  coincide, lo repite **sin reiniciar**: mientras U-Boot siga corriendo, la
  cámara se puede salvar.

### Qué hay adentro de la cámara

| | |
|---|---|
| Procesador | HiSilicon **Hi3518EV200** (impreso "Hi3518 ERBCV200"): un ARM926EJ-S con 64 MB de RAM adentro del chip, y cristal de 24 MHz |
| Flash | **Macronix MX25L128**: SPI NOR de **16 MB**, en un SOP8 (ID `c2 20 18`) |
| Sensor | **OmniVision OV9732**, 1280×720 |
| WiFi | Un módulo USB aparte con un **MediaTek MT7601U** (el firmware de fábrica le carga `mt7601Usta`) |
| Ethernet | No tiene |
| Tarjeta | Ranura microSD |
| Consola | 4 pads rotulados **TXD, RXD, 3.3V, GND**, junto al cristal, a 115200 baudios |
| Firmware de fábrica | U-Boot 2010.06 de HiSilicon (2016), Linux 3.4.35 y la app `241BA_2.0.16` de nube Danale (2018) |

### Materiales

- **La cámara**, con su cable y una **fuente micro-USB buena** (5 V, 1 A o
  más). Con una fuente floja la cámara arranca mal y por la consola sale
  basura: nos pasó, y estuvimos un rato buscando el error en otro lado.
- **Un adaptador USB-serie de 3,3 V:** CH340, CP2102, FT232 o PL2303. Muchos
  tienen un jumper o un interruptor 3,3 V / 5 V: **ponelo en 3,3 V**. Los
  pines de la cámara son de 3,3 V y 5 V los puede dañar.
- **Tres cables** finos (los de wire-wrap o los de un cable de red viejo
  andan bien) y tres cables dupont hembra para el adaptador.
- **Soldador** de punta fina, estaño y, si tenés, flux.
- **Una microSD** de 32 GB o menos, que se pueda formatear en FAT32.
- **Una computadora** con Windows, macOS o Linux.
- **Opcional:** una pinza SOIC8 y un programador CH341A, para el plan B.

### El software

1. **Python 3.8 o más nuevo:**
   - **Windows:** de [python.org](https://www.python.org/downloads/),
     tildando "Add Python to PATH".
   - **macOS:** ya trae `python3`; si no, de python.org o `brew install
     python`.
   - **Linux:** casi seguro ya lo tenés.
2. **pyserial**, la única librería que usan los scripts:

   ```bash
   python3 -m pip install pyserial
   ```

   En Windows, `python` en lugar de `python3`, en este comando y en todos los
   de este tutorial.
3. **Los scripts de este repositorio**, todos juntos en una misma carpeta.
   Lo más fácil es bajar el repositorio entero (en GitHub: Code → Download
   ZIP, o `git clone`), que trae también el firmware:

   | Archivo | Qué hace |
   |---|---|
   | `sc10w.py` | La parte común: habla con U-Boot por el puerto serie. No se ejecuta solo |
   | `volcar.py` | La copia de seguridad de la flash. **Solo lee** |
   | `armar_imagen.py` | Arma la imagen de 16 MB de OpenIPC con sus tres piezas |
   | `instalar.py` | Graba una imagen desde la microSD de la cámara, verificando todo: OpenIPC o el firmware de fábrica |
   | `fake_uboot.py` | Una cámara de mentira para probar todo antes (opcional; macOS y Linux) |

---

## Paso 1: abrir la cámara y encontrar la consola

1. Desenchufá la cámara.
2. Sacá los tornillos de la carcasa: suelen estar debajo de etiquetas o de
   las patas de goma. Separá las dos mitades con cuidado: el parlante y
   el micrófono van con cables a la placa.
3. En la placa principal (la del procesador grande con el logo de
   HiSilicon) buscá **cuatro pads redondos en fila**, junto al cristal
   plateado que dice `24.000`. Están rotulados **TXD, RXD, 3.3V y GND**:

![La placa de la SC10W: el Hi3518EV200, el cristal de 24 MHz y los cuatro pads de la consola (TXD, RXD, 3.3V, GND) a su izquierda](img/placa-pads-consola.jpg)

**La consola serie** es por donde el procesador escribe sus mensajes
mientras arranca, y por donde se le pueden mandar comandos. Va a 115200
baudios, 8 bits, sin paridad y 1 bit de parada (115200 8N1). Funciona a
3,3 V.

## Paso 2: soldar y conectar el adaptador

**Soldar los cables:**

1. Estañá un poco cada pad (con flux, si tenés).
2. Pelá 2 mm de cada cable y estañalos.
3. Soldá **tres** cables: **TXD, RXD y GND**. **El de 3.3V no se usa.**

Fijate con una lupa o con la cámara del celular que ningún pad quede
puenteado con el de al lado.

**Conectar el adaptador, cruzados:** lo que la cámara transmite (TX) va a
lo que el adaptador recibe (RX), y al revés.

| Cámara | Adaptador USB-serie |
|---|---|
| TXD | **RXD** |
| RXD | **TXD** |
| GND | **GND** |
| 3.3V | **nada** |

- **No conectes el 3,3 V del adaptador a la cámara.** La cámara se alimenta
  sola, con su fuente micro-USB. El adaptador no da corriente suficiente, y
  dos fuentes encontradas pueden dañar algo.
- **El GND sí o sí.** Sin masa común, por la consola llega basura.

## Paso 3: encontrar el puerto en tu computadora

Enchufá el adaptador a la computadora (la cámara puede seguir apagada).

- **Windows:** Administrador de dispositivos → "Puertos (COM y LPT)". Va a
  aparecer algo como `USB-SERIAL CH340 (COM5)`; tu puerto es **`COM5`**. Si
  no aparece, instalá el driver de tu chip (CH340: wch-ic.com; CP2102: Silicon
  Labs).
- **macOS:** en una terminal, `ls /dev/cu.*`. Va a ser algo como
  **`/dev/cu.usbserial-110`** o `/dev/cu.wchusbserial110`.
- **Linux:** `ls /dev/ttyUSB*`, normalmente **`/dev/ttyUSB0`**. Si te dice
  "Permission denied", agregate al grupo `dialout` (`sudo usermod -aG
  dialout $USER`) y volvé a entrar a la sesión.

En lo que sigue, donde dice `PUERTO` poné el tuyo.

## Paso 4: mirar la consola

Antes de tocar nada, conviene ver que el cableado anda. pyserial trae una
terminal serie:

```bash
python3 -m serial.tools.miniterm PUERTO 115200
```

Ahora **enchufá la cámara a su fuente**. Tienen que aparecer, en orden:

```
U-Boot 2010.06-dirty (Feb 27 2016 - 14:46:03)

Check Flash Memory Controller v100 ... Found
SPI Nor(cs 0) ID: 0xc2 0x20 0x18
Block:64KB Chip:16MB Name:"MX25L128XX"
...
*** Warning - bad CRC, using default environment
...
Hit any key to stop autoboot:  1
 0
## Booting kernel from Legacy Image at 82000000 ...
...
Linux version 3.4.35 ...
Machine: hi3518ev200
...
Welcome to HiLinux.
...
(none) login:
```

Qué es cada cosa:
- **`U-Boot 2010.06-dirty`:** el cargador de arranque. Prepara el hardware,
  carga Linux de la flash y lo arranca. Es con quien vamos a hablar.
- **`ID: 0xc2 0x20 0x18`:** la flash, una Macronix (`c2`) de 16 MB (`18`).
- **`bad CRC, using default environment`:** la configuración guardada de
  U-Boot no es válida, así que usa la que trae de fábrica. Es normal en esta
  cámara.
- **`Hit any key to stop autoboot`:** la ventana para frenar el arranque. En
  esta cámara dura **menos de un segundo**.
- **Lo que sigue:** Linux arrancando, la app de fábrica, y un login cuya
  clave no se sabe (y no hace falta).

Para salir de miniterm: **Ctrl+]** (en algunos teclados, Ctrl+5 o Ctrl+AltGr+]).

Así se ve el firmware de fábrica ya arrancado (en la foto, la consola
leída con la Terminal de [P4OS](https://github.com/charliejgallo/P4OS); con
miniterm se ve igual):

![La consola de la SC10W con el firmware de fábrica: el sensor ov9732, los módulos de audio y el login de "(none)"](img/consola-firmware-fabrica.jpg)

**Si sale basura** (signos raros, puntos sueltos), mirá
[Problemas y soluciones](#problemas-y-soluciones): casi siempre es la fuente
o el GND. **Si no sale nada**, probá invertir TXD y RXD en el adaptador.

## Paso 5: frenar el arranque (y por qué cuesta)

Para leer y grabar la flash hay que **frenar a U-Boot en su prompt**,
`hisilicon # `, antes de que arranque Linux. Ahí acepta comandos.

**La trampa:** dice "Hit any key", pero **no se frena con cualquier
tecla**. Ni Enter ni Ctrl+C solos lo frenan: le llegaron 644 Ctrl+C seguidos,
varios dentro de la cuenta, y siguió de largo. Lo que sí lo frena es una
mezcla de teclas mandada sin parar mientras prende:

```
Ctrl+C, Enter, Ctrl+C, espacio, Ctrl+C, q, Ctrl+C, x, Ctrl+C, Esc   (y otra vez)
```

La que sirve es una de espacio, `q`, `x` o Esc (no se averiguó cuál).

Además, la cuenta dura unos 0,7 segundos y llega recién ~5 segundos después
de darle corriente (antes revisa la microSD y el USB). Hacerlo a mano en
miniterm es casi imposible. **Los scripts lo hacen solos:** empiezan a
mandar la mezcla y te dicen "prendé la cámara". Ahí **desenchufás y
enchufás la cámara**, y en unos segundos queda frenada.

Al frenarla, el script verifica dos cosas:
- que la línea que vuelve sea un prompt: lo confirma con un Enter, que
  tiene que devolver la misma línea;
- que sea U-Boot y no un Linux (le pide `version`).

## Paso 6: la copia de seguridad de la flash

**No te saltees este paso.** Es tu forma de volver a fábrica.

```bash
python3 volcar.py --puerto PUERTO --salida fabrica.bin
```

Cuando diga "prendé la cámara", desenchufala y enchufala. Después, esperá.

Qué hace, por dentro:
1. Frena U-Boot (Paso 5) y le pide `version`, `printenv` y `sf probe 0`, que
   inicializa la flash y dice su tamaño (`16384 KiB`).
2. Lee la flash **de a 64 KB**. Para cada pedazo:
   - **`sf read 0x82000000 <posición> 0x10000`:** U-Boot copia ese pedazo
     de la flash a su RAM;
   - **`crc32 0x82000000 0x10000`:** U-Boot calcula el CRC32 de ese pedazo,
     una "huella" de 8 dígitos;
   - **`md.l 0x82000000 0x4000`:** U-Boot imprime ese pedazo como texto
     hexadecimal, y el script lo vuelve a convertir a bytes;
   - **compara** el CRC32 de lo que recibió con el de la cámara. Si no
     coinciden (un carácter que llegó mal por el cable), le pide a U-Boot el
     CRC32 de cada 4 KB y repite solo las partes que vinieron mal.
3. Guarda `fabrica.bin` (16777216 bytes) y `fabrica-consola.txt`, con todo
   lo que dijo la cámara.

**Tarda unos 100 minutos.** La consola de esta cámara no acepta más de
115200 baudios: su U-Boot contesta "not supported" a velocidades mayores.
Además `md` usa casi 4 caracteres por byte: 16 MB son ~65 millones de
caracteres a ~11 500 por segundo.

**Hacelo dos veces** y compará: si las dos copias son iguales, es la buena.

```bash
python3 volcar.py --puerto PUERTO --salida fabrica2.bin --comparar fabrica.bin --ya-frenada
```

(`--ya-frenada` porque la cámara quedó en el prompt después de la primera.)
Tiene que terminar con **`IGUAL byte por byte`**. Guardá `fabrica.bin` en
dos lugares.

Lo que hay en la flash de fábrica, si querés mirarla (con
[binwalk](https://github.com/ReFirmLabs/binwalk), o con un editor
hexadecimal):

| Desde | Tamaño | Partición | Qué hay |
|---|---|---|---|
| 0x000000 | 512K | boot | U-Boot 2010.06 |
| 0x080000 | 2560K | kernel | Linux 3.4.35 (uImage: empieza con `27 05 19 56`) |
| 0x300000 | 12800K | rootfs | el sistema, en jffs2 (bloques que empiezan con `85 19`) |
| 0xF80000 | 512K | config | la configuración de la app, otro jffs2 |

## Paso 7: bajar OpenIPC y armar la imagen

**El atajo:** la imagen ya armada está en este repositorio,
[`firmware/openipc-sc10w-16mb.bin`](firmware/openipc-sc10w-16mb.bin)
(CRC32 `05f1243a`), hecha con `armar_imagen.py` y las tres piezas de la
release de OpenIPC del 4/11/2026, que también están en `firmware/`. Si la
usás, renombrala `openipc.bin` y saltá al [Paso 8](#paso-8-preparar-la-microsd).
Lo que sigue es para armarla vos con la release más nueva.

OpenIPC publica sus compilaciones en
[github.com/OpenIPC/firmware/releases/tag/latest](https://github.com/OpenIPC/firmware/releases/tag/latest).
Hacen falta dos archivos:

1. **`openipc.hi3518ev200-nor-ultimate.tgz`:** el sistema. Adentro trae
   `uImage.hi3518ev200` (el kernel) y `rootfs.squashfs.hi3518ev200` (el
   resto), cada uno con su `.md5sum`.
   - **"nor"** porque la flash es NOR (SPI), no NAND.
   - **"ultimate"** es la versión completa, que entra porque la flash es de
     16 MB. La "lite" es para flashes de 8 MB.
2. **`u-boot-hi3518ev200-universal.bin`:** el U-Boot de OpenIPC para este
   procesador.

Descomprimí el `.tgz` (en Windows, con 7-Zip; en macOS y Linux, `tar xzf`) y
verificá los MD5:

```bash
md5sum uImage.hi3518ev200 rootfs.squashfs.hi3518ev200    # Linux
md5 uImage.hi3518ev200 rootfs.squashfs.hi3518ev200       # macOS
certutil -hashfile uImage.hi3518ev200 MD5                # Windows
```

Tienen que coincidir con los `.md5sum`.

**Armá la imagen de 16 MB:**

```bash
python3 armar_imagen.py \
    --uboot u-boot-hi3518ev200-universal.bin \
    --kernel uImage.hi3518ev200 \
    --rootfs rootfs.squashfs.hi3518ev200 \
    --salida openipc.bin
```

(En Windows, todo en una línea, sin las `\`.)

El script arma la imagen con el layout de 16 MB de OpenIPC:

| Desde | Tamaño | Partición | Qué va |
|---|---|---|---|
| 0x000000 | 256K | boot | U-Boot de OpenIPC |
| 0x040000 | 64K | env | vacío: OpenIPC escribe ahí su configuración |
| 0x050000 | 3072K | kernel | `uImage.hi3518ev200` |
| 0x350000 | 10240K | rootfs | `rootfs.squashfs.hi3518ev200` |
| 0xD50000 | el resto | rootfs_data | vacío: OpenIPC lo formatea al arrancar, para tus cambios |

Además:
- deja todo lo que sobra en `0xFF`, que es lo que tiene una flash borrada;
- comprueba que cada pieza entre y sea lo que dice ser (el kernel empieza
  con `27 05 19 56` y el sistema con `hsqs`);
- al final dice el **CRC32** de la imagen.

Con la release del 4/11/2026 dio `05f1243a`. Con otra release va a dar otro:
no importa, porque `instalar.py` lo calcula solo.

## Paso 8: preparar la microSD

1. **Formateala en FAT32**, con una sola partición:
   - **Windows:** clic derecho → Formatear → FAT32. Para tarjetas de más
     de 32 GB Windows no ofrece FAT32; usá una más chica o una herramienta
     como guiformat.
   - **macOS:** Utilidad de Discos → Borrar → "MS-DOS (FAT)", esquema
     "Registro de arranque maestro".
   - **Linux:** `sudo mkfs.vfat -F 32 /dev/sdX1`.
2. **Copiá `openipc.bin` a la raíz** de la tarjeta, con ese nombre: corto,
   sin espacios.
3. **No pongas en la tarjeta archivos con estos nombres:** `config`,
   `u-boot`, `kernel`, `rootfs`, `rootfsbk` ni `autoupdate-*.img`.
   El U-Boot de fábrica y el de OpenIPC los buscan al arrancar para
   actualizarse solos, y los grabarían sin preguntar.
4. Expulsala bien de la computadora y **ponela en la cámara con la cámara
   desenchufada**.

## Paso 9: instalar OpenIPC

```bash
python3 instalar.py --puerto PUERTO --imagen openipc.bin --openipc
```

`--imagen` es **el mismo archivo** que copiaste a la tarjeta: el script lo
usa para saber su tamaño y su CRC32. Cuando diga "prendé la cámara",
desenchufala y enchufala (con la microSD puesta).

Lo que va a pasar:

1. **Frena U-Boot.**
2. **Mira la microSD.** `mmcinfo` muestra la tarjeta y `fatls mmc 0` sus
   archivos: tiene que estar `openipc.bin` con 16777216 bytes.
3. **Carga la imagen a la RAM y la verifica.**
   - `mw.b 0x82000000 0xff 0x1000000` llena esa RAM de `0xFF`.
   - `fatload mmc 0 0x82000000 openipc.bin` copia el archivo a la RAM.
   - `crc32 0x82000000 0x1000000` tiene que dar el CRC32 de la imagen.

   Si no coincide, **para ahí**: la flash no se tocó.

   ![La consola durante la instalación: mmcinfo muestra la microSD, fatls el archivo openipc.bin de 16777216 bytes, fatload lo carga y crc32 da 05f1243a](img/instalar-1-microsd-y-crc32.jpg)

4. **Pregunta.** Escribí `GRABAR` y Enter. Recién ahí:
   - `sf erase 0x0 0x1000000` borra los 16 MB (~66 s).
   - `sf write 0x82000000 0x0 0x1000000` graba la imagen (~21 s).

   | Borrando | Grabando | Grabada |
   |---|---|---|
   | ![sf erase, bloque por bloque, por el 40 %](img/instalar-2-borrado.jpg) | ![terminó el borrado al 100 % y empieza sf write](img/instalar-3-grabacion.jpg) | ![sf write al 100 % y el mw.b que pone la RAM en ceros para verificar](img/instalar-4-grabado.jpg) |

5. **Verifica:**
   - `mw.b 0x82000000 0x00 0x1000000` pone la RAM en ceros, para estar
     seguros de que lo que sigue viene de la flash.
   - `sf read 0x82000000 0x0 0x1000000` lee la flash de vuelta.
   - `crc32` tiene que dar otra vez el CRC32 de la imagen.

   Si no da, **no desenchufes nada**: el script repite el borrado y la
   grabación, hasta tres veces.
6. **Reinicia** (`reset`). Arranca el U-Boot de OpenIPC, pero con el layout
   de 8 MB, que es el que trae de fábrica. Linux no encuentra su sistema
   donde lo busca y entra en pánico (`Kernel panic ... Unable to mount
   root fs`), y la cámara se reinicia cada 20 segundos. **Es lo esperado.**
7. **El script frena ese U-Boot** (prompt `OpenIPC # `) y corre
   **`run setnor16m`**. Ese comando cambia el layout al de 16 MB, lo guarda
   (`saveenv`) y reinicia.
8. **Arranca OpenIPC.** El script termina cuando ve
   `openipc-hi3518ev200 login:`.

   ![El primer arranque de OpenIPC en la consola: dropbear, crond, los módulos de video, "Starting majestic: OK", "Welcome to OpenIPC" y el login](img/openipc-primer-arranque.jpg)

**Si algo se corta** a la mitad (se desenchufó el cable USB, se cerró la
ventana): mientras la cámara siga prendida y en el prompt, volvé a correr
lo mismo con `--ya-frenada`.

## Paso 10: el primer arranque y la configuración

En el primer arranque OpenIPC:
- formatea su partición `rootfs_data`;
- **detecta solo el sensor** ("set SENSOR as ov9732");
- cambia la MAC de ejemplo (`00:00:23:34:45:66`) por una propia.

Todavía no tiene red, porque falta la WiFi.

1. **Entrá por la consola:**

   ```bash
   python3 -m serial.tools.miniterm PUERTO 115200
   ```

   Enter. Usuario **`root`**, clave **`12345`**.
2. **Cambiá la clave:**

   ```
   passwd
   ```

3. **Configurá la WiFi:**

   ```
   fw_setenv wlandev mt7601u-generic
   fw_setenv wlanssid "Nombre de tu red"
   fw_setenv wlanpass "Clave de tu red"
   reboot
   ```

   `mt7601u-generic` es el perfil del módulo MT7601U de esta cámara, que se
   prende solo sin tocar ningún GPIO, igual que con el firmware de fábrica.
   Las tres variables quedan guardadas en la configuración de U-Boot.
4. **Encontrá la IP:** en la lista de clientes DHCP de tu router, o en la
   consola con `ip a` (busca `wlan0`).
5. **La página web:** `http://IP-DE-LA-CAMARA`, usuario `root` y la clave
   nueva. En **Live** está el video (la foto del principio de este
   tutorial).
6. **El video por RTSP** (para VLC: Medio → Abrir ubicación de red):
   - principal: `rtsp://root:CLAVE@IP-DE-LA-CAMARA:554/stream=0`
   - secundario, más liviano: `rtsp://root:CLAVE@IP-DE-LA-CAMARA:554/stream=1`
7. **La configuración del video** (resolución, bitrate, grabación en la
   microSD, detección de movimiento, MQTT) está en `/etc/majestic.yaml`, o
   en la página web. La grabación va en la sección `records`.
8. **La consola ya no hace falta.** Podés entrar por SSH (`ssh
   root@IP-DE-LA-CAMARA`), desoldar los cables y cerrar la cámara. Si
   pensás volver a tocarla, dejalos: no molestan.

**Pendiente:** los GPIO de las luces infrarrojas, del filtro IR-cut, del
parlante y del botón de esta cámara todavía no están identificados para
OpenIPC.

## Por qué tarda tanto en arrancar

Entre que la enchufás y ves video pasan varios segundos de más que en una
cámara nueva. Es el hardware:
- un procesador de 2015 de un solo núcleo;
- 32 MB de RAM para Linux (el resto es para el video);
- y en cada arranque, cargar los módulos de video de HiSilicon, inicializar
  el sensor, levantar la WiFi por USB, conseguir IP y arrancar Majestic (el
  programa que comprime y sirve el video).

## Volver al firmware de fábrica

Con la copia del Paso 6:

1. Copiá `fabrica.bin` a la raíz de la microSD (FAT32), con ese nombre.
2. Con la cámara desenchufada, poné la tarjeta.
3. Corré el script:

   ```bash
   python3 instalar.py --puerto PUERTO --imagen fabrica.bin
   ```

   (sin `--openipc`). Cuando diga "prendé la cámara", desenchufala y
   enchufala.

Funciona igual desde el U-Boot de OpenIPC (`OpenIPC # `) que desde el de
fábrica, porque los dos tienen `mmc`, `fatload`, `sf` y `crc32`. Al final
reinicia con el firmware de fábrica tal cual estaba.

**Si la cámara no arranca para nada** (ni U-Boot aparece por la consola):

- **Pinza SOIC8 y programador CH341A**, con [flashrom](https://flashrom.org):
  1. Cámara **desenchufada**.
  2. La pinza sobre la flash (el chip de 8 patas marcado MX25L128, con el
     punto o la muesca hacia la pata 1 de la pinza).
  3. Grabar y verificar:

     ```bash
     flashrom -p ch341a_spi -w fabrica.bin
     ```

  **Ojo:** los CH341A negros comunes tienen las líneas de datos a **5 V**
  aunque el chip sea de 3,3 V. Hay que usar uno de 3,3 V o modificarlo
  (hay guías buscando "CH341A 3.3V mod"). Además, la pinza alimenta la placa
  entera de la cámara: si flashrom no reconoce el chip, probá con otra
  fuente de 3,3 V con GND común.
- **La ROM del Hi3518EV200:** al arrancar, si recibe por la consola un
  patrón especial, acepta que le carguen un U-Boot a la RAM. Es lo que hace
  la herramienta `burn` de OpenIPC (github.com/OpenIPC/burn). Con ese U-Boot
  en RAM se repite el Paso 9 con `--ya-frenada`.

## Problemas y soluciones

| Síntoma | Causa probable | Qué hacer |
|---|---|---|
| Por la consola sale basura (puntos, signos raros, pocos bytes) | **La fuente de la cámara** o el GND | Otra fuente de 5 V, de 1 A o más; revisar que el GND esté conectado. Nos pasó con una fuente floja |
| No sale nada | TXD y RXD sin cruzar, o el adaptador en otro puerto | Invertir TXD/RXD; revisar el puerto (Paso 3) |
| Sale bien pero no se frena ("arranco Linux sin frenarse") | Las teclas empezaron tarde | Correr el script **antes** de enchufar la cámara, y enchufarla recién cuando diga "prendé la cámara" |
| `volcar.py` dice "no salió bien en 4 intentos" | Muchos errores en el cable | Cables más cortos, lejos del parlante, y la fuente buena. Volver a correr |
| `instalar.py` no ve el archivo en la microSD | La tarjeta no es FAT32, o tiene varias particiones, o el nombre no coincide | Formatearla de nuevo (Paso 8); mismo nombre que `--imagen` |
| El CRC de la RAM no coincide (paso 3 del script) | El archivo de la tarjeta no es el mismo que `--imagen`, o la tarjeta falla | Volver a copiarlo; probar otra tarjeta. No se tocó la flash |
| El CRC de la flash no coincide después de grabar | Raro: la flash o la alimentación | El script repite solo. **No desenchufar** |
| Después de instalar, se reinicia cada 20 s con "Kernel panic" | Faltó `run setnor16m`, por ejemplo si corriste sin `--openipc` | Frenar el U-Boot de OpenIPC (`instalar.py` lo hace, o cualquier tecla en miniterm justo al arrancar) y escribir `run setnor16m` |
| OpenIPC arranca pero no se conecta a la WiFi | Nombre o clave mal, o una red de 5 GHz | El MT7601U es solo de 2,4 GHz. Revisar con `fw_printenv wlanssid` y volver a configurar |
| "Permission denied" al abrir el puerto (Linux) | Tu usuario no está en `dialout` | `sudo usermod -aG dialout $USER` y volver a entrar |

## Detalles técnicos

Lo que dijo la cámara durante este trabajo, por si sirve para otras
parecidas.

**El U-Boot de fábrica:**
- `U-Boot 2010.06-dirty (Feb 27 2016 - 14:46:03)`, prompt `hisilicon # `,
  `bootdelay=1`.
- `bootcmd=sf probe 0;sf read 0x82000000 0x80000 0x280000;bootm 0x82000000`
- `bootargs=mem=40M console=ttyAMA0,115200 root=/dev/mtdblock2
  rootfstype=jffs2 mtdparts=hi_sfc:512K(boot),2560K(kernel),12800K(rootfs),512K(config) init=/linuxrc`
- **Comandos:** `sf`, `md`, `mm`, `mw`, `cp`, `cmp`, `crc32`, `mmc`,
  `mmcinfo`, `fatls`, `fatload`, `ext2load`, `usb`, `loadb`, `loady`,
  `tftp`, `bootm`, `go`, `setenv`, `saveenv`, `getinfo`, `reset`.
- **No tiene:** `bdinfo`, ni nada para mandar archivos por la serie
  (`loadb`/`loady` solo reciben).
- **Velocidades:** solo acepta hasta 115200; a `setenv baudrate 921600`,
  460800 y 230400 contesta "not supported".
- **La RAM:** 64 MB, de 0x80000000 a 0x84000000. 0x82000000 es la dirección
  de trabajo que usa el propio fabricante para cargar el kernel.
- **Con microSD:** antes de la cuenta busca `config`, `u-boot`, `kernel`,
  `rootfs` y `rootfsbk` (su actualización por tarjeta).

**El Linux de fábrica:**
- Kernel 3.4.35, compilado con la toolchain `arm-hisiv300-linux` (gcc 4.8.3).
- **Watchdog por hardware:** de 3 segundos, y una vez armado no se puede
  apagar (`nowayout=1`).
- **Scripts de arranque:** `S00devs`, `S01udev`, `S03bootargs`, `S09init`,
  `S20drv` (los módulos de video de HiSilicon), `S22WifiDrv` y `S90app`.
- **La app:** `241BA_2.0.16` (16/11/2018), con la librería de nube Danale
  1.0.170420. Busca una actualización en la microSD al arrancar.

**OpenIPC en esta cámara:**
- **U-Boot:** `U-Boot 2010.06 (Oct 04 2026)` de OpenIPC, prompt `OpenIPC # `.
  Se frena con cualquier tecla. Lee `autoupdate-uboot.img`,
  `autoupdate-kernel.img` y `autoupdate-rootfs.img` de la microSD.
- **Kernel:** 4.9.37, con `mem=32M`; la MMZ de 32M en 0x82000000 es para el
  video.
- **mtdparts:**
  `hi_sfc:256k(boot),64k(env),3072k(kernel),10240k(rootfs),-(rootfs_data)`.

**Por qué la copia es por `md` y tan lenta:** este U-Boot no puede mandar
archivos por la consola. Lo único que saca datos es imprimirlos (`md`). Lo
más rápido sería copiarlos a una microSD con `mmc write`. Funciona, pero
escribe en sectores crudos de la tarjeta, pisando lo que haya. Se prefirió la
consola por ser segura y verificada. Para leer la flash en minutos, la pinza
SOIC8.

## Probar los scripts sin la cámara

`fake_uboot.py` es un U-Boot de mentira que imita al de esta cámara:
- se frena con una sola tecla que no es ni Enter ni Ctrl+C;
- tiene su mismo layout de flash;
- con `--writable`, tiene una "microSD", deja grabar y, después de
  instalar, hace de U-Boot de OpenIPC con su pánico y su `setnor16m`.

Usa un pty, así que anda en **macOS y Linux** (no en Windows).

```bash
mkdir sd && cp openipc.bin sd/
python3 fake_uboot.py serve --writable --sd sd --flash-out cam.bin
# dice: PTY /dev/ttys004
```

En otra terminal, los mismos comandos del tutorial, con ese pty de puerto:

```bash
python3 volcar.py --puerto /dev/ttys004 --salida fabrica.bin
cp fabrica.bin sd/
python3 instalar.py --puerto /dev/ttys004 --imagen sd/openipc.bin --openipc --ya-frenada
```

- **La "cámara" arranca sola** con el primer byte que le llega. Para
  "desenchufarla": `kill -USR1 <pid de fake_uboot.py>`.
- **Al cerrarlo** (Ctrl+C), deja la flash final en `cam.bin.after`.
- **Al salir dice** cuántos comandos de escritura recibió.

Así se probaron los scripts:
1. copiar los 16 MB, idénticos a su flash;
2. instalar OpenIPC hasta el login;
3. "desenchufar", volver a fábrica, y comprobar que la flash quedó igual
   byte por byte a la original.

## Cómo se hizo

Esta cámara se abrió, se copió y se le instaló OpenIPC el 4 y 5 de noviembre
de 2026 usando [P4OS](https://github.com/charliejgallo/P4OS) como
herramienta de campo: una placa con pantalla que habla por su consola.
- El "Programador" de P4OS copió la flash por U-Boot (dos veces, iguales).
- Su Terminal mandó los comandos de la instalación (las fotos del
  [Paso 9](#paso-9-instalar-openipc)).

![El Programador de P4OS copiando la flash de la cámara por su U-Boot: familia U-Boot, Hi3518EV200, flash MX25L128 de 16 MB](img/p4os-programador-volcado.jpg)

Este tutorial pasa lo mismo a un adaptador USB-serie común y unos scripts
de Python, para que cualquiera lo pueda repetir.

## Créditos y licencias

- **OpenIPC:** [openipc.org](https://openipc.org) y
  [github.com/OpenIPC](https://github.com/OpenIPC). El firmware de
  `firmware/` y su U-Boot son de ellos; cada pieza tiene su licencia (Linux
  y U-Boot GPL-2.0, OpenIPC MIT, Majestic Prosperity 3.0.0). Todo el
  detalle, en [`CREDITOS.md`](CREDITOS.md).
- **El tutorial, los scripts y las fotos:** Charlie Gallo, licencia MIT
  ([`LICENSE`](LICENSE)).
