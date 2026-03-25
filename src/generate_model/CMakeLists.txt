cmake_minimum_required(VERSION 3.15)
project(generate_model)

find_package(pybind11 CONFIG REQUIRED)
pybind11_add_module(generate_model ./generateModel/wrapper_bindings.cpp)
install(TARGETS generate_model DESTINATION .)
