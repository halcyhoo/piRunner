#!/usr/bin/python

import RPi.GPIO as GPIO
import threading
import os
import time


processId = os.getpid()
print('ProcessID: ',processId)

#Initialize

GPIO.setwarnings(False)
GPIO.setmode(GPIO.BCM)

#Outputs

statusLED = 27
windowRelay1 = 24
windowRelay2 = 23
cabLightRelay = 26
cargoLightRelay = 25


GPIO.setup(statusLED, GPIO.OUT)
GPIO.setup(windowRelay1, GPIO.OUT)
GPIO.output(windowRelay1, True)
GPIO.setup(windowRelay2, GPIO.OUT)
GPIO.output(windowRelay2, True)
GPIO.setup(cabLightRelay, GPIO.OUT)
GPIO.output(cabLightRelay, True)
GPIO.setup(cargoLightRelay, GPIO.OUT)
GPIO.output(cargoLightRelay, True)

#Inputs

cabLightSwitch = 4
cargoLightSwitch = 5
windowUpSwitch = 6
windowDownSwitch = 7
windowUpPosition = 8
windowDownPosition = 9
windowUpRemote = 10
windowDownRemote = 12
cabLightRemote = 13
cargoLightRemote = 11


GPIO.setup(cabLightSwitch, GPIO.IN, GPIO.PUD_UP)
GPIO.setup(cargoLightSwitch, GPIO.IN, GPIO.PUD_UP)
GPIO.setup(windowUpSwitch, GPIO.IN, GPIO.PUD_UP)
GPIO.setup(windowDownSwitch, GPIO.IN, GPIO.PUD_UP)
GPIO.setup(windowUpPosition, GPIO.IN, GPIO.PUD_UP)
GPIO.setup(windowDownPosition, GPIO.IN, GPIO.PUD_UP)
GPIO.setup(windowUpRemote, GPIO.IN, GPIO.PUD_UP)
GPIO.setup(windowDownRemote, GPIO.IN, GPIO.PUD_UP)
GPIO.setup(cabLightRemote, GPIO.IN, GPIO.PUD_UP)
GPIO.setup(cargoLightRemote, GPIO.IN, GPIO.PUD_UP)

states = {
    "windowUpSwitch": False,
    "windowUpSwitchDouble": False,
    "windowDownSwitch": False,
    "windowDownSwitchDouble": False,
    "windowUpPosition": False if (GPIO.input(windowUpPosition) == 0) else True,
    "windowDownPosition": False if (GPIO.input(windowDownPosition) == 0) else True,
    "cabLight": False,
    "cargoLight": False,
}

buttonTimers = {
    "windowDownSwitch": time.perf_counter(),
    "windowUpSwitch": time.perf_counter(),
    "cabLight": time.perf_counter(),
    "cargoLight": time.perf_counter(),
}

doubleClickTime = 1


class ButtonHandler(threading.Thread):
    def __init__(self, pin, edge, bouncetime, buttonId, func, *args):
        super().__init__(daemon=True)

        self.edge = edge
        self.func = func
        self.pin = pin
        self.args = args
        self.bouncetime = float(bouncetime)/1000
        self.lastpinval = GPIO.input(self.pin)
        self.buttonId = buttonId
        self.lock = threading.Lock()

    def __call__(self, *args):
        if not self.lock.acquire(blocking=False):
            return
        t = threading.Timer(self.bouncetime, self.read, args=self.args)
        t.start()

    def read(self, *args):
        pinval = GPIO.input(self.pin)
        if (
                ((pinval == GPIO.LOW and self.lastpinval == GPIO.HIGH) and
                 (self.edge in ['rising', 'both'])) or
                ((pinval == GPIO.HIGH and self.lastpinval == GPIO.LOW) and
                 (self.edge in ['falling', 'both']))
        ):
            self.func(*args)

        if(pinval == GPIO.LOW and self.lastpinval == GPIO.HIGH and self.buttonId in buttonTimers):
            if((time.perf_counter() - buttonTimers[self.buttonId]) <= doubleClickTime):
                states[self.buttonId + "Double"] = True
            else:
                states[self.buttonId + "Double"] = False
            buttonTimers[self.buttonId] = time.perf_counter()

        self.lastpinval = pinval
        self.lock.release()

def setupToggleInput(pin, buttonId, func, *args):
    cb = ButtonHandler(pin, 'rising', 100, buttonId, func, *args)
    cb.start()
    GPIO.add_event_detect(pin, GPIO.BOTH, callback=cb)

def setupMomentaryInput(pin, buttonId, func, *args):
    cb = ButtonHandler(pin, 'both', 100, buttonId, func, *args)
    cb.start()
    GPIO.add_event_detect(pin, GPIO.BOTH, callback=cb)

def momentaryController(id, pin):
    if states[id]==True and GPIO.input(pin) == 1:
        states[id]=False
    elif states[id]==False and GPIO.input(pin) == 0:
        states[id]=True

def toggleController(id, pin):
    if states[id] == False:
        states[id] = True
    else:
        states[id] = False

def windowDownPositionController(channel):
    if states["windowDownPosition"]==True and GPIO.input(windowDownPosition) == 1:
        states["windowDownPosition"]=False
    elif states["windowDownPosition"]==False and GPIO.input(windowDownPosition) == 0:
        states["windowDownPosition"]=True

def windowUpPositionController(channel):
    if states["windowUpPosition"]==True and GPIO.input(windowUpPosition) == 1:
        states["windowUpPosition"]=False
    elif states["windowUpPosition"]==False and GPIO.input(windowUpPosition) == 0:
        states["windowUpPosition"]=True

GPIO.add_event_detect(windowDownPosition, GPIO.BOTH, callback=windowDownPositionController )
GPIO.add_event_detect(windowUpPosition, GPIO.BOTH, callback=windowUpPositionController )

setupToggleInput(cabLightSwitch, "cabLight", toggleController, "cabLight", cabLightSwitch);
setupToggleInput(cabLightRemote, "cabLight", toggleController, "cabLight", cabLightRemote);

setupToggleInput(cargoLightSwitch, "cargoLight", toggleController, "cargoLight", cargoLightSwitch);
setupToggleInput(cargoLightRemote, "cargoLight", toggleController, "cargoLight", cargoLightRemote);

setupMomentaryInput(windowUpRemote, "windowUpSwitch", momentaryController, "windowUpSwitch", windowUpRemote);
setupMomentaryInput(windowDownRemote, "windowDownSwitch", momentaryController, "windowDownSwitch", windowDownRemote);

setupMomentaryInput(windowUpSwitch, "windowUpSwitch", momentaryController, "windowUpSwitch", windowUpSwitch);
setupMomentaryInput(windowDownSwitch, "windowDownSwitch", momentaryController, "windowDownSwitch", windowDownSwitch);

try:
    while True:
        GPIO.output(statusLED, True)

        if states["cabLight"] == True:
            GPIO.output(cabLightRelay, False)
        else:
            GPIO.output(cabLightRelay, True)

        if states["cargoLight"] == True:
            GPIO.output(cargoLightRelay, False)
        else:
            GPIO.output(cargoLightRelay, True)

        #Control Window Relays
        if (states["windowUpSwitch"] == True and states["windowDownSwitch"] == True) or \
            (states["windowUpSwitch"] == True and states["windowDownSwitchDouble"] == True) or \
            (states["windowUpSwitchDouble"] == True and states["windowDownSwitch"] == True) or \
            (states["windowUpSwitchDouble"] == True and states["windowDownSwitchDouble"] == True):
                GPIO.output(windowRelay1, True)
                GPIO.output(windowRelay2, True)
                states["windowDownSwitch"] = False
                states["windowUpSwitchDouble"] = False
                states["windowUpSwitch"] = False
                states["windowDownSwitchDouble"] = False
        else:
            if (states["windowDownSwitch"] or states["windowDownSwitchDouble"]) and not states["windowDownPosition"]:
                GPIO.output(windowRelay1, False)
            elif (states["windowDownSwitch"] or states["windowDownSwitchDouble"]) and states["windowDownPosition"]:
                GPIO.output(windowRelay1, True)
                states["windowDownSwitch"] = False
                states["windowDownSwitchDouble"] = False
            else:
                GPIO.output(windowRelay1, True)

            if (states["windowUpSwitch"] or states["windowUpSwitchDouble"]) and not states["windowUpPosition"]:
                GPIO.output(windowRelay2, False)
            elif (states["windowUpSwitch"] or states["windowUpSwitchDouble"]) and states["windowUpPosition"]:
                states["windowUpSwitchDouble"] = False
                states["windowUpSwitch"] = False
                GPIO.output(windowRelay2, True)
            else:
                GPIO.output(windowRelay2, True)

        #End Control Window Relays
except KeyboardInterrupt:
    GPIO.cleanup()
GPIO.cleanup()
