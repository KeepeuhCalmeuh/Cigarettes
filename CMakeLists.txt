cmake_minimum_required(VERSION 3.10)
if(POLICY CMP0135)
  cmake_policy(SET CMP0135 NEW)
endif()

project(Cigarettes VERSION 1.0)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED True)

# Directories
set(INCLUDE_DIR ${CMAKE_SOURCE_DIR}/include)
set(SRC_DIR ${CMAKE_SOURCE_DIR}/src)
set(API_SRC_DIR ${SRC_DIR}/api)

# Include directories
include_directories(${INCLUDE_DIR})
include_directories(${CMAKE_SOURCE_DIR}/include/api)

# Source files (excluding main.cpp and api/library.cpp for library support)
set(CORE_SOURCES
    ${SRC_DIR}/CommandHandler.cpp
    ${SRC_DIR}/ProtocolHandler.cpp
    ${SRC_DIR}/libConfig.cpp
    ${SRC_DIR}/libCrypto.cpp
    ${SRC_DIR}/libCryptoSession.cpp
    ${SRC_DIR}/libHost.cpp
    ${SRC_DIR}/libNetwork.cpp
    ${SRC_DIR}/torManager.cpp
)

# Common dependencies
find_package(OpenSSL REQUIRED)
# If you are using additional libs (e.g., pthread, curl, etc.), add them here
set(LIBS OpenSSL::SSL OpenSSL::Crypto pthread)

include(FetchContent)
FetchContent_Declare(json
  URL https://github.com/nlohmann/json/releases/download/v3.11.3/json.tar.xz
)
FetchContent_MakeAvailable(json)

# -----------------------------------------------------------------------------
# 1. Main Executable (Cigarettes)
# -----------------------------------------------------------------------------
add_executable(Cigarettes
    ${SRC_DIR}/main.cpp
    ${CORE_SOURCES}
)

target_link_libraries(Cigarettes PRIVATE ${LIBS} nlohmann_json::nlohmann_json)

# -----------------------------------------------------------------------------
# 2. Shared Library (libCigarettes.so)
# -----------------------------------------------------------------------------
add_library(Cigarettes_lib SHARED
    ${API_SRC_DIR}/library.cpp
    ${CORE_SOURCES}
)
set_target_properties(Cigarettes_lib PROPERTIES OUTPUT_NAME "Cigarettes")

target_link_libraries(Cigarettes_lib PRIVATE ${LIBS} nlohmann_json::nlohmann_json)

# Set output directory for library
set_target_properties(Cigarettes_lib PROPERTIES
    LIBRARY_OUTPUT_DIRECTORY ${CMAKE_BINARY_DIR}
)
