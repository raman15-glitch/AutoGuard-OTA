import grpc
from concurrent import futures
import time
import hashlib
import os
import database 
import traceback

# Cryptography Imports
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.primitives import serialization

import ota_pb2
import ota_pb2_grpc
import logging 

SERVER_PORT = 'localhost:50051'
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
FIRMWARE_PATH = os.path.join(BASE_DIR, "../firmware/v2.0.bin")
PRIVATE_KEY_PATH = os.path.join(BASE_DIR, "../../keys/private.pem")
CHUNK_SIZE = 1024 * 64 

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)


class OTAService(ota_pb2_grpc.FirmwareUpdateServiceServicer):

	def __init__(self):
	    # Load the Private Key into memory when server starts
		with open(PRIVATE_KEY_PATH, "rb") as key_file:
			self.private_key = serialization.load_pem_private_key(
				key_file.read(),
				password=None
			)
		logger.info("[Security] Private Key loaded successfully.")

	def sign_data(self, data):
		"""
		Generates a digital signature for the binary data
		"""
		signature = self.private_key.sign(data,padding.PKCS1v15(),hashes.SHA256())
		return signature.hex() # Send as hex string

	def CheckForUpdate(self, request, context):
		try:
			logger.info(f"CheckForUpdate ping from: {request.device_id} (v{request.current_version})")
			logger.info("Attempting to write to database...")
			database.update_device_status(request.device_id, request.current_version)
			logger.info("Database write successful!")	
			logger.info("Querying active campaigns...")
			target_version = database.get_active_campaign_for_device(request.device_id)
			logger.info(f"Query successful! Target version is: {target_version}")	
			response = ota_pb2.UpdateResponse()

			if target_version and request.current_version != target_version:
				logger.info(f"[Campaign] Matched! {request.device_id} is authorized for v{target_version}")

				with open(FIRMWARE_PATH, "rb") as f:
					firmware_data = f.read()
				raw_hash = hashlib.sha256(firmware_data).hexdigest()
				signature = self.sign_data(firmware_data)
				response.update_available = True
				response.new_version = target_version
				response.release_notes = f"Targeted Rollout: v{target_version}"
				response.severity = ota_pb2.UpdateResponse.OPTIONAL
				response.firmware_sha256 = raw_hash
				response.firmware_signature = signature 
			else:
				logger.info(f"[Campaign] No active updates required for {request.device_id}")
				response.update_available = False
			logger.info("Returning response to client.")
			return response
		except Exception as e:
			
			logger.critical(f"[TRACEBACK in CheckForUpdate]: {e}")
			traceback.print_exc()
			return ota_pb2.UpdateResponse(update_available=False)

	def DownloadUpdate(self, request, context):
		logger.info(f"[Streaming firmware to: {request.device_id}")
		offset = request.resume_offset
		try:
			with open(FIRMWARE_PATH, "rb") as f:
				if offset>0:
					logger.info(f"[Network] Client requested resume from byte {offset}. Seeking ...")
					f.seek(offset)

				chunk_count = 0
				while True:
					chunk = f.read(CHUNK_SIZE)
					if not chunk: break
					yield ota_pb2.FileChunk(data=chunk)

					# 64KB per chunk. 80 chunks = ~5MB.
                	# Only simulate the drop on the FIRST download attempt (when offset is 0)

					chunk_count+=1
					if offset == 0 and chunk_count>80:
						logger.info("[network Simulation] Car entered tunnel! Dropping connection.")
						context.abort(grpc.StatusCode.UNAVAILABLE, "Network connection lost.")
				
			logger.info(f"[Streaming] Finished streaming to {request.device_id}")
		except Exception as e:
			logger.error(f"[Error] {e}")

def serve():
	server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
	ota_pb2_grpc.add_FirmwareUpdateServiceServicer_to_server(OTAService(), server)
	try:
		key_path = os.path.join(BASE_DIR, "../../keys/server.key")
		crt_path = os.path.join(BASE_DIR, "../../keys/server.crt")

		with open(key_path, "rb") as f:
			private_key = f.read()
		with open(crt_path, "rb") as f:
			certificate_chain = f.read()

		server_credentials = grpc.ssl_server_credentials(((private_key, certificate_chain),))
		server.add_secure_port(SERVER_PORT, server_credentials)
		logger.info(f"[Security] TLS/SSL enabled on port {SERVER_PORT}")
        
	except FileNotFoundError:
		logger.critical("Missing SSL certificates. Cannot start secure server.")
		return

	server.start()
	logger.info(f"Secure OTA Server started on {SERVER_PORT}")
	server.wait_for_termination()

if __name__ == '__main__':
	serve()