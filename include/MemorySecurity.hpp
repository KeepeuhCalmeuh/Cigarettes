#ifndef MEMORYSECURITY_HPP
#define MEMORYSECURITY_HPP

#include <vector>
#include <string>
#include <openssl/crypto.h> // for OPENSSL_cleanse
#include <cstdlib>
#include <new>

template <typename T>
struct SecureAllocator {
    using value_type = T;

    SecureAllocator() noexcept = default;
    template <typename U> SecureAllocator(const SecureAllocator<U>&) noexcept {}

    T* allocate(std::size_t n) {
        if (n > std::size_t(-1) / sizeof(T)) throw std::bad_alloc();
        if (auto p = static_cast<T*>(std::malloc(n * sizeof(T)))) {
            return p;
        }
        throw std::bad_alloc();
    }

    void deallocate(T* p, std::size_t n) noexcept {
        if (p) {
            OPENSSL_cleanse(p, n * sizeof(T));
            std::free(p);
        }
    }
};

template <typename T, typename U>
inline bool operator==(const SecureAllocator<T>&, const SecureAllocator<U>&) { return true; }

template <typename T, typename U>
inline bool operator!=(const SecureAllocator<T>&, const SecureAllocator<U>&) { return false; }

using SecureVector = std::vector<uint8_t, SecureAllocator<uint8_t>>;
using SecureString = std::basic_string<char, std::char_traits<char>, SecureAllocator<char>>;

#endif // MEMORYSECURITY_HPP
