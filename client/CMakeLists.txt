cmake_minimum_required(VERSION 3.15)
project(AutoGuardClient CXX)

set(CMAKE_CXX_STANDARD 17)

# Find installed dependencies
find_package(Protobuf REQUIRED)
find_package(gRPC REQUIRED)
find_package(OpenSSL REQUIRED)
# Define the executable
add_executable(ota_client 
    src/main.cpp 
    src/partition_manager.cpp
    ${hw_grpc_srcs} 
    ${hw_proto_srcs}
)

# Setup Protobuf/gRPC generation
get_filename_component(ota_proto "../proto/ota.proto" ABSOLUTE)
get_filename_component(proto_path "../proto" ABSOLUTE)

add_custom_command(
  OUTPUT "${CMAKE_CURRENT_BINARY_DIR}/ota.pb.cc"
         "${CMAKE_CURRENT_BINARY_DIR}/ota.pb.h"
         "${CMAKE_CURRENT_BINARY_DIR}/ota.grpc.pb.cc"
         "${CMAKE_CURRENT_BINARY_DIR}/ota.grpc.pb.h"
  COMMAND protoc
    --grpc_out "${CMAKE_CURRENT_BINARY_DIR}"
    --cpp_out "${CMAKE_CURRENT_BINARY_DIR}"
    -I "${proto_path}"
    --plugin=protoc-gen-grpc=`which grpc_cpp_plugin`
    "${ota_proto}"
  DEPENDS "${ota_proto}"
)

# Link everything together
target_sources(ota_client PRIVATE
  "${CMAKE_CURRENT_BINARY_DIR}/ota.pb.cc"
  "${CMAKE_CURRENT_BINARY_DIR}/ota.grpc.pb.cc"
)

target_include_directories(ota_client PRIVATE "${CMAKE_CURRENT_BINARY_DIR}")

target_link_libraries(ota_client PRIVATE
  protobuf::libprotobuf
  gRPC::grpc++
  OpenSSL::SSL
  OpenSSL::Crypto
)

add_executable(test_partition 
    src/test_partition.cpp 
    src/partition_manager.cpp
)