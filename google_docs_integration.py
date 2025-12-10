"""
Google Docs Integration Module
Simple integration to create and write content to Google Docs
"""

import streamlit as st
from google.oauth2 import service_account
from googleapiclient.discovery import build
import os

# Scopes required for Google Docs API
SCOPES = ['https://www.googleapis.com/auth/documents', 'https://www.googleapis.com/auth/drive', 'https://www.googleapis.com/auth/drive.file']

def get_credentials():
    """
    Authenticate and get credentials for Google Docs API.
    Uses Streamlit secrets for deployment or local credentials.json for development.
    """
    # Try Streamlit secrets first (for deployment)
    if "google_credentials" in st.secrets:
        creds = service_account.Credentials.from_service_account_info(
            st.secrets["google_credentials"],
            scopes=SCOPES
        )
        return creds
    
    # Fall back to local service account file (for local development)
    if os.path.exists('credentials.json'):
        creds = service_account.Credentials.from_service_account_file(
            'credentials.json',
            scopes=SCOPES
        )
        return creds
    
    # If neither exists, raise error
    raise FileNotFoundError(
        "credentials.json not found and no Streamlit secrets configured. "
        "Please add google_credentials to Streamlit secrets or download credentials.json from Google Cloud Console.\n"
        "Visit: https://console.cloud.google.com/apis/credentials"
    )

def create_google_doc(title, content, folder_id="1HXjw0QBYCi8NBqOfhzazkzl-_ZyREWSr"):
    """
    Create a new Google Doc with the given title and content.
    Documents are created in a shared folder since service accounts 
    don't have their own Drive space.
    
    Args:
        title (str): Title of the document
        content (str): Content to add to the document
        folder_id (str): Google Drive folder ID (REQUIRED for service accounts)
    
    Returns:
        dict: Dictionary containing document_id and document_url
    """
    try:
        # Get credentials
        creds = get_credentials()
        
        # Build the Drive and Docs API services
        drive_service = build('drive', 'v3', credentials=creds)
        docs_service = build('docs', 'v1', credentials=creds)
        
        # Create document metadata with parent folder
        file_metadata = {
            'name': title,
            'mimeType': 'application/vnd.google-apps.document',
            'parents': [folder_id]  # Create directly in the folder
        }
        
        # Create the document using Drive API (in the specified folder)
        file = drive_service.files().create(
            body=file_metadata,
            fields='id'
        ).execute()
        
        document_id = file.get('id')
        
        # Now add content using Docs API
        requests = [
            {
                'insertText': {
                    'location': {
                        'index': 1,
                    },
                    'text': content
                }
            }
        ]
        
        # Execute the batch update
        docs_service.documents().batchUpdate(
            documentId=document_id,
            body={'requests': requests}
        ).execute()
        
        document_url = f'https://docs.google.com/document/d/{document_id}/edit'
        
        return {
            'document_id': document_id,
            'document_url': document_url,
            'success': True,
            'message': 'Document created successfully!'
        }
    
    except FileNotFoundError as e:
        return {
            'success': False,
            'message': str(e)
        }
    except Exception as e:
        return {
            'success': False,
            'message': f'Error creating document: {str(e)}'
        }
        

def append_to_google_doc(document_id, content):
    """
    Append content to an existing Google Doc.
    
    Args:
        document_id (str): ID of the document to append to
        content (str): Content to append
    
    Returns:
        dict: Status dictionary
    """
    try:
        # Get credentials
        creds = get_credentials()
        
        # Build the Docs API service
        service = build('docs', 'v1', credentials=creds)
        
        # Get the current document to find the end index
        doc = service.documents().get(documentId=document_id).execute()
        end_index = doc.get('body').get('content')[-1].get('endIndex') - 1
        
        # Prepare request to append content
        requests = [
            {
                'insertText': {
                    'location': {
                        'index': end_index,
                    },
                    'text': '\n\n' + content
                }
            }
        ]
        
        # Execute the batch update
        service.documents().batchUpdate(
            documentId=document_id,
            body={'requests': requests}
        ).execute()
        
        return {
            'success': True,
            'message': 'Content appended successfully!'
        }
    
    except Exception as e:
        return {
            'success': False,
            'message': f'Error appending to document: {str(e)}'
        }





