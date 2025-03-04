import serial
import time
import threading

class SBusTransmitter:
    def __init__(self, port='/dev/serial0', update_rate=0.01):
        # Initialize the serial port with nonblocking timeout.
        self.ser = serial.Serial(
            port=port,
            baudrate=100000,
            bytesize=serial.EIGHTBITS,
            parity=serial.PARITY_EVEN,
            stopbits=serial.STOPBITS_TWO,
            timeout=0  # nonblocking mode
        )
        self.update_rate = update_rate  # seconds (e.g., 0.01 for 100Hz)
        self.running = False
        self.thread = None
        # Initial gamepad state with values in the range [-1, 1]. 
        # 0 is the neutral (center) value.
        self.gamepad_input = {
            'roll': 0.0,
            'pitch': 0.0,
            'yaw': 0.0,
            'throttle': 0.0,
            # Add additional controls as needed.
        }
        # Calibration parameters: mapping [-1, 1] to [min_val, max_val]
        self.min_val = 0
        self.max_val = 2047

    def calibrate_value(self, val):
        """
        Map a gamepad value in [-1,1] to an SBUS channel value.
        Here, -1 -> self.min_val, 0 -> mid value, 1 -> self.max_val.
        """
        # Clamp the value to [-1,1]
        if val < -1:
            val = -1
        elif val > 1:
            val = 1
        # Linear mapping
        return int(((val + 1) / 2) * (self.max_val - self.min_val) + self.min_val)

    def pack_sbus(self, channels, flags=0):
        """
        Pack 16 channels (11-bit each) into a 25-byte SBUS frame.
        """
        bitstream = 0
        bits_filled = 0
        for ch in channels:
            bitstream |= (ch & 0x7FF) << bits_filled
            bits_filled += 11

        frame = bytearray(25)
        frame[0] = 0x0F  # start byte
        for i in range(22):
            frame[i+1] = (bitstream >> (i * 8)) & 0xFF
        frame[23] = flags  # flags byte (e.g., for failsafe)
        frame[24] = 0x00   # end byte
        return frame

    def gamepad_to_sbus_channels(self):
        """
        Convert the gamepad input values (in [-1,1]) into a list of 16 SBUS channel values.
        """
        channels = [0] * 16
        channels[0] = self.calibrate_value(self.gamepad_input.get('roll', 0.0))
        channels[1] = self.calibrate_value(self.gamepad_input.get('pitch', 0.0))
        channels[2] = self.calibrate_value(self.gamepad_input.get('yaw', 0.0))
        channels[3] = self.calibrate_value(self.gamepad_input.get('throttle', 0.0))
        # For unused channels, use the neutral value (0.0 -> center value)
        for i in range(4, 16):
            channels[i] = self.calibrate_value(0.0)
        return channels

    def update_gamepad(self, gamepad_data):
        """
        Update gamepad command values. This method can be called
        from another thread or function to change the SBUS output.
        The input values should be between -1 and 1.
        """
        self.gamepad_input.update(gamepad_data)

    def transmitter_loop(self):
        """
        Background loop that continuously sends SBUS frames.
        """
        while self.running:
            channels = self.gamepad_to_sbus_channels()
            frame = self.pack_sbus(channels)
            self.ser.write(frame)
            time.sleep(self.update_rate)

    def start(self):
        """
        Start the SBUS transmitter loop in a nonblocking background thread.
        """
        if not self.running:
            self.running = True
            self.thread = threading.Thread(target=self.transmitter_loop, daemon=True)
            self.thread.start()

    def stop(self):
        """
        Stop the transmitter loop and close the serial connection.
        """
        self.running = False
        if self.thread:
            self.thread.join()
        self.ser.close()
