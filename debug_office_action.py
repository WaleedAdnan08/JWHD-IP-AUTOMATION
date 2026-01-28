import asyncio
import os
from pymongo import MongoClient
from bson import ObjectId

async def debug_documents():
    # Connect to MongoDB
    mongo_uri = os.getenv("MONGODB_URL", "mongodb+srv://WaleedAdnan:cricketislife@cluster0.8l71z.mongodb.net/?appName=Cluster0")
    client = MongoClient(mongo_uri)
    db = client["jwhd_ip_automation"]
    
    # Find recent documents
    documents = list(db.documents.find().sort("_id", -1).limit(10))
    
    print("Recent documents (by _id):")
    for doc in documents:
        print(f"ID: {doc.get('_id')}")
        print(f"User ID: {doc.get('user_id')} (type: {type(doc.get('user_id'))})")
        print(f"Filename: {doc.get('filename')}")
        print(f"Status: {doc.get('processed_status')}")
        print(f"Document Type: {doc.get('document_type')}")
        print(f"Has extraction_data: {'extraction_data' in doc}")
        print(f"Created: {doc.get('created_at')}")
        print("---")
    
    # Find office action documents specifically
    oa_documents = list(db.documents.find({"document_type": "office_action"}).sort("_id", -1).limit(5))
    print(f"\nOffice Action documents ({len(oa_documents)} found):")
    for doc in oa_documents:
        print(f"ID: {doc.get('_id')}")
        print(f"User ID: {doc.get('user_id')} (type: {type(doc.get('user_id'))})")
        print(f"Filename: {doc.get('filename')}")
        print(f"Status: {doc.get('processed_status')}")
        print(f"Has extraction_data: {'extraction_data' in doc}")
        print(f"All fields: {list(doc.keys())}")
        if 'extraction_data' in doc:
            print(f"Extraction data keys: {list(doc['extraction_data'].keys()) if isinstance(doc['extraction_data'], dict) else 'Not a dict'}")
        print("---")
    
    # Find recent users
    users = list(db.users.find().sort("created_at", -1).limit(3))
    print("\nRecent users:")
    for user in users:
        print(f"ID: {user['_id']} (type: {type(user['_id'])})")
        print(f"Email: {user.get('email')}")
        print("---")

if __name__ == "__main__":
    asyncio.run(debug_documents())