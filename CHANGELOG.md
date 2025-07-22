# Changelog – restructuring branch

## [Unreleased] – Preparing merge into Dev

### Added
- Dynamic hosts file path and automatic migration in `hosts.py`. The KnownHostsManager now supports a dynamic path and can migrate existing files automatically. ([de9f4b8])
- New unit tests for core modules and features. ([a2f37d3], [2a5eb3d])
- Modular mixins for connection handling: introduced `connection_base.py`, `connection_file.py`, `connection_handshake.py`, `connection_io.py`, `connection_message.py`, `connection_peer.py` for improved code organization. ([2a5eb3d])
- `command_handlers.py` for better command delegation in the UI. ([2a5eb3d])

### Changed
- Major project restructuring: moved and reorganized core, network, and UI modules for clarity and maintainability. ([557e32c])
- Updated `.gitignore` and cleaned up usage instructions in `README.md`. ([a2f37d3])
- Refactored multiple modules for readability, modularity, and consistency:
  - Commented out debug/logging print statements in `connection_message.py`, `tor_manager.py`, `console_ui.py`, and `main.py` for cleaner output. ([7d45458], [0538c73], [a128aa1])
  - Improved comments and docstrings across connection-related modules for clarity and consistent terminology. ([5a87965])
  - Refactored `P2PConnection` to use mixins, simplifying connection logic. ([2a5eb3d])
  - Updated `ConsoleUI` to delegate command handling and streamline logic. ([2a5eb3d])
  - Enhanced logging in `main.py` and `P2PConnection` for better traceability. ([66d41f0])

### Fixed
- Improved socket closure and peer disconnection handling in `connection.py` and `console_ui.py`. ([57f7731], [8e233e7])
- Enhanced connection management and user experience in `ConsoleUI` (e.g., added wait before accepting new connections, improved disconnection flow). ([23b0dcd], [e196991])
- Improved conversation saving: now creates a history directory and notifies the peer. ([e196991])
- Updated connection messages to include peer nickname and timestamp; improved ping response formatting. ([d5f05c6])

### Removed
- Legacy scripts and test files replaced by new structure and unit tests. ([a2f37d3], [557e32c])
- Redundant imports and methods in `ConsoleUI` and connection modules. ([2a5eb3d])

### Miscellaneous
- Merged remote restructuring branch for synchronization. ([3162384])

---

> This branch delivers a major architectural overhaul, improved network connection management, dynamic hosts file migration, and general codebase cleanup. It sets the foundation for better maintainability and extensibility for future development on the Dev branch.
