# ✅ TODO - Cigarettes

Tracking planned improvements to the Cigarettes app.

---

## Needed to release
- [ ] Release with a compiled version and a verification of the hash.


## 🔐 Security

- [ ] Add automatic session expiration after inactivity
- [ ] Add a temporary password (OTP-like) to strengthen connections
- [ ] Support for post-quantum signatures (e.g., Dilithium)
- [ ] "Ephemeral message" option (self-destructs after X minutes)

---

## 💬 Messaging Features

- [ ] Persistent history between sessions
- [ ] Encrypted file transfer (optional)
- [ ] Message compression (e.g., gzip or zlib)
- [ ] Add Group Features

---

## 🌐 Connectivity

- [ ] Automatic reconnection after loss of Connection
- [ ] Peer-to-peer latency ping
- [ ] Automatic peer discovery on the local network (mDNS or UDP broadcast)
- [ ] Connection via Tor or SOCKS5 proxy

---

## 🧭 Interface and user experience

- [ ] Alias ​​system for commands in a configuration file
- [ ] Display session stats: number of messages, duration, volume exchanged
- [ ] Add a more readable prompt with color/nickname
- [ ] Verbose/debug mode with detailed logs

---

## 🛠️ Deployment and modularity

- [ ] Configuration file (`.ini`, `.json` or `.yaml`)
- [ ] Plugin support: adding commands from `plugins/`
- [ ] Creating an `.exe` installer or `pip` package

---

## 🎓 Educational / Bonus

- [ ] MITM attack detection training mode
- [ ] Attacker simulation mode (MITM/Key spoofing) with warning
- [ ] Addition of a cryptographic mini-game (encrypted exchange challenge)

---

## 🧪 Testing & Reliability

- [ ] Add unit tests for encryption and key management
- [ ] Automated tests for commands (`/connect`, `/rename`, etc.)
- [ ] Validation of key and fingerprint formats
- [ ] Network testing between multiple machines with logs

---

**Last updated:** `10/07/25`