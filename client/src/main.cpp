#include <iostream>
#include <fstream>
#include <memory>
#include <string>
#include <vector>
#include <iomanip>
#include <sstream>
#include <iomanip>

#include <grpcpp/grpcpp.h>
#include <openssl/evp.h>
#include <openssl/pem.h>
#include <openssl/err.h>

#include "ota.grpc.pb.h"

using grpc::Channel;
using grpc::ClientContext;
using grpc::Status;
using ota::FirmwareUpdateService;
using ota::UpdateRequest;
using ota::UpdateResponse;
using ota::DownloadRequest;
using ota::FileChunk;

// --- Security Helper Class ---
class Verifier {
public:
    static std::string CalculateSHA256(const std::string& filepath) {
        std::ifstream file(filepath, std::ios::binary);
        if (!file) return "";

        EVP_MD_CTX* ctx = EVP_MD_CTX_new();
        EVP_DigestInit_ex(ctx, EVP_sha256(), NULL);

        char buffer[4096];
        while (file.read(buffer, sizeof(buffer))) {
            EVP_DigestUpdate(ctx, buffer, file.gcount());
        }
        EVP_DigestUpdate(ctx, buffer, file.gcount());

        unsigned char hash[EVP_MAX_MD_SIZE];
        unsigned int lengthOfHash = 0;
        EVP_DigestFinal_ex(ctx, hash, &lengthOfHash);
        EVP_MD_CTX_free(ctx);

        std::stringstream ss;
        for (unsigned int i = 0; i < lengthOfHash; ++i) {
            ss << std::hex << std::setw(2) << std::setfill('0') << (int)hash[i];
        }
        return ss.str();
    }

    // Existing RSA Signature check
    static bool VerifySignature(const std::string& public_key_path, const std::string& target_file_path, const std::string& signature_hex) {
        // ... (Keep your existing VerifySignature logic exactly as it is) ...
        FILE* pubKeyFile = fopen(public_key_path.c_str(), "r");
        if (!pubKeyFile) return false;
        EVP_PKEY* pubKey = PEM_read_PUBKEY(pubKeyFile, NULL, NULL, NULL);
        fclose(pubKeyFile);
        if (!pubKey) return false;

        EVP_MD_CTX* ctx = EVP_MD_CTX_new();
        EVP_DigestVerifyInit(ctx, NULL, EVP_sha256(), NULL, pubKey);
        
        std::ifstream file(target_file_path, std::ios::binary);
        char buffer[4096];
        while (file.read(buffer, sizeof(buffer))) {
            EVP_DigestVerifyUpdate(ctx, buffer, file.gcount());
        }
        EVP_DigestVerifyUpdate(ctx, buffer, file.gcount()); 

        std::vector<unsigned char> sig_bytes;
        for (size_t i = 0; i < signature_hex.length(); i += 2) {
            unsigned char byte = (unsigned char)strtol(signature_hex.substr(i, 2).c_str(), NULL, 16);
            sig_bytes.push_back(byte);
        }

        int result = EVP_DigestVerifyFinal(ctx, sig_bytes.data(), sig_bytes.size());
        EVP_MD_CTX_free(ctx);
        EVP_PKEY_free(pubKey);
        return result == 1;
    }
};

class OTAClient {
public:
    OTAClient(std::shared_ptr<Channel> channel)
        : stub_(FirmwareUpdateService::NewStub(channel)) {}

    void Run(const std::string& device_id) {
        // Step 1: Check for Update
        UpdateRequest request;
        request.set_device_id(device_id);
        request.set_current_version("1.0");
        
        UpdateResponse response;
        ClientContext context;
        
        Status status = stub_->CheckForUpdate(&context, request, &response);
        if (!status.ok()) {
            std::cout << "[CRITICAL RPC ERROR] Server failed to process request: " << status.error_message() << std::endl;
            return;
        }
        
        if (!response.update_available()) {
            std::cout << "[INFO] No update available." << std::endl;
            return;
        }
        // if (!status.ok() || !response.update_available()) {
        //     std::cout << "[INFO] No update available." << std::endl;
        //     return;
        // }

        std::cout << "[INFO] Found Update v" << response.new_version() << std::endl;
        std::string temp_file = "firmware_v2.tmp";
        std::ifstream in_file(temp_file, std::ios::binary | std::ios::ate);
        uint64_t existing_size = 0; 
        if(in_file.is_open()){
            existing_size = in_file.tellg();
            in_file.close();
            std::cout<< "[Network] Interrupted download found. Resuming from byte "<<existing_size<<"..."<<std::endl;
        }
        else{
            std::cout<<"[Network] Starting fresh download..."<<std::endl;
        }

        // Step 2: Download
        DownloadRequest dl_req;
        dl_req.set_device_id(device_id);
        dl_req.set_version_requested(response.new_version());
        dl_req.set_resume_offset(existing_size);

        ClientContext dl_context;
        FileChunk chunk;
        std::unique_ptr<grpc::ClientReader<FileChunk>> reader(stub_->DownloadUpdate(&dl_context, dl_req));

        std::ios_base::openmode mode = std::ios::binary;
        mode |= (existing_size > 0) ? std::ios::app : std::ios::trunc;
        std::ofstream outfile(temp_file,mode);

        while (reader->Read(&chunk)) {
            outfile.write(chunk.data().c_str(),chunk.data().length());
        }
        outfile.close();

        Status dl_status = reader->Finish();
        if (dl_status.ok()) {
            // std::ifstream check_file(temp_file,std::ios::binary | std::ios::ate);
            // uint64_t final_size = check_file.tellg();
            std::cout << "[INFO] Download Complete. Commencing Dual-Verification..." << std::endl;
            
            std::string calculated_hash = Verifier::CalculateSHA256(temp_file);
            if (calculated_hash != response.firmware_sha256()) {
                std::cout << "[CRITICAL] Hash Mismatch! File corrupted during transfer." << std::endl;
                std::remove(temp_file.c_str());
                return;
            }
            std::cout << "[Security] Checksum valid. File integrity confirmed." << std::endl;

            // Step 3: VERIFY SIGNATURE
            std::string pub_key_path = "../../keys/public.pem"; // Path relative to build folder
            
            std::cout << "[Security] Verifying Signature..." << std::endl;
            bool is_valid = Verifier::VerifySignature(pub_key_path, temp_file, response.firmware_signature());

            if (is_valid) {
                std::cout << "\n[SUCCESS] SIGNATURE MATCHED! Firmware is trusted." << std::endl;
                if(std::rename(temp_file.c_str(),"active_firware.bin") == 0){
                    std::cout<< "[System] partition swapped successfully." << std::endl;
                }
                else{
                    std::cout<< "[Error] Failed to install firmware to acitve partition." << std::endl;
                }
            } else {
                std::cout << "\n[CRITICAL WARNING] SIGNATURE MISMATCH! File may be tampered." << std::endl;
                std::cout << "[Security] Discarding malicious file.\n" << std::endl;
                std::remove(temp_file.c_str());
            }

        }
        else {
            std::cout << "[Network Error] Download interrupted: " << dl_status.error_message() << std::endl;
            std::cout << "[System] Partial file saved to disk. Will resume on next boot." << std::endl;
        }

    }

private:
    std::unique_ptr<FirmwareUpdateService::Stub> stub_;
};

int main() {
    const char* env_dev = std::getenv("DEVICE_ID");
    const char* env_host = std::getenv("SERVER_HOST");
    
    std::string device_id = env_dev ? env_dev : "CAR-123";
    std::string target = env_host ? env_host : "localhost:50051";

    std::cout << "--- Starting ECU for " << device_id << " ---" << std::endl;
    
    std::ifstream cert_file("../../keys/server.crt");
    std::stringstream cert_buffer;
    cert_buffer << cert_file.rdbuf();

    grpc::SslCredentialsOptions ssl_opts;
    ssl_opts.pem_root_certs = cert_buffer.str();
    
    auto channel_creds = grpc::SslCredentials(ssl_opts);

    OTAClient client(grpc::CreateChannel(target, channel_creds));
    client.Run(device_id);
    return 0;
}