FROM ubuntu:24.04

# Avoid timezone prompts during apt install
ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && apt-get install -y \
    build-essential cmake pkg-config \
    libgrpc++-dev protobuf-compiler-grpc protobuf-compiler \
    libssl-dev

WORKDIR /app

# Copy everything into the container
COPY . /app/

# Build the C++ client inside the container
WORKDIR /app/client/build
RUN rm -rf * && cmake .. && make

CMD ["./ota_client"]