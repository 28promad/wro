import ubluetooth
import time

# --- Constants for BLE UART Service ---
_UART_SERVICE_UUID = ubluetooth.UUID("6E400001-B5A3-F393-E0A9-E50E24DCCA9E")
_UART_RX_CHAR_UUID = ubluetooth.UUID("6E400002-B5A3-F393-E0A9-E50E24DCCA9E") # Central writes to this
_UART_TX_CHAR_UUID = ubluetooth.UUID("6E400003-B5A3-F393-E0A9-E50E24DCCA9E") # Central reads from this (Notify)


class BLE_UART:
    def __init__(self, name="databot-uart"):
        self.ble = ubluetooth.BLE()
        
        # *** FIX: Activate BLE hardware immediately ***
        self.ble.active(True)
        self.ble.irq(self._irq) # Register IRQ handler right away
        
        self.name = name
        self.conn_handle = None
        
        # --- Callbacks ---
        self.on_connect_cb = None
        self.on_disconnect_cb = None
        self.on_receive_cb = None
        
        # --- Register GATT Services ---
        uart_service = (
            _UART_SERVICE_UUID,
            (
                (_UART_TX_CHAR_UUID, ubluetooth.FLAG_NOTIFY),
                (_UART_RX_CHAR_UUID, ubluetooth.FLAG_WRITE),
            ),
        )
        
        # Register the service and get characteristic handles
        ( (self.tx_handle, self.rx_handle), ) = self.ble.gatts_register_services((uart_service,))
        
        # Build advertising data after all setup is complete
        self.adv_data = self._build_adv_payload()
        print("BLE UART initialized.")


    def _irq(self, event, data):
        """Internal BLE event handler"""
        
        if event == 1: # _IRQ_CENTRAL_CONNECT
            self.conn_handle, addr_type, addr = data
            print(f"Connected to central: {addr}")
            if self.on_connect_cb:
                self.on_connect_cb()
                
        elif event == 2: # _IRQ_CENTRAL_DISCONNECT
            self.conn_handle = None
            print("Disconnected from central")
            if self.on_disconnect_cb:
                self.on_disconnect_cb()
            self.start_advertising() # Start advertising again
            
        elif event == 3: # _IRQ_GATTS_WRITE
            conn_handle, attr_handle = data
            if attr_handle == self.rx_handle:
                received_data = self.ble.gatts_read(self.rx_handle)
                if self.on_receive_cb:
                    self.on_receive_cb(received_data)


    def _build_adv_payload(self):
        """Builds the advertising payload"""
        adv_payload = bytearray([
            len(self.name) + 1, 0x09, # 0x09 = Complete Local Name
        ]) + self.name.encode()
        return bytes(adv_payload)


    def start_advertising(self):
        """Starts BLE advertising"""
        print(f"Advertising as '{self.name}'...")
        # Advertise every 100ms
        self.ble.gap_advertise(100000, adv_data=self.adv_data)

    def stop_advertising(self):
        self.ble.gap_advertise(None)

    def send(self, data):
        """Sends data to the connected central (if any)"""
        if self.conn_handle is not None:
            if not isinstance(data, bytes):
                data = str(data).encode('utf-8')
            
            try:
                self.ble.gatts_notify(self.conn_handle, self.tx_handle, data)
                return True
            except OSError as e:
                # Catching specific errors is better than a generic print
                print(f"Error sending data: {e}")
                return False
        else:
            # Not an error, just informational
            # print("Not connected, data buffered/dropped.")
            return False

    def is_connected(self):
        return self.conn_handle is not None

    # --- Public methods to set callbacks ---
    
    def on_connect(self, callback):
        self.on_connect_cb = callback

    def on_disconnect(self, callback):
        self.on_disconnect_cb = callback
        
    def on_receive(self, callback):
        self.on_receive_cb = callback

# --- How to use the class ---
if __name__ == "__main__":
    
    print("Starting BLE UART...")
    ble_uart = BLE_UART(name="databot-uart")

    # --- Define our callback functions ---
    
    def handle_rx(data):
        """Called when data is received from the central"""
        print(f"Received: {data.decode('utf-8')}") # Decode bytes to string

    def on_connect():
        print("Central connected!")

    def on_disconnect():
        print("Central disconnected. Re-advertising.")
    
    # --- Register the callbacks ---
    ble_uart.on_receive(handle_rx)
    ble_uart.on_connect(on_connect)
    ble_uart.on_disconnect(on_disconnect)
    
    # Start advertising
    ble_uart.start_advertising()

    # --- Main loop ---
    print("--- Databot Ready ---")
    heartbeat_timer = time.time()
    
    try:
        while True:
            # Send a heartbeat message every 5 seconds
            if time.time() - heartbeat_timer > 5:
                # This is where your sensor data collection/sending would go
                if ble_uart.is_connected():
                    # Keeping the print inside the check avoids bloat when disconnected
                    print("Sending heartbeat...")
                    ble_uart.send("Hello from databot!")
                heartbeat_timer = time.time()
                
            time.sleep_ms(100)
            
    except KeyboardInterrupt:
        # Graceful shutdown
        ble_uart.stop_advertising()
        ble_uart.ble.active(False)
        print("Bluetooth turned off.")