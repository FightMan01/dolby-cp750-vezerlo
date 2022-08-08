from quart import Quart, render_template, request, abort
import socket
import time

debug_mode = False

class CP750Control():

    def __init__(self):
        self.port = 61408
        self.destination = "10.36.11.13" #CP750 IP címe
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
            s.connect((self.destination, self.port))
            s.settimeout(10)
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
            self.socket_stream.write(command.encode('UTF-8') + b"\r\n")
            time.sleep(0.05) # 50ms várakozási idő. Ez egy belső hálózaton bőven elégnek kell lennie.
            res = self.socket_stream.read().decode('UTF-8').strip()
            return res
        except:
            print(f"[Parancskezelő - HIBA] ~> Parancs '{command}' hibát jelzett.")
            return

cp750 = CP750Control()

app = Quart(__name__)

@app.route('/')
async def main():
    dolby51warn = False
    if not debug_mode:
        version = cp750.send("cp750.sysinfo.version ?")
    else:
        version = "cp750.sysinfo.version 1.2.3.8"
    if not version:
        return abort(500)
    version = version.split(' ')[1]
    if not debug_mode:
        input_mode = cp750.send("cp750.sys.input_mode ?")
    else:
        input_mode = "cp750.sys.input_mode dig_1"
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
    if not debug_mode:
        fader = cp750.send("cp750.sys.fader ?")
    else:
        fader = "cp750.sys.fader 55"
    if not fader:
        return abort(500)
    fader = float(fader.split(' ')[1])
    if not debug_mode:
        decode_mode = cp750.send("cp750.state.decode_mode ?")
    else:
        decode_mode = "cp750.state.decode_mode 4_discrete_sur"
    if not decode_mode:
        return abort(500)
    decode_mode = decode_mode.split(' ')[1]
    if decode_mode == "lr_discrete":
        decode_mode = "Discrete (aka Dolby 5.1)"
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
        dolby51warn = True
        decode_mode = "4 Discrete Surrounds (aka Dolby 7.1)"
    if not debug_mode:
        muted = cp750.send("cp750.sys.mute ?")
    else:
        muted = "cp750.sys.mute 1"
    muted = int(muted.split(' ')[1])
    return await render_template('index.html', version=version, input_mode=input_mode, fader=fader, decode_mode=decode_mode, muted=muted, dolbywarn=dolby51warn)

@app.route('/send', methods=['POST'])
async def send_cmd():
    data = await request.form
    print(f"[HTTP - INFO] ~> Beérkezett parancs: {data.get('cmd')}")
    if not debug_mode:
        if data.get("cmd"):
            resp = cp750.send(data.get("cmd"))
        if resp:
            return resp
        else:
            return abort(500)
    else:
        return data.get("cmd")

app.run(host="0.0.0.0", port=5782)