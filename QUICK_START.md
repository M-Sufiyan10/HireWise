# Quick Start Guide - Resume Database API

## 🚀 5-Minute Setup

### 1. Install Dependencies

```bash
pip install pymongo python-dotenv
```

### 2. Configure Environment

Copy `.env.example` to `.env` and fill it in:

```env
MONGO_URI=mongodb://localhost:27017/
GOOGLE_API_KEY=your-gemini-api-key   # needed for parsing/ranking resumes
```

### Run the Resume Pipeline

```bash
# Rank every PDF in a folder against a job description
python ResumeAnalyzer.py resumes/ -j "Senior Python developer with MongoDB"

# Specific files, job description read from a file
python ResumeAnalyzer.py alice.pdf bob.pdf --jd-file job.txt

# No arguments: all PDFs in the current directory, job description prompted
python ResumeAnalyzer.py
```

Each resume is parsed by Gemini, stored in MongoDB, scored out of 100 and a
leaderboard is printed at the end.

### 3. Basic Usage

```python
from Db import ResumeDatabase

# Initialize
db = ResumeDatabase()

# Insert
resume = {
    'name': 'John Doe',
    'skills': ['Python', 'MongoDB'],
    'experience': [],
    'education': [],
    'projects': [],
    'extras': []
}
result = db.insert_resume(resume)

# Get
resume = db.get_resume(result['id'])

# Update
db.update_resume(result['id'], {'skills': ['Python', 'MongoDB', 'React']})

# Delete
db.delete_resume(result['id'])

# Close
db.close_connection()
```

## 📋 Common Operations

### Get All Resumes (with pagination)

```python
resumes = db.get_all_resumes(limit=10, skip=0)
```

### Search Resumes

```python
# Find Python developers
python_devs = db.search_resumes({'skills': {'$in': ['Python']}})

# Case-insensitive name search
results = db.search_resumes({
    'name': {'$regex': 'john', '$options': 'i'}
})
```

### Add Ranking

```python
ranking = {
    'skills': {'score': 35, 'justification': '...'},
    'experience': {'score': 28, 'justification': '...'},
    'projects': {'score': 8, 'justification': '...'},
    'other_relevant_skills': {'score': 7, 'justification': '...'},
    'extras': {'score': 4, 'justification': '...'},
    'total_score': 82
}
db.add_ranking(resume_id, ranking, "Job description here")
```

### Bulk Insert

```python
resumes = [
    {'name': 'Alice', 'skills': ['Python']},
    {'name': 'Bob', 'skills': ['JavaScript']}
]
result = db.bulk_insert_resumes(resumes)
```

### Top Ranked Resumes

```python
for r in db.get_top_resumes(limit=5):
    print(r['name'], r['total_score'])
```

### Count Resumes

```python
total = db.get_resume_count()
python_count = db.get_resume_count({'skills': {'$in': ['Python']}})
```

## 🔍 MongoDB Query Examples

```python
# Exact match
db.search_resumes({'name': 'John Doe'})

# Multiple conditions
db.search_resumes({
    'skills': {'$in': ['Python', 'JavaScript']},
    'experience.company': 'Google'
})

# Comparison operators
db.search_resumes({
    'total_score': {'$gte': 70, '$lte': 90}
})

# Array operations
db.search_resumes({
    'skills': {'$all': ['Python', 'MongoDB']}  # Has both
})

# Nested fields
db.search_resumes({
    'experience': {
        '$elemMatch': {
            'company': 'Google',
            'position': {'$regex': 'Engineer'}
        }
    }
})
```

## ⚡ Best Practices

### 1. Use Try-Except

```python
from pymongo.errors import DuplicateKeyError, PyMongoError

try:
    db = ResumeDatabase()
    result = db.insert_resume(resume)
except DuplicateKeyError:
    print("Resume already exists")
except PyMongoError as e:
    print(f"Database error: {e}")
finally:
    db.close_connection()
```

### 2. Context Manager (Recommended)

```python
with ResumeDatabase() as db:
    resume = db.get_resume('resume_001')
    # Connection closes automatically
```

### 3. Reuse Database Instance

```python
# Good - reuse connection
db = ResumeDatabase()
for resume in resumes:
    db.insert_resume(resume)
db.close_connection()

# Bad - creates new connection each time
for resume in resumes:
    db = ResumeDatabase()
    db.insert_resume(resume)
    db.close_connection()
```

## 🧪 Testing

Run the test suite:

```bash
pytest
```

Tests use an isolated `HireWise_test` database and a fake LLM, so they need a
running MongoDB but no Gemini API key.

## 📚 Full Documentation

See `DB_API_README.md` for complete documentation.

## 📝 Examples

See `db_usage_examples.py` for comprehensive examples.

## 🔧 Integration Example

```python
from Db import ResumeDatabase
from RankResume import rank_resume

db = ResumeDatabase()

try:
    # Parse and insert resume
    resume = parse_resume(pdf_file)
    result = db.insert_resume(resume)
    resume_id = result['id']

    # Rank resume
    ranking = rank_resume(resume, job_description)
    db.add_ranking(resume_id, ranking, job_description)

    print(f"Total Score: {ranking['total_score']}/100")

finally:
    db.close_connection()
```

## ⚠️ Troubleshooting

### Connection Error

```
ValueError: MONGO_URI not found in environment variables
```

**Solution**: Create `.env` file with `MONGO_URI`

### Duplicate Key Error

```
DuplicateKeyError: Resume with ID ... already exists
```

**Solution**: Use different `_id` or delete existing resume first

### Import Error

```
ModuleNotFoundError: No module named 'pymongo'
```

**Solution**: `pip install pymongo`

## 🎯 Next Steps

1. Review `DB_API_README.md` for full API documentation
2. Run `test_db.py` to test your setup
3. Check `db_usage_examples.py` for advanced usage
4. Integrate with your existing code

## 📞 Need Help?

- Check MongoDB logs for errors
- Review application logs (logging is built-in)
- Refer to MongoDB documentation for query syntax
- See examples for common patterns

---

**Happy coding! 🚀**
