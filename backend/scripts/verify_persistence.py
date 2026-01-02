import os
import sys
import logging

# Add src to path
sys.path.append(os.getcwd())

from src.infrastructure.repositories.persistence_repository import get_persistence_repository

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("verify_persistence")

def test_persistence():
    logger.info("Starting persistence verification...")
    
    repo = get_persistence_repository()
    
    test_key = "test_persistence_key"
    test_data = {
        "status": "success",
        "message": "Persistence is working!",
        "timestamp": "2026-01-02T12:00:00"
    }
    
    # 1. Save data
    logger.info(f"Saving test data with key: {test_key}")
    success = repo.save_training_result(test_key, test_data)
    if not success:
        logger.error("Failed to save data to database")
        return False
        
    # 2. Retrieve data
    logger.info(f"Retrieving data with key: {test_key}")
    retrieved_data = repo.get_training_result(test_key)
    
    if retrieved_data == test_data:
        logger.info("Verification SUCCESS: Saved and retrieved data match!")
        
        # 3. Check last updated
        last_updated = repo.get_last_updated(test_key)
        logger.info(f"Last updated: {last_updated}")
        
        return True
    else:
        logger.error(f"Verification FAILED: Data mismatch. Sent: {test_data}, Received: {retrieved_data}")
        return False

if __name__ == "__main__":
    if test_persistence():
        sys.exit(0)
    else:
        sys.exit(1)
