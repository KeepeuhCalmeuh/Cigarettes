# Changelog – restructuring branch

### Added
- Dynamic hosts file path and automatic migration in `hosts.py`. The KnownHostsManager now supports a dynamic path and can migrate existing files automatically. 
- Modular mixins for connection handling: introduced `connection_base.py`, `connection_file.py`, `connection_handshake.py`, `connection_io.py`, `connection_message.py`, `connection_peer.py` for improved code organization. 
- `command_handlers.py` for better command delegation in the UI. 
- Method in `hosts.py` to retrieve all fingerprints from known hosts, enhancing host management functionality.
- We now root via TOR (automatic installation).
- The private authentification key is now cryptable with a passphrase.
- We can transfer files.
- And a lot more features.

### Changed
- Major project restructuring: moved and reorganized core, network, and UI modules for clarity and maintainability. 
- Refactored multiple modules for readability, modularity, and consistency:
  - Commented out debug/logging print statements in `connection_message.py`, `tor_manager.py`, `console_ui.py`, and `main.py` for cleaner output.
  - Improved comments and docstrings across connection-related modules for clarity and consistent terminology.
  - Refactored `P2PConnection` to use mixins, simplifying connection logic.
  - Updated `ConsoleUI` to delegate command handling and streamline logic. 
  - Enhanced logging in `main.py` and `P2PConnection` for better traceability. 
  - `main.py` now prints the .onion address in a highlighted format for better visibility. 
  - `console_ui.py` prints startup information in a highlighted format for improved user experience.
  - `connection_peer.py` now includes timestamps in connection attempt messages for better context.
  - `connection_handshake.py` verifies peer identity against known fingerprints and provides clearer feedback. 

### Fixed
- Improved socket closure and peer disconnection handling in `connection.py` and `console_ui.py`.
- Enhanced connection management and user experience in `ConsoleUI` (e.g., added wait before accepting new connections, improved disconnection flow).
- Improved conversation saving: now creates a history directory and notifies the peer. 
- Updated connection messages to include peer nickname and timestamp; improved ping response formatting.
- `connection_message.py` now notifies when a peer disconnects, improving user awareness. 

### Removed
- Legacy scripts and test files replaced by new structure and unit tests.
- Redundant imports and methods in `ConsoleUI` and connection modules. 
---

> This branch delivers a major architectural overhaul, improved network connection management, dynamic hosts file migration, and general codebase cleanup. It sets the foundation for better maintainability and extensibility for future development on the Dev branch.
