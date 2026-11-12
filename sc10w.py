"""
sc10w.py - hablar con el U-Boot de una camara por su consola serie.

Es la parte comun de volcar.py e instalar.py. Habla con cualquier U-Boot por
un adaptador USB-serie comun (CH340, CP2102, FT232...) y solo necesita
pyserial (pip install pyserial).

Que hace:
- abre el puerto (115200 8N1, sin control de flujo);
- frena el arranque mandando una mezcla de teclas mientras la camara
  prende (ver frenar());
- reconoce el prompt ("hisilicon # ", "OpenIPC # ", "=> "...);
- manda comandos y junta lo que contestan hasta que vuelve el prompt;
- lee la RAM de la camara con "md.l" y la verifica con su propio "crc32".

Si se pierde un byte en el peor lugar (un adaptador barato, un hub), el
prompt puede llegar pegado a la ultima linea de "md", o no llegar: entonces
se recupera el prompt con Ctrl+C y Enter y se sigue con lo que llego; la
verificacion por crc32 vuelve a pedir lo que falte. Antes eso cortaba todo
con "no volvio el prompt".

Probado con una Orvibo SC10W (Hi3518EV200, U-Boot 2010.06 de HiSilicon) y,
sin camara, contra tools/fake_uboot.py de P4OS.
"""
import re
import sys
import time
import zlib

try:
    import serial
except ImportError:
    sys.exit("Falta pyserial: pip install pyserial")

# El U-Boot de la SC10W dice "Hit any key to stop autoboot", pero no le
# alcanzan ni Enter ni Ctrl+C solos (dejo pasar 644 Ctrl+C seguidos). Lo
# frena esta mezcla, mandada sin parar: una de espacio, q, x o Esc es la que
# sirve. Ctrl+C entre cada una limpia la linea si ya se freno.
TECLAS = [b"\x03", b"\r", b"\x03", b" ", b"\x03", b"q", b"\x03", b"x", b"\x03", b"\x1b"]

# Un prompt: una linea corta que termina en #, > o =>, sin "login"
_PROMPT = re.compile(r"^[\w\-\. ]{0,20}(#|>|=>) ?$")


class Consola:
    def __init__(self, puerto, baudios=115200, registro=None):
        self.ser = serial.Serial(puerto, baudios, timeout=0.05)
        self.prompt = None
        self.linea = ""              # lo que llego desde el ultimo salto de linea
        self.registro = registro     # un archivo donde va todo lo que dice la camara

    # -- el cable ---------------------------------------------------------

    def _leer(self, segundos, al_llegar=None):
        """Lee durante 'segundos'. Cada linea completa va a al_llegar(linea).
        Devuelve True si llego algo."""
        hubo = False
        fin = time.time() + segundos
        while time.time() < fin:
            datos = self.ser.read(4096)
            if not datos:
                continue
            hubo = True
            if self.registro:
                self.registro.write(datos)
            for c in datos.decode("latin-1"):
                if c == "\n":
                    if al_llegar:
                        al_llegar(self.linea)
                    self.linea = ""
                elif c == "\b":
                    self.linea = self.linea[:-1]
                elif c not in "\r\x00":
                    self.linea += c if " " <= c <= "~" else "."
        return hubo

    def en_prompt(self):
        return self.prompt is not None and self.linea == self.prompt

    # -- frenar el arranque ------------------------------------------------

    def frenar(self, segundos=90, aviso="Mandando teclas: prende la camara (o desenchufala y enchufala) ahora..."):
        """Manda la mezcla de teclas hasta ver un prompt, que confirma con un
        Enter. Hay que prender (o reiniciar) la camara mientras corre."""
        if aviso:
            print(aviso)
        vio = {"cuenta": False, "linux": False}

        def mirar(l):
            if "autoboot" in l or "any key" in l:
                vio["cuenta"] = True
            if "Starting kernel" in l or "Linux version" in l:
                vio["linux"] = True

        fin = time.time() + segundos
        k = 0
        while time.time() < fin:
            self.ser.write(TECLAS[k % len(TECLAS)])
            k += 1
            self._leer(0.08, mirar)
            if not _PROMPT.match(self.linea) or "login" in self.linea:
                continue
            candidato = self.linea
            self._leer(0.2, mirar)
            for _ in range(2):
                self.ser.write(b"\r")
                lineas = []
                self._leer(0.4, lineas.append)
                if lineas and self.linea == candidato:
                    self.prompt = candidato
                    return True
        if vio["linux"]:
            raise RuntimeError("La camara arranco Linux sin frenarse. Proba de nuevo, con las teclas "
                               "saliendo ANTES de darle corriente.")
        if vio["cuenta"]:
            raise RuntimeError("Aparecio la cuenta del autoboot pero no se freno.")
        raise RuntimeError("No llego nada por la consola: revisa TX/RX cruzados, GND y la fuente.")

    def esperar_prompt(self, segundos=5):
        """Para cuando ya esta frenada: un Enter y el prompt que vuelve."""
        self.ser.write(b"\x03")
        self._leer(0.3)
        self.ser.write(b"\r")
        self._leer(0.5)
        if _PROMPT.match(self.linea):
            self.prompt = self.linea
            return True
        return False

    # -- comandos ---------------------------------------------------------

    def comando(self, cmd, espera=30, al_llegar=None):
        """Manda cmd y junta las lineas hasta que vuelve el prompt. 'espera'
        son los segundos sin que llegue nada que se aguantan."""
        self._leer(0.05)
        self.linea = ""
        self.ser.write(cmd.encode() + b"\r")
        lineas = []

        def guardar(l):
            if (self.prompt and l.startswith(self.prompt)) or (not lineas and l.strip() == cmd):
                return                          # el eco del comando
            lineas.append(l)
            if al_llegar:
                al_llegar(l)

        ultimo = time.time()
        while True:
            if self._leer(0.1, guardar):
                ultimo = time.time()
            if self.en_prompt():
                return lineas
            # el prompt pegado a la ultima linea (se perdio su salto de linea):
            # cuando ya no llega nada mas. Esa ultima linea se pierde; crc32 lo nota.
            if self.prompt and self.linea.endswith(self.prompt) and time.time() - ultimo > 0.3:
                self.linea = self.prompt
                return lineas
            if time.time() - ultimo > espera:
                if self.recuperar_prompt():
                    return lineas
                raise RuntimeError(f"'{cmd}' no termino: no volvio el prompt en {espera} s")

    def recuperar_prompt(self, intentos=3):
        """El prompt no volvio (se perdio en el cable): Ctrl+C y Enter hasta
        que vuelva. True si volvio."""
        for _ in range(intentos):
            self.ser.write(b"\x03")
            self._leer(0.3)
            self.linea = ""
            self.ser.write(b"\r")
            self._leer(0.6)
            if self.en_prompt():
                return True
        return False

    def crc32(self, addr, n, intentos=3):
        """El CRC32 que calcula la camara de su RAM (el mismo que zlib.crc32).
        Si la respuesta llego mal, se pide otra vez; None si nunca llego."""
        for _ in range(intentos):
            for l in self.comando(f"crc32 0x{addr:x} 0x{n:x}"):
                m = re.search(r"==>\s*([0-9a-fA-F]{8})", l)
                if m:
                    return int(m.group(1), 16)
        return None

    def leer_ram(self, addr, n):
        """La RAM de addr a addr+n con md.l. Lo que no llego bien queda en 0:
        hay que verificarlo con crc32()."""
        buf = bytearray(n)

        def linea(l):
            m = re.match(r"^([0-9a-fA-F]{8}):((?: [0-9a-fA-F]{8}){1,4})(?:  |$)", l)
            if not m:
                return
            a = int(m.group(1), 16)
            palabras = m.group(2).split()
            if a % 16 or a < addr or a + 4 * len(palabras) > addr + n:
                return
            o = a - addr
            for i, w in enumerate(palabras):
                buf[o + 4 * i:o + 4 * i + 4] = int(w, 16).to_bytes(4, "little")
        self.comando(f"md.l 0x{addr:x} 0x{n // 4:x}", espera=10, al_llegar=linea)
        return buf

    def leer_verificado(self, addr, n, intentos=4):
        """La RAM, verificada contra el crc32 de la camara. Si no coincide, el
        crc32 de cada 4 KB dice que parte vino mal y solo esa se repite; si
        sigue mal, de a 256 bytes (_reparar_fino)."""
        quiere = self.crc32(addr, n)
        if quiere is None:
            raise RuntimeError("Este U-Boot no tiene crc32")
        if quiere == zlib.crc32(b"\xff" * n):
            return bytearray(b"\xff" * n)       # vacio: ni se imprime
        buf = self.leer_ram(addr, n)
        for _ in range(intentos):
            if zlib.crc32(buf) == quiere:
                return buf
            for o in range(0, n, 4096):
                m = min(4096, n - o)
                w = self.crc32(addr + o, m)
                for k in range(4):
                    if zlib.crc32(buf[o:o + m]) == w:
                        break
                    if k < 2:
                        buf[o:o + m] = self.leer_ram(addr + o, m)
                    else:
                        self._reparar_fino(buf, addr, o, m)
        if zlib.crc32(buf) != quiere:
            raise RuntimeError(f"0x{addr:x}: no salio bien en {intentos} intentos")
        return buf

    def _reparar_fino(self, buf, addr, o, m, paso=256, intentos=6):
        """Un pedazo de 4 KB que sigue mal: de a 256 bytes, cada uno contra su
        crc32 y repetido solo si hace falta. Con mucho ruido en el cable, 4 KB
        (unos 19 mil caracteres de md) rara vez llegan enteros; 256 bytes si."""
        for p in range(o, o + m, paso):
            q = min(paso, o + m - p)
            w = self.crc32(addr + p, q)
            for _ in range(intentos):
                if w is None or zlib.crc32(buf[p:p + q]) == w:
                    break
                buf[p:p + q] = self.leer_ram(addr + p, q)

    def cerrar(self):
        self.ser.close()


def tamano(s):
    """'16M', '0x1000000', '512K' -> bytes"""
    s = s.strip().upper()
    if s.endswith("M"):
        return int(s[:-1], 0) << 20
    if s.endswith("K"):
        return int(s[:-1], 0) << 10
    return int(s, 0)
