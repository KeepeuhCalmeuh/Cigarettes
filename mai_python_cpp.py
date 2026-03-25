import ctypes
import time

lib = ctypes.CDLL('./libCigarettes.so')

# Prototypes
lib.create_object.argtypes = [ctypes.c_char_p]
lib.create_object.restype = ctypes.c_void_p
lib.receive_chat.argtypes = [ctypes.c_void_p, ctypes.c_char_p, ctypes.c_int]
lib.process_command.argtypes = [ctypes.c_void_p, ctypes.c_char_p]

obj = lib.create_object(b"my_passphrase")

try:
    while lib.should_keep_running(obj):
        lib.tick(obj)
        
        # Check for messages
        buf = ctypes.create_string_buffer(1024)
        if lib.receive_chat(obj, buf, 1024):
            print(f"Message: {buf.value.decode()}")
            
        time.sleep(0.05)
finally:
    lib.delete_object(obj)