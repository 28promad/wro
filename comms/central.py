import asyncio
from bleak import BleakScanner, BleakClient

TARGET_NAME = "databot-uart"
UART_SERVICE_UUID = "6E400001-B5A3-F393-E0A9-E50E24DCCA9E"
UART_RX_CHAR_UUID = "6E400002-B5A3-F393-E0A9-E50E24DCCA9E"
UART_TX_CHAR_UUID = "6E400003-B5A3-F393-E0A9-E50E24DCCA9E"


class BLE_UART_Central:
    def __init__(self):
        self.client = None
        self.rx_char = None
        self.on_receive_cb = None

    def _notification_handler(self, sender, data):
        """Bleak notification callback. Forwards data to user callback if set."""
        if self.on_receive_cb:
            self.on_receive_cb(data)

    def on_receive(self, callback):
        """Set the user callback for received data"""
        self.on_receive_cb = callback

    @property
    def is_connected(self):
        return self.client is not None and self.client.is_connected

    async def connect(self):
        """Scan for the databot by name and connect; starts notifications."""
        print(f"Scanning for '{TARGET_NAME}'...")
        device = await BleakScanner.find_device_by_name(TARGET_NAME)
        
        if device is None:
            print(f"Could not find device with name '{TARGET_NAME}'")
            return False

        print(f"Found databot: {device.name} ({device.address})")
        
        try:
            self.client = BleakClient(device)
            await self.client.connect()
            print("Connected successfully!")
            
            uart_service = self.client.services.get_service(UART_SERVICE_UUID)
            if not uart_service:
                print(f"UART Service {UART_SERVICE_UUID} not found!")
                await self.client.disconnect()
                return False
                
            self.rx_char = uart_service.get_characteristic(UART_RX_CHAR_UUID)
            if not self.rx_char:
                print(f"RX Characteristic {UART_RX_CHAR_UUID} not found!")
                await self.client.disconnect()
                return False

            tx_char = uart_service.get_characteristic(UART_TX_CHAR_UUID)
            if tx_char:
                await self.client.start_notify(tx_char, self._notification_handler)
                print("Started listening for notifications.")
            else:
                print(f"TX Characteristic {UART_TX_CHAR_UUID} not found!")

            return True

        except Exception as e:
            print(f"An error occurred during connection: {e}")
            if self.client:
                await self.client.disconnect()
            self.client = None
            return False

    async def disconnect(self):
        """Disconnect from the device and clear state."""
        if self.client:
            try:
                # Note: stop_notify is often not strictly needed before disconnect
                await self.client.disconnect()
            except Exception as e:
                print(f"Error during disconnect: {e}")
            finally:
                self.client = None
                self.rx_char = None
                print("Disconnected.")

    async def send(self, data):
        """Write bytes to the device's RX characteristic.

        Accepts bytes or convertible types (will be UTF-8 encoded).
        """
        if not self.is_connected:
            print("Not connected, cannot send data.")
            return False
        
        if not isinstance(data, bytes):
            data = str(data).encode('utf-8')
            
        try:
            # 'response=False' is "Write Without Response", which is standard for UART
            await self.client.write_gatt_char(self.rx_char, data, response=False)
            return True
        except Exception as e:
            print(f"Error sending data: {e}")
            return False


async def user_input_loop(central: BLE_UART_Central):
    """Prompt user for input (runs in an asyncio thread) and send to device.

    Type 'exit' to end the loop.
    """
    print("Type a message and press Enter to send. Type 'exit' to quit.")
    while True:
        try:
            msg = await asyncio.to_thread(input, "")
        except EOFError:
            break

        if msg.lower() == 'exit':
            print("Exiting user input loop...")
            break

        if not central.is_connected:
            print("Cannot send, not connected. Waiting for reconnect...")
            continue

        if msg:
            print(f"Sending: '{msg}'")
            await central.send(msg)

async def connection_manager(central: BLE_UART_Central):
    """Keep the BLE connection alive; try to reconnect on failure."""
    while True:
        if not central.is_connected:
            print("Connection lost. Attempting to reconnect...")
            try:
                if await central.connect():
                    print("Reconnected successfully!")
                else:
                    await asyncio.sleep(5)
            except Exception as e:
                print(f"Connection attempt failed with error: {e}")
                print("Retrying in 5 seconds...")
                await asyncio.sleep(5)
        else:
            await asyncio.sleep(1)

# --- REVISED: Main function to orchestrate tasks ---
async def main():
    
    central = BLE_UART_Central()

    def handle_rx(data):
        """Callback invoked when bytes are received from the device.

        Tries to decode as UTF-8; falls back to repr on failure.
        """
        try:
            text = data.decode('utf-8')
        except Exception:
            text = repr(data)
        print(f"\n[Received]: {text}")

    # Register the callback
    central.on_receive(handle_rx)

    print("--- Central Starting ---")
    print("Attempting to connect to databot... (Will auto-reconnect)")

    try:
        # Start the two tasks concurrently
        input_task = asyncio.create_task(user_input_loop(central))
        conn_task = asyncio.create_task(connection_manager(central))
        
        # Wait for either task to finish
        # (user_input_loop will finish if user types 'exit')
        done, pending = await asyncio.wait(
            [input_task, conn_task],
            return_when=asyncio.FIRST_COMPLETED
        )

        # Clean up pending tasks
        for task in pending:
            task.cancel()

    except asyncio.CancelledError:
        print("Program cancelled.")
    except KeyboardInterrupt:
        print("Program stopped by user.")
    finally:
        if central.is_connected:
            print("Disconnecting...")
            await central.disconnect()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nProgram shut down.")