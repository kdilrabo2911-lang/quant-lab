cmake_minimum_required(VERSION 3.15)
project(BacktestAgent CXX)

# C++17 standard
set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

# Optimization flags
set(CMAKE_CXX_FLAGS "${CMAKE_CXX_FLAGS} -O3 -march=native")

# Enable AVX2 if available
include(CheckCXXCompilerFlag)
check_cxx_compiler_flag("-mavx2" COMPILER_SUPPORTS_AVX2)
if(COMPILER_SUPPORTS_AVX2)
    set(CMAKE_CXX_FLAGS "${CMAKE_CXX_FLAGS} -mavx2")
    add_definitions(-D__AVX2__)
endif()

# Include directories
include_directories(${CMAKE_SOURCE_DIR}/cpp/include)

# Core backtester library
add_library(backtester_core
    cpp/src/backtester.cpp
    cpp/src/indicators.cpp
)

# Strategy library
add_library(strategies
    cpp/strategies/ma_dip_buyer2.cpp
)

# Link strategies with backtester core
target_link_libraries(strategies backtester_core)

# CLI executable
add_executable(backtester_cli
    cpp/main.cpp
    cpp/strategies/ma_crossover.cpp
    cpp/strategies/volatilityharvesting.cpp
    cpp/strategies/rsi_reversal_test.cpp
)

# Link CLI with libraries
target_link_libraries(backtester_cli
    backtester_core
    strategies
)

# Install target
install(TARGETS backtester_cli DESTINATION bin)

# Print configuration
message(STATUS "Build type: ${CMAKE_BUILD_TYPE}")
message(STATUS "C++ flags: ${CMAKE_CXX_FLAGS}")
message(STATUS "AVX2 support: ${COMPILER_SUPPORTS_AVX2}")
