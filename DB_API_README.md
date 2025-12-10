# Professional MongoDB CRUD API for Resume Management

A robust, production-ready MongoDB CRUD API with comprehensive error handling, logging, and type hints.

## 🌟 Features

- **Object-Oriented Design**: Clean class-based architecture
- **Comprehensive Error Handling**: Proper exception handling for all database operations
- **Type Hints**: Full typing support for better IDE integration
- **Logging**: Built-in logging for debugging and monitoring
- **Automatic Timestamps**: Automatic `created_at` and `updated_at` tracking
- **Connection Management**: Proper connection lifecycle management
- **Pagination & Sorting**: Built-in pagination support for large datasets
- **Search Capabilities**: Flexible MongoDB query support
- **Bulk Operations**: Efficient bulk insert operations
- **Ranking System**: Built-in support for resume ranking
- **Backward Compatible**: Legacy function support for existing code

## 📦 Installation

```bash
pip install pymongo python-dotenv
```

## ⚙️ Configuration

Create a `.env` file in your project root:

```env
MONGO_URI=mongodb://localhost:27017/
# or for MongoDB Atlas:
# MONGO_URI=mongodb+srv://username:password@cluster.mongodb.net/
```

## 🚀 Quick Start

### Basic Usage

```python
from Db import ResumeDatabase

# Initialize database
db = ResumeDatabase()

# Insert a resume
resume = {
    'name': 'John Doe',
    'skills': ['Python', 'JavaScript'],
    'experience': [],
    'education': [],
    'projects': [],
    'extras': []
}

result = db.insert_resume(resume)
print(result)  # {'success': True, 'id': '...', 'message': 'Resume inserted successfully'}

# Get a resume
resume = db.get_resume(result['id'])

# Update a resume
db.update_resume(result['id'], {'skills': ['Python', 'JavaScript', 'React']})

# Delete a resume
db.delete_resume(result['id'])

# Close connection
db.close_connection()
```

### Context Manager (Recommended)

```python
from Db import ResumeDatabase

class ResumeDatabaseContext(ResumeDatabase):
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close_connection()

# Automatic connection cleanup
with ResumeDatabaseContext() as db:
    resume = db.get_resume('resume_001')
    # Connection closes automatically
```

## 📚 API Reference

### Class: `ResumeDatabase`

#### Constructor

```python
db = ResumeDatabase(db_name='ResumeAnalyzer', collection_name='resumes')
```

**Parameters:**

- `db_name` (str): MongoDB database name (default: 'ResumeAnalyzer')
- `collection_name` (str): Collection name (default: 'resumes')

**Raises:**

- `ValueError`: If MONGO_URI not found in environment
- `ConnectionFailure`: If unable to connect to MongoDB

---

#### `insert_resume(resume: Dict[str, Any]) -> Dict[str, Any]`

Insert a new resume into the database.

**Parameters:**

- `resume`: Dictionary containing resume data

**Returns:**

```python
{
    'success': True,
    'id': 'resume_id',
    'message': 'Resume inserted successfully'
}
```

**Raises:**

- `ValueError`: If resume data is empty
- `DuplicateKeyError`: If resume with same ID already exists
- `PyMongoError`: For other database errors

**Example:**

```python
resume = {
    '_id': 'resume_001',  # Optional - auto-generated if not provided
    'name': 'John Doe',
    'skills': ['Python', 'MongoDB'],
    'experience': [...],
    'education': [...],
    'projects': [...],
    'extras': [...]
}
result = db.insert_resume(resume)
```

---

#### `get_resume(resume_id: str) -> Optional[Dict[str, Any]]`

Retrieve a resume by ID.

**Parameters:**

- `resume_id`: Unique identifier of the resume

**Returns:**

- Resume dictionary if found, `None` otherwise

**Example:**

```python
resume = db.get_resume('resume_001')
if resume:
    print(f"Name: {resume['name']}")
```

---

#### `get_all_resumes(limit=100, skip=0, sort_by='created_at', ascending=False) -> List[Dict[str, Any]]`

Retrieve all resumes with pagination and sorting.

**Parameters:**

- `limit` (int): Maximum number of resumes to return (default: 100)
- `skip` (int): Number of resumes to skip (default: 0)
- `sort_by` (str): Field to sort by (default: 'created_at')
- `ascending` (bool): Sort order (default: False for descending)

**Returns:**

- List of resume dictionaries

**Example:**

```python
# Get first 10 resumes, sorted by creation date (newest first)
resumes = db.get_all_resumes(limit=10, skip=0, sort_by='created_at', ascending=False)

# Pagination: Get next 10 resumes
next_batch = db.get_all_resumes(limit=10, skip=10)
```

---

#### `update_resume(resume_id: str, update_data: Dict[str, Any], upsert=False) -> Dict[str, Any]`

Update an existing resume.

**Parameters:**

- `resume_id`: Unique identifier of the resume
- `update_data`: Dictionary containing fields to update
- `upsert` (bool): If True, insert if document doesn't exist (default: False)

**Returns:**

```python
{
    'success': True,
    'message': 'Resume updated successfully',
    'matched_count': 1,
    'modified_count': 1,
    'upserted_id': None
}
```

**Example:**

```python
# Update specific fields
result = db.update_resume('resume_001', {
    'skills': ['Python', 'JavaScript', 'React'],
    'experience': [...]
})

# Upsert - insert if doesn't exist
result = db.update_resume('resume_new', {...}, upsert=True)
```

---

#### `delete_resume(resume_id: str) -> Dict[str, Any]`

Delete a resume by ID.

**Parameters:**

- `resume_id`: Unique identifier of the resume

**Returns:**

```python
{
    'success': True,
    'message': 'Resume deleted successfully',
    'deleted_count': 1
}
```

**Example:**

```python
result = db.delete_resume('resume_001')
if result['success']:
    print("Resume deleted successfully")
```

---

#### `search_resumes(query: Dict[str, Any], limit=50) -> List[Dict[str, Any]]`

Search resumes using MongoDB query syntax.

**Parameters:**

- `query`: MongoDB query dictionary
- `limit` (int): Maximum results to return (default: 50)

**Returns:**

- List of matching resume dictionaries

**Examples:**

```python
# Find resumes with Python skill
python_devs = db.search_resumes({'skills': {'$in': ['Python']}})

# Complex query - Python developers with 3+ years experience
results = db.search_resumes({
    'skills': {'$in': ['Python']},
    'experience.duration': {'$regex': '3|4|5', '$options': 'i'}
})

# Find by name pattern
results = db.search_resumes({
    'name': {'$regex': 'John', '$options': 'i'}
})
```

---

#### `add_ranking(resume_id: str, ranking_data: Dict[str, Any], job_description: str) -> Dict[str, Any]`

Add ranking information to a resume (supports multiple rankings).

**Parameters:**

- `resume_id`: Unique identifier of the resume
- `ranking_data`: Dictionary containing scores and justifications
- `job_description`: Job description used for ranking

**Returns:**

```python
{
    'success': True,
    'message': 'Ranking added successfully'
}
```

**Example:**

```python
ranking = {
    'skills': {'score': 35, 'justification': 'Strong Python skills'},
    'experience': {'score': 28, 'justification': 'Relevant experience'},
    'projects': {'score': 8, 'justification': 'Good portfolio'},
    'other_relevant_skills': {'score': 7, 'justification': 'Cloud knowledge'},
    'extras': {'score': 4, 'justification': 'AWS certified'},
    'total_score': 82
}

job_desc = "Looking for Full Stack Developer with Python"
result = db.add_ranking('resume_001', ranking, job_desc)
```

---

#### `get_resume_count(query: Optional[Dict[str, Any]] = None) -> int`

Get count of resumes matching query.

**Parameters:**

- `query`: Optional MongoDB query dictionary

**Returns:**

- Integer count of matching documents

**Example:**

```python
# Total resumes
total = db.get_resume_count()

# Count Python developers
python_count = db.get_resume_count({'skills': {'$in': ['Python']}})
```

---

#### `bulk_insert_resumes(resumes: List[Dict[str, Any]]) -> Dict[str, Any]`

Insert multiple resumes at once.

**Parameters:**

- `resumes`: List of resume dictionaries

**Returns:**

```python
{
    'success': True,
    'message': '10 resumes inserted',
    'inserted_ids': ['id1', 'id2', ...]
}
```

**Example:**

```python
resumes = [
    {'name': 'Alice', 'skills': ['Python', 'Django']},
    {'name': 'Bob', 'skills': ['JavaScript', 'React']},
    {'name': 'Carol', 'skills': ['Java', 'Spring']}
]

result = db.bulk_insert_resumes(resumes)
print(f"Inserted {len(result['inserted_ids'])} resumes")
```

---

#### `close_connection()`

Close the MongoDB connection.

**Example:**

```python
db = ResumeDatabase()
# ... perform operations ...
db.close_connection()
```

---

## 🔄 Legacy API (Backward Compatibility)

The module provides legacy functions for existing codebases:

```python
from Db import load_mongodb, insert_resume, get_resume, update_resume, delete_resume

# Get collection
collection = load_mongodb()

# Use with collection
resume = {'_id': 'test', 'name': 'Test User'}
insert_resume(resume, collection)

# Or use without collection (creates new connection each time)
resume = get_resume('test')
```

**Note:** The class-based API is recommended for new projects.

---

## 🛡️ Error Handling

The API uses proper exception handling. Always wrap operations in try-except blocks:

```python
from pymongo.errors import DuplicateKeyError, PyMongoError

try:
    db = ResumeDatabase()
    result = db.insert_resume(resume)

except DuplicateKeyError as e:
    print(f"Resume already exists: {e}")

except ValueError as e:
    print(f"Invalid data: {e}")

except PyMongoError as e:
    print(f"Database error: {e}")

finally:
    db.close_connection()
```

---

## 📊 Logging

The API uses Python's `logging` module. Configure logging level:

```python
import logging

# Set to DEBUG for detailed logs
logging.basicConfig(level=logging.DEBUG)

# Or set to WARNING to reduce output
logging.basicConfig(level=logging.WARNING)
```

---

## 🔍 MongoDB Query Examples

### Basic Queries

```python
# Exact match
db.search_resumes({'name': 'John Doe'})

# Multiple fields
db.search_resumes({'name': 'John Doe', 'skills': {'$in': ['Python']}})
```

### Pattern Matching

```python
# Case-insensitive regex
db.search_resumes({
    'name': {'$regex': 'john', '$options': 'i'}
})

# Starts with
db.search_resumes({
    'name': {'$regex': '^John'}
})
```

### Array Queries

```python
# Contains any
db.search_resumes({
    'skills': {'$in': ['Python', 'JavaScript']}
})

# Contains all
db.search_resumes({
    'skills': {'$all': ['Python', 'MongoDB']}
})

# Array size
db.search_resumes({
    'skills': {'$size': 5}
})
```

### Comparison Operators

```python
# Greater than
db.search_resumes({
    'experience.years': {'$gt': 3}
})

# Range
db.search_resumes({
    'total_score': {'$gte': 70, '$lte': 90}
})
```

### Nested Fields

```python
# Nested object field
db.search_resumes({
    'experience.company': 'Google'
})

# Array of objects
db.search_resumes({
    'experience': {
        '$elemMatch': {
            'company': 'Google',
            'position': {'$regex': 'Engineer'}
        }
    }
})
```

---

## 📈 Best Practices

1. **Use Context Managers**: Automatically close connections
2. **Error Handling**: Always wrap operations in try-except
3. **Pagination**: Use `limit` and `skip` for large datasets
4. **Indexing**: Create indexes for frequently queried fields
5. **Validation**: Validate data before insertion
6. **Connection Pooling**: Reuse `ResumeDatabase` instance
7. **Logging**: Monitor operations in production

---

## 🔧 Integration with Existing Code

### ResumeAnalyzer.py Integration

```python
from Db import ResumeDatabase

# Create database instance
db = ResumeDatabase()

# Parse resume
resume = parse_resume()

# Insert with error handling
try:
    result = db.insert_resume(resume)
    print(f"Resume inserted: {result['id']}")

    # Rank resume
    ranking = rank_resume(resume, job_description)

    # Add ranking to database
    db.add_ranking(result['id'], ranking, job_description)

except Exception as e:
    print(f"Error: {e}")
finally:
    db.close_connection()
```

---

## 🧪 Testing

```python
def test_database_operations():
    db = ResumeDatabase()

    # Test insert
    test_resume = {
        '_id': 'test_001',
        'name': 'Test User',
        'skills': ['Python'],
        'experience': [],
        'education': [],
        'projects': [],
        'extras': []
    }

    result = db.insert_resume(test_resume)
    assert result['success'] == True

    # Test get
    resume = db.get_resume('test_001')
    assert resume['name'] == 'Test User'

    # Test update
    result = db.update_resume('test_001', {'skills': ['Python', 'MongoDB']})
    assert result['modified_count'] == 1

    # Test delete
    result = db.delete_resume('test_001')
    assert result['deleted_count'] == 1

    db.close_connection()
    print("All tests passed!")

if __name__ == "__main__":
    test_database_operations()
```

---

## 📝 License

This is a professional-grade CRUD API for resume management. Use it in your projects freely!

---

## 🤝 Contributing

Feel free to extend this API with additional features like:

- Full-text search
- Aggregation pipelines
- Backup/restore functionality
- Data validation schemas
- Rate limiting
- Caching layer

---

## 📞 Support

For issues or questions:

1. Check the examples in `db_usage_examples.py`
2. Review MongoDB documentation
3. Check application logs for detailed error messages
