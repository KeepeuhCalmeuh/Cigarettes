# Cigarettes Library Documentation

This library provides the core logic for the Cigarettes P2P messenger. It is designed to be exportable as a shared library (`.so` on Linux, `.dll` on Windows) for use in other applications (GUI, Web, etc.).

not tested yet

## Compilation

### Linux & Windows

To compile the primary executable and the shared library (`libCigarettes.so` / `Cigarettes.dll`), use CMake:

```bash
mkdir build
cd build
cmake ..
make
```

The resulting library will be available in the `build/` directory.

## API Reference

### C++ API

The main interface is the `Cigarettes` class.

```cpp
class Cigarettes {
public:
    Cigarettes(std::string passphrase);
    void add_host(const string& fingerprint, const string& onion, const string& nickname);
    void delete_host(const string& fingerprint);
    // ... other methods
};
```

### C API (for FFI)

The library provides a C-style API for easier integration with other languages (Python, JavaScript, etc.).

| Function | Description |
| --- | --- |
| `create_object(char* passphrase)` | Creates a new Cigarettes instance. |
| `delete_object(Cigarettes* obj)` | Deletes a Cigarettes instance. |
| `tick(Cigarettes* obj)` | Processes network events (must be called in a loop). |
| `receive_chat(Cigarettes* obj, char* buf, int size)` | Returns 1 and fills `buf` if a message is available. |
| `process_command(Cigarettes* obj, char* cmd)` | Processes a command or sends a message. |
| `get_onion(Cigarettes* obj, char* buf, int size)` | Fills `buf` with your onion address. |
| `get_fingerprint(Cigarettes* obj, char* buf, int size)` | Fills `buf` with your fingerprint. |
| `should_keep_running(Cigarettes* obj)` | Returns 1 if the app should continue running. |

## Usage Example (Python)

```python
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
```
