import pygame

pygame.init()

clock = pygame.time.Clock()

def controller(socket):
    joysticks = {}
    while True:
        # Possible joystick events: JOYAXISMOTION, JOYBALLMOTION, JOYBUTTONDOWN,
        # JOYBUTTONUP, JOYHATMOTION, JOYDEVICEADDED, JOYDEVICEREMOVED
        for event in pygame.event.get():
            if event.type == pygame.JOYBUTTONDOWN:
                print(f"Joystick button {event.button} pressed.")
            if event.type == pygame.JOYBUTTONUP:
                print(f"Joystick button {event.button} released.")
            if event.type == pygame.JOYAXISMOTION:
                print("Joystick movement.", event.value, event.axis)
            
            # Handle hotplugging
            if event.type == pygame.JOYDEVICEADDED:
                # This event will be generated when the program starts for every
                # joystick, filling up the list without needing to create them manually.
                joy = pygame.joystick.Joystick(event.device_index)
                joysticks[joy.get_instance_id()] = joy
                print(f"Joystick {joy.get_instance_id()} connencted")
            if event.type == pygame.JOYDEVICEREMOVED:
                del joysticks[event.instance_id]
                print(f"Joystick {event.instance_id} disconnected")

if __name__ == "__main__":
    controller(True)
