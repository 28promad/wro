import asyncio
import argparse
import json
import sys
from central import BLE_UART_Central


async def run(duration: float):
    central = BLE_UART_Central()
    ready_event = asyncio.Event()

    def on_receive(data: bytes):
        # Try decode
        try:
            text = data.decode('utf-8')
        except Exception:
            text = repr(data)

        # Announce the message
        print(f"From{text}")

        # If we see 'ready', set the event
        if isinstance(text, str) and text.strip().lower() == 'ready':
            ready_event.set()

        # Attempt JSON parse and pretty-print
        try:
            parsed = json.loads(text)
            print(json.dumps(parsed, indent=2))
        except Exception:
            pass

    central.on_receive(on_receive)

    print("Starting scan/connect...")
    if not await central.connect():
        print("Failed to connect to databot.")
        return 1

    try:
        # Send Start
        print("Sending 'Start'")
        await central.send('Start')

        # Wait up to 5s for ready
        try:
            await asyncio.wait_for(ready_event.wait(), timeout=5.0)
            print("Received 'ready' from databot")
        except asyncio.TimeoutError:
            print("Timed out waiting for 'ready' (continuing to listen)")

        # Keep listening for the requested duration
        print(f"Listening for {duration} seconds for notifications...")
        await asyncio.sleep(duration)

    finally:
        if central.is_connected:
            print("Disconnecting...")
            await central.disconnect()

    return 0


def main(argv=None):
    parser = argparse.ArgumentParser(description='Test databot BLE from laptop')
    parser.add_argument('--duration', '-d', type=float, default=20.0,
                        help='How many seconds to listen for notifications (default: 20)')
    args = parser.parse_args(argv)

    try:
        return asyncio.run(run(args.duration))
    except KeyboardInterrupt:
        print('\nInterrupted by user')
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
