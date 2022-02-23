from asyncpg import InvalidTimeZoneDisplacementValueError
from quart import Quart, render_template, request, abort
import socket
import time
import asyncio

def nonblocking_readline(f, timeout=250):
	timeout = timeout + int(round(time.time() * 1000))
	line = b""
	while int(round(time.time() * 1000)) < timeout:
		char = f.read(1)
		if char is None:
			time.sleep(0.01)
			continue
		line += char
		if char == b"\n":
			return line
	raise IOError(0, 'Timeout')

class CP750Control():

    def __init__(self):
        self.port = 61408
        self.destination = "cp750 ip címe" 
        self.socket = None
        self.socket_stream = None

    def is_connected(self):
        if self.socket is None:
            print("[Connection - HIBA] ~> A csatlakozás a CP750-hez sikertelen!")
            return False
        checkver = self.send('cp750.sysinfo.version ?')
        if not checkver:
            self.disconnect()
            return checkver
        print("[Connection - INFO] ~> A csatlakozás a CP750-hez sikeres!")
        return True

    def connect(self):
        if self.socket:
            self.disconnect()
        print(f"[Connection - INFO] ~> Csatlakozás a CP750-hez, itt: {self.destination}:{self.port}")
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(10)
            s.connect((self.destination, self.port))
            s.settimeout(500)
            s.setblocking(False)
            self.socket_stream = s.makefile("rwb", 0)
            self.socket = s
        except:
            print(f"[Connection - HIBA] ~> A csatlakozás a CP750-hez meghiúsult, itt: {self.destination}:{self.port}")
            return
        return self.is_connected()

    def disconnect(self):
        if self.socket:
            print(f"Lecsatlakozás innen: {self.destination}:{self.port}")
            try:
                self.socket.close()
            except:
                print("A lecsatlakozás közben hiba történt!")
                return
            finally:
                self.socket = None
                self.socket_stream = None
        return self.is_connected()

    def send(self, command):
        print(f"[Parancskezelő - INFO] ~> Parancs: {command}")
        if not self.socket:
            self.connect()
        try:
            result = ""
            self.socket_stream.write(command.encode('UTF-8') + b"\r\n")
            line = nonblocking_readline(self.socket_stream).decode('UTF-8').strip()
            while line:
                result = result + line + "\n"
                line = nonblocking_readline(self.socket_stream).decode('UTF-8').strip()
            return result.strip()
        except:
            print(f"[Parancskezelő - HIBA] ~> Parancs '{command}' hibát jelzett.")
            return

cp750 = CP750Control()

app = Quart(__name__)

@app.route('/')
async def main():
    version = cp750.send("cp750.sysinfo.version ?")
    if not version:
        return abort(500)
    version = version.split(' ')[1]
    await asyncio.sleep(0.2)
    input_mode = cp750.send("cp750.sys.input_mode ?")
    if not input_mode:
        return abort(500)
    input_mode = input_mode.split(' ')[1]
    if input_mode == "analog":
        input_mode = "Multi-ch Analog"
    if input_mode == "dig_1":
        input_mode = "Digital 1"
    if input_mode == "dig_2":
        input_mode = "Digital 2"
    if input_mode == "dig_3":
        input_mode = "Digital 3"
    if input_mode == "dig_4":
        input_mode = "Digital 4"
    if input_mode == "non_sync":
        input_mode = "Non-Sync"
    if input_mode == "mic":
        input_mode = "Microphone"
    await asyncio.sleep(0.2)
    fader = cp750.send("cp750.sys.fader ?")
    if not fader:
        return abort(500)
    fader = float(fader.split(' ')[1])
    await asyncio.sleep(0.2)
    decode_mode = cp750.send("cp750.state.decode_mode ?")
    if not decode_mode:
        return abort(500)
    decode_mode = decode_mode.split(' ')[1]
    if decode_mode == "lr_discrete":
        decode_mode = "Discrete"
    if decode_mode == "auto":
        decode_mode = "Automatikus"
    if decode_mode == "invalid":
        decode_mode = "Érvénytelen"
    if decode_mode == "n_a":
        decode_mode = "NA"
    if decode_mode == "prologic":
        decode_mode = "Pro Logic"
    if decode_mode == "prologic_2":
        decode_mode = "Pro Logic II"
    if decode_mode == "4_discrete_sur":
        decode_mode = "4 Discrete Surrounds"
    return await render_template('index.html', version=version, input_mode=input_mode, fader=fader, decode_mode=decode_mode)

@app.route('/send', methods=['POST'])
async def send_cmd():
    data = await request.form
    if data.get("cmd"):
        resp = cp750.send(data.get("cmd"))
    return resp

app.run(host="0.0.0.0", port=5782)