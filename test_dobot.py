from pydobotplus import Dobot
from serial.tools import list_ports
import time

def main():
    print("Finding available ports...")
    available_ports = list_ports.comports()
    if not available_ports:
        print("No serial ports found. Is the Dobot Magician Lite connected to your laptop?")
        return
        
    print(f"Available ports:")
    for port in available_ports:
        print(f" - {port.device} ({port.description})")
    
    # Using the specific port we found for the Dobot
    target_port = '/dev/cu.usbmodem389438CC04312'
    print(f"\nAttempting to connect to Dobot on port: {target_port}")
    
    try:
        # Initialize connection
        device = Dobot(port=target_port)
        print("Connected successfully!")
        
        # Give it a moment to initialize
        time.sleep(1)
        
        # Read the current position
        pose = device.get_pose()
        print(f"Current Pose: {pose}")
        
        # Test movement: Move to a known safe position
        print("Moving to safe starting position (x=200, y=0, z=50)...")
        device.move_to(200, 0, 50, 0, wait=False) 
        time.sleep(2) # wait for the movement to finish
        
        print("Moving down by 30mm (x=200, y=0, z=20)...")
        device.move_to(200, 0, 20, 0, wait=False)
        time.sleep(2)
        
        print("Moving back to starting position...")
        device.move_to(200, 0, 50, 0, wait=False)
        time.sleep(2)
        
        print("Movement test complete.")
        
    except Exception as e:
        print(f"Error occurred: {e}")
        print("\nTroubleshooting tips:")
        print("1. Make sure the Dobot is turned on.")
        print("2. Ensure no other software (like DobotStudio) is currently using the serial port.")
        print("3. You may need to change `target_port` in the code to the correct port from the list above.")
    finally:
        try:
            device.close()
            print("Connection closed.")
        except:
            pass

if __name__ == "__main__":
    main()
