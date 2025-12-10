from pymongo import MongoClient
from pymongo.errors import (
    PyMongoError, 
    DuplicateKeyError, 
    ConnectionFailure,
    OperationFailure
)
from dotenv import load_dotenv
from typing import Dict, List, Optional, Any, Union
from datetime import datetime
import os
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ResumeDatabase:
    """
    Professional MongoDB CRUD API for Resume Management
    
    Provides robust database operations with error handling,
    validation, and comprehensive CRUD functionality.
    """
    
    def __init__(self, db_name: str = 'ResumeAnalyzer', collection_name: str = 'resumes'):
        """
        Initialize database connection
        
        Args:
            db_name: Name of the MongoDB database
            collection_name: Name of the collection to use
        """
        load_dotenv()
        self.mongo_uri = os.getenv("MONGO_URI")
        
        if not self.mongo_uri:
            raise ValueError("MONGO_URI not found in environment variables")
        
        try:
            self.client = MongoClient(self.mongo_uri, serverSelectionTimeoutMS=5000)
            # Test connection
            self.client.admin.command('ping')
            self.db = self.client[db_name]
            self.collection = self.db[collection_name]
            logger.info(f"Successfully connected to MongoDB: {db_name}.{collection_name}")
        except ConnectionFailure as e:
            logger.error(f"Failed to connect to MongoDB: {e}")
            raise
    
    def insert_resume(self, resume: Dict[str, Any]) -> Dict[str, Any]:
        """
        Insert a new resume into the database
        
        Args:
            resume: Dictionary containing resume data
            
        Returns:
            Dictionary with success status and inserted ID
            
        Raises:
            ValueError: If resume data is invalid
            DuplicateKeyError: If resume with same ID already exists
        """
        if not resume:
            raise ValueError("Resume data cannot be empty")
        
        # Add metadata
        if '_id' not in resume:
            resume['_id'] = self._generate_resume_id()
        
        resume['created_at'] = datetime.utcnow()
        resume['updated_at'] = datetime.utcnow()
        
        try:
            # Check if resume already exists
            if self.collection.find_one({'_id': resume['_id']}):
                raise DuplicateKeyError(f"Resume with ID {resume['_id']} already exists")
            
            result = self.collection.insert_one(resume)
            logger.info(f"Resume inserted successfully with ID: {result.inserted_id}")
            
            return {
                'success': True,
                'id': str(result.inserted_id),
                'message': 'Resume inserted successfully'
            }
        except DuplicateKeyError as e:
            logger.error(f"Duplicate resume ID: {e}")
            raise
        except PyMongoError as e:
            logger.error(f"Database error during insert: {e}")
            raise
    
    def get_resume(self, resume_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve a resume by ID
        
        Args:
            resume_id: The unique identifier of the resume
            
        Returns:
            Resume dictionary if found, None otherwise
        """
        try:
            resume = self.collection.find_one({'_id': resume_id})
            if resume:
                logger.info(f"Resume found: {resume_id}")
            else:
                logger.warning(f"Resume not found: {resume_id}")
            return resume
        except PyMongoError as e:
            logger.error(f"Database error during retrieval: {e}")
            raise
    
    def get_all_resumes(self, limit: int = 100, skip: int = 0, 
                       sort_by: str = 'created_at', ascending: bool = False) -> List[Dict[str, Any]]:
        """
        Retrieve all resumes with pagination and sorting
        
        Args:
            limit: Maximum number of resumes to return
            skip: Number of resumes to skip
            sort_by: Field to sort by
            ascending: Sort order (True for ascending, False for descending)
            
        Returns:
            List of resume dictionaries
        """
        try:
            sort_order = 1 if ascending else -1
            resumes = list(self.collection.find().sort(sort_by, sort_order).skip(skip).limit(limit))
            logger.info(f"Retrieved {len(resumes)} resumes")
            return resumes
        except PyMongoError as e:
            logger.error(f"Database error during retrieval: {e}")
            raise
    
    def update_resume(self, resume_id: str, update_data: Dict[str, Any], 
                     upsert: bool = False) -> Dict[str, Any]:
        """
        Update an existing resume
        
        Args:
            resume_id: The unique identifier of the resume
            update_data: Dictionary containing fields to update
            upsert: If True, insert the document if it doesn't exist
            
        Returns:
            Dictionary with success status and modified count
        """
        if not update_data:
            raise ValueError("Update data cannot be empty")
        
        # Add updated timestamp
        update_data['updated_at'] = datetime.utcnow()
        
        try:
            result = self.collection.update_one(
                {'_id': resume_id},
                {'$set': update_data},
                upsert=upsert
            )
            
            if result.matched_count == 0 and not upsert:
                logger.warning(f"Resume not found for update: {resume_id}")
                return {
                    'success': False,
                    'message': 'Resume not found',
                    'matched_count': 0,
                    'modified_count': 0
                }
            
            logger.info(f"Resume updated: {resume_id}, Modified: {result.modified_count}")
            return {
                'success': True,
                'message': 'Resume updated successfully',
                'matched_count': result.matched_count,
                'modified_count': result.modified_count,
                'upserted_id': str(result.upserted_id) if result.upserted_id else None
            }
        except PyMongoError as e:
            logger.error(f"Database error during update: {e}")
            raise
    
    def delete_resume(self, resume_id: str) -> Dict[str, Any]:
        """
        Delete a resume by ID
        
        Args:
            resume_id: The unique identifier of the resume
            
        Returns:
            Dictionary with success status and deleted count
        """
        try:
            result = self.collection.delete_one({'_id': resume_id})
            
            if result.deleted_count == 0:
                logger.warning(f"Resume not found for deletion: {resume_id}")
                return {
                    'success': False,
                    'message': 'Resume not found',
                    'deleted_count': 0
                }
            
            logger.info(f"Resume deleted: {resume_id}")
            return {
                'success': True,
                'message': 'Resume deleted successfully',
                'deleted_count': result.deleted_count
            }
        except PyMongoError as e:
            logger.error(f"Database error during deletion: {e}")
            raise
    
    def search_resumes(self, query: Dict[str, Any], limit: int = 50) -> List[Dict[str, Any]]:
        """
        Search resumes based on custom query
        
        Args:
            query: MongoDB query dictionary
            limit: Maximum number of results to return
            
        Returns:
            List of matching resume dictionaries
        """
        try:
            resumes = list(self.collection.find(query).limit(limit))
            logger.info(f"Search returned {len(resumes)} results")
            return resumes
        except PyMongoError as e:
            logger.error(f"Database error during search: {e}")
            raise
    
    def add_ranking(self, resume_id: str, ranking_data: Dict[str, Any], 
                   job_description: str) -> Dict[str, Any]:
        """
        Add ranking information to a resume
        
        Args:
            resume_id: The unique identifier of the resume
            ranking_data: Dictionary containing ranking scores and justifications
            job_description: The job description used for ranking
            
        Returns:
            Dictionary with success status
        """
        ranking_entry = {
            'ranking': ranking_data,
            'job_description': job_description,
            'ranked_at': datetime.utcnow()
        }
        
        try:
            result = self.collection.update_one(
                {'_id': resume_id},
                {
                    '$push': {'rankings': ranking_entry},
                    '$set': {'updated_at': datetime.utcnow()}
                }
            )
            
            if result.matched_count == 0:
                logger.warning(f"Resume not found for adding ranking: {resume_id}")
                return {
                    'success': False,
                    'message': 'Resume not found'
                }
            
            logger.info(f"Ranking added to resume: {resume_id}")
            return {
                'success': True,
                'message': 'Ranking added successfully'
            }
        except PyMongoError as e:
            logger.error(f"Database error during ranking addition: {e}")
            raise
    
    def get_resume_count(self, query: Optional[Dict[str, Any]] = None) -> int:
        """
        Get count of resumes matching query
        
        Args:
            query: Optional MongoDB query dictionary
            
        Returns:
            Count of matching documents
        """
        try:
            query = query or {}
            count = self.collection.count_documents(query)
            return count
        except PyMongoError as e:
            logger.error(f"Database error during count: {e}")
            raise
    
    def bulk_insert_resumes(self, resumes: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Insert multiple resumes at once
        
        Args:
            resumes: List of resume dictionaries
            
        Returns:
            Dictionary with success status and inserted IDs
        """
        if not resumes:
            raise ValueError("Resume list cannot be empty")
        
        # Add metadata to all resumes
        for resume in resumes:
            if '_id' not in resume:
                resume['_id'] = self._generate_resume_id()
            resume['created_at'] = datetime.utcnow()
            resume['updated_at'] = datetime.utcnow()
        
        try:
            result = self.collection.insert_many(resumes, ordered=False)
            logger.info(f"Bulk insert: {len(result.inserted_ids)} resumes inserted")
            
            return {
                'success': True,
                'message': f'{len(result.inserted_ids)} resumes inserted',
                'inserted_ids': [str(id) for id in result.inserted_ids]
            }
        except PyMongoError as e:
            logger.error(f"Database error during bulk insert: {e}")
            raise
    
    def _generate_resume_id(self) -> str:
        """Generate a unique resume ID"""
        from bson import ObjectId
        return str(ObjectId())
    
    def close_connection(self):
        """Close the MongoDB connection"""
        if self.client:
            self.client.close()
            logger.info("MongoDB connection closed")


# Legacy function support (for backward compatibility)
def load_mongodb():
    """Legacy function to load MongoDB collection"""
    db = ResumeDatabase()
    return db.collection


def insert_resume(resume: dict, collection=None):
    """Legacy function to insert resume"""
    if collection:
        # Direct collection usage
        if '_id' in resume and collection.find_one({'_id': resume['_id']}):
            raise DuplicateKeyError(f"Resume with ID {resume['_id']} already exists")
        resume['created_at'] = datetime.utcnow()
        resume['updated_at'] = datetime.utcnow()
        collection.insert_one(resume)
    else:
        # Use new API
        db = ResumeDatabase()
        db.insert_resume(resume)


def get_resume(resume_id: str, collection=None):
    """Legacy function to get resume"""
    if collection:
        return collection.find_one({'_id': resume_id})
    else:
        db = ResumeDatabase()
        return db.get_resume(resume_id)


def update_resume(resume_id: str, resume: dict, collection=None):
    """Legacy function to update resume"""
    if collection:
        resume['updated_at'] = datetime.utcnow()
        collection.update_one({'_id': resume_id}, {'$set': resume})
    else:
        db = ResumeDatabase()
        db.update_resume(resume_id, resume)


def delete_resume(resume_id: str, collection=None):
    """Legacy function to delete resume"""
    if collection:
        collection.delete_one({'_id': resume_id})
    else:
        db = ResumeDatabase()
        db.delete_resume(resume_id)
