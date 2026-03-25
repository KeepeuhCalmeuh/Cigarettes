// library.cpp
// g++ -shared -fPIC library.cpp -o Cigarettes_lib.so -lssl -lcrypto
#include "library.hpp"

Cigarettes::Cigarettes(std::string passphrase) 
    : config(),
      hostManager(),
      cryptoManager(passphrase),
      network(config.TOR_SERVICE_PORT, config.install_dir, config.socks_port, config.version),
      protocol(&network, &cryptoManager, &hostManager),
      command(&protocol, &hostManager, keep_running)
{
}

void Cigarettes::add_host(const string& fingerprint, const string& onion, const string& nickname) {
    hostManager.upsert_host(fingerprint, onion, nickname);
}

void Cigarettes::delete_host(const string& fingerprint) {
    hostManager.delete_host(fingerprint);
}

void Cigarettes::tick() {
    protocol.tick();
}

bool Cigarettes::receive_chat(string& out_msg) {
    return protocol.receive_chat(out_msg);
}

void Cigarettes::process_command(const string& cmd) {
    command.process(cmd);
}

string Cigarettes::get_onion() const {
    return network.get_onion();
}

string Cigarettes::get_fingerprint() const {
    return cryptoManager.get_fingerprint();
}

void Cigarettes::test_function() {
    // Implement test logic if needed
}

extern "C" {
    CIG_EXPORT Cigarettes* create_object(const char* passphrase) {
        std::string p = passphrase ? passphrase : "";
        return new Cigarettes(p);
    }

    CIG_EXPORT void delete_object(Cigarettes* obj) {
        if (obj) delete obj;
    }

    CIG_EXPORT void add_host(Cigarettes* obj, const char* fingerprint, const char* onion, const char* nickname) {
        if (obj && fingerprint && onion && nickname) {
            obj->add_host(fingerprint, onion, nickname);
        }
    }

    CIG_EXPORT void delete_host(Cigarettes* obj, const char* fingerprint) {
        if (obj && fingerprint) {
            obj->delete_host(fingerprint);
        }
    }

    CIG_EXPORT void tick(Cigarettes* obj) {
        if (obj) obj->tick();
    }

    CIG_EXPORT int receive_chat(Cigarettes* obj, char* out_buf, int buf_size) {
        if (!obj || !out_buf || buf_size <= 0) return 0;
        std::string msg;
        if (obj->receive_chat(msg)) {
            size_t len = msg.copy(out_buf, buf_size - 1);
            out_buf[len] = '\0';
            return 1;
        }
        return 0;
    }

    CIG_EXPORT void process_command(Cigarettes* obj, const char* cmd) {
        if (obj && cmd) {
            obj->process_command(cmd);
        }
    }

    CIG_EXPORT int get_onion(Cigarettes* obj, char* out_buf, int buf_size) {
        if (!obj || !out_buf || buf_size <= 0) return 0;
        std::string onion = obj->get_onion();
        size_t len = onion.copy(out_buf, buf_size - 1);
        out_buf[len] = '\0';
        return 1;
    }

    CIG_EXPORT int get_fingerprint(Cigarettes* obj, char* out_buf, int buf_size) {
        if (!obj || !out_buf || buf_size <= 0) return 0;
        std::string fp = obj->get_fingerprint();
        size_t len = fp.copy(out_buf, buf_size - 1);
        out_buf[len] = '\0';
        return 1;
    }

    CIG_EXPORT int should_keep_running(Cigarettes* obj) {
        return (obj && obj->keep_running) ? 1 : 0;
    }

    CIG_EXPORT void test_function(Cigarettes* obj) {
        if (obj) obj->test_function();
    }
}



