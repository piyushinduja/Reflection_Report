"""
Google Docs Integration Module
Simple integration to create and write content to Google Docs
"""

from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
import os
import pickle

# Scopes required for Google Docs API
SCOPES = ['https://www.googleapis.com/auth/documents']

def get_credentials():
    """
    Authenticate and get credentials for Google Docs API.
    Saves credentials to token.pickle for future use.
    """
    creds = None
    
    # Check if token.pickle exists (saved credentials)
    if os.path.exists('token.pickle'):
        with open('token.pickle', 'rb') as token:
            creds = pickle.load(token)
    
    # If credentials don't exist or are invalid, authenticate
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            # You need to download credentials.json from Google Cloud Console
            if not os.path.exists('credentials.json'):
                raise FileNotFoundError(
                    "credentials.json not found. Please download it from Google Cloud Console.\n"
                    "Visit: https://console.cloud.google.com/apis/credentials"
                )
            
            flow = InstalledAppFlow.from_client_secrets_file('credentials.json', SCOPES)
            creds = flow.run_local_server(port=0)
        
        # Save credentials for future use
        with open('token.pickle', 'wb') as token:
            pickle.dump(creds, token)
    
    return creds

def create_google_doc(title, content):
    """
    Create a new Google Doc with the given title and content.
    
    Args:
        title (str): Title of the document
        content (str): Content to add to the document
    
    Returns:
        dict: Dictionary containing document_id and document_url
    """
    try:
        # Get credentials
        creds = get_credentials()
        
        # Build the Docs API service
        service = build('docs', 'v1', credentials=creds)
        
        # Create a new document
        doc = service.documents().create(body={'title': title}).execute()
        document_id = doc.get('documentId')
        
        # Prepare requests to insert content
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
        service.documents().batchUpdate(
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
        