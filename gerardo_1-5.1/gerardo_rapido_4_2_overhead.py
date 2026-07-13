import board, keypad, time, digitalio, random
from ideaboard import IdeaBoard
from time import sleep

ib = IdeaBoard()
sleep(1)

keys = keypad.Keys((board.IO0,), value_when_pressed=False, pull=True)

sen = [
    ib.AnalogIn(board.IO36),
    ib.AnalogIn(board.IO39),
    ib.AnalogIn(board.IO34),
    ib.AnalogIn(board.IO35),
]

thr = [0]*4

trig = digitalio.DigitalInOut(board.IO25)
trig.direction = digitalio.Direction.OUTPUT
echo = digitalio.DigitalInOut(board.IO26)
echo.direction = digitalio.Direction.INPUT

_m1, _m2 = ib.motor_1, ib.motor_2

DIR = 1
t_cambio = 0
barridos = 0
perdido = 0
t_borde = None

MAX_PERDIDO = 1
INTERVALO = 0.15
DIST = 50

COL = {1:(255,100,0),2:(0,255,100),3:(0,100,255)}

def btn():
    e = keys.events.get()
    return e and e.released

def motores(a,b):
    _m1.throttle = a
    _m2.throttle = b

def stop():
    motores(0,0)

def mv(a,b,t,chk_borde=True,chk_rival=False):
    motores(a,b)
    s = time.monotonic()
    while time.monotonic()-s < t:
        if btn(): return "STOP"
        if chk_borde and borde(): return "BORDE"
        if chk_rival and rival(): return "RIVAL"
    return None

def dist():
    trig.value=True
    time.sleep(1e-5)
    trig.value=False
    s=time.monotonic()
    while not echo.value:
        if time.monotonic()-s>0.006:return 999
    i=time.monotonic()
    while echo.value:
        if time.monotonic()-i>0.004:return 999
    return (time.monotonic()-i)*34300/2

def rival():
    return dist()<DIST

def leer():
    return [s.value < thr[i] for i,s in enumerate(sen)]

def borde():
    d=leer()
    if not any(d): return None
    d2=leer()
    d=[d[i] and d2[i] for i in range(4)]
    if not any(d): return None
    if d[1] and d[3] and not d[0] and not d[2]: return "EL"
    if d[0] and d[2] and not d[1] and not d[3]: return "ER"
    if d[0] and d[1]: return "F"
    if d[0]: return "IZ"
    if d[1] or d[3]: return "DE"
    if d[2]: return "IZ"
    return None

def combo(seq):
    for a,b,t in seq:
        if mv(a,b,t)=="STOP": return True
    return False

def escape(dir):
    global t_borde
    ib.pixel=(255,0,255)

    if dir=="EL":
        if combo([(-1,1,0.35),(1,1,0.35),(-1,1,0.3)]): return True
        stop(); return False

    if dir=="ER":
        if combo([(-1,1,0.35),(-1,-1,0.35),(-1,1,0.3)]): return True
        stop(); return False

    now=time.monotonic()
    if t_borde is None: t_borde=now

    if now-t_borde>0.4 and not rival():
        lado=random.choice([1,-1])
        mv(-1*lado,-1*lado,0.35)
        mv(-1,1,0.2)
        t_borde=None
        stop()
        return False

    if mv(1,-1,0.15)=="STOP": return True

    if dir in ("F","IZ"):
        mv(-1,-1,0.45)
    elif dir=="DE":
        mv(-1,-1,0.3)
    else:
        mv(1,1,0.3)

    stop()
    return False

def atacar():
    global DIR,t_cambio,barridos,perdido

    if btn(): return True

    if rival():
        perdido=0
        ib.pixel=(0,255,0)
        if mv(-1,1,0.15)=="STOP": return True
        return False

    perdido+=1

    if perdido<MAX_PERDIDO:
        mv(-1,1,0.05)
        return False

    ib.pixel=(255,165,0)

    now=time.monotonic()
    if now-t_cambio>INTERVALO:
        barridos+=1
        if barridos%3==0: DIR*=-1
        t_cambio=now

    if mv(-1*DIR,-1*DIR,0.25,chk_rival=True)=="RIVAL":
        perdido=0

    return False

def inicio(r):
    sleep(0.2)
    if r==1: mv(-1,1,0.3)
    elif r==2: mv(-1,-1,0.35)
    elif r==3: mv(-1,-1,0.95)
    stop()
    ib.pixel=(0,0,0)

def esperar(color):
    ib.pixel=color
    while True:
        if btn():
            v=[s.value for s in sen]
            ib.pixel=(0,0,0)
            sleep(0.5)
            return v

def calib():
    n=esperar((255,0,0))
    b=esperar((255,255,255))
    for i in range(4):
        thr[i]=(n[i]+b[i])//2
    esperar((0,255,0))
    sleep(0.3)

stop()
r=1

while r<=3:

    for _ in range(r):
        ib.pixel=COL[r]; sleep(0.3)
        ib.pixel=(0,0,0); sleep(0.3)

    calib()
    inicio(r)

    perdido=0
    barridos=0
    DIR=1
    t_cambio=time.monotonic()

    while True:

        if btn():
            stop()
            break

        b=borde()
        if b:
            if escape(b):
                stop()
                break
        else:
            t_borde=None
            if atacar():
                stop()
                break

    r+=1
    sleep(0.5)

stop()
ib.pixel=(200,200,200)