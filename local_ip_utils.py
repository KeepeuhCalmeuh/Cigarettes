import socket
import requests

def get_local_ip():
    """Returns the local IP address of the machine."""
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        # We connect to an external address without sending data
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
    except Exception:
        ip = "127.0.0.1"
    finally:
        s.close()
    return ip


def get_public_ip():
    try:
        response = requests.get('https://api.ipify.org?format=text', timeout=5)
        response.raise_for_status()
        return response.text.strip()
    except requests.RequestException as e:
        print("Error retrieving public IP:", e)
        return None
    

if __name__ == "__main__":
    print("Local IP:", get_local_ip())
    print("Public IP:", get_public_ip())