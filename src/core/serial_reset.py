import serial
import time

def reset_serial_device(port_path):
    """
    Toggles the DTR and RTS lines of a serial port to trigger a hardware reset
    on connected microcontrollers (e.g. Arduino, ESP32).
    Returns (success: bool, message: str).
    """
    ser = None
    try:
        # Open the serial port
        ser = serial.Serial()
        ser.port = port_path
        ser.timeout = 1
        ser.write_timeout = 1
        ser.open()
        
        # 1. Pull both lines inactive
        ser.dtr = False
        ser.rts = False
        time.sleep(0.1)
        
        # 2. Trigger reset pulse (DTR/RTS active)
        ser.dtr = True
        ser.rts = True
        time.sleep(0.2)
        
        # 3. Release reset (DTR/RTS inactive)
        ser.dtr = False
        ser.rts = False
        
        return True, "Reset sequence completed."
    except Exception as e:
        return False, str(e)
    finally:
        if ser and ser.is_open:
            try:
                ser.close()
            except Exception:
                pass
