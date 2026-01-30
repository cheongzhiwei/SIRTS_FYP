"""
AI Ticket Classifier Script
Uses machine learning to classify incident tickets into categories:
- Hardware
- Software
- Network
- Account
- Other

This script can be used standalone or integrated with n8n workflows.
"""

import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.naive_bayes import MultinomialNB
from sklearn.pipeline import make_pipeline
import sys
import json
import pickle
import os

# Global model variable to avoid retraining on every call
_model = None

# Expanded Training Data for better accuracy
training_data = {
    'text': [
        # Hardware issues
        'laptop screen is flickering', 'keyboard button is broken', 'mouse not working',
        'need new charger', 'laptop battery not charging', 'screen cracked',
        'keyboard keys stuck', 'trackpad not responding', 'laptop overheating',
        'hard drive making noise', 'USB port not working', 'headphones broken',
        'monitor display issue', 'printer not printing', 'scanner not working',
        'laptop fan loud', 'power button not working', 'webcam not working',
        
        # Software issues
        'cannot login to email', 'software keeps crashing', 'update windows error',
        'blue screen of death', 'application not opening', 'program freezing',
        'windows update failed', 'software installation error', 'antivirus blocking',
        'excel not responding', 'word document corrupted', 'outlook sync issue',
        'browser slow', 'application error', 'software compatibility issue',
        'windows activation problem', 'driver update needed', 'program won\'t start',
        
        # Network issues
        'wifi is slow', 'cannot connect to printer', 'vpn connection failed',
        'internet not working', 'cannot access shared drive', 'email server down',
        'network connection lost', 'wifi password reset', 'ethernet cable issue',
        'cannot connect to server', 'remote desktop not working', 'network printer offline',
        'slow internet speed', 'dns resolution failed', 'firewall blocking',
        'cannot access website', 'network timeout', 'connection dropped',
        
        # Account issues
        'reset my password', 'account locked', 'cannot login',
        'password expired', 'account access denied', 'user permissions issue',
        'forgot password', 'account disabled', 'login credentials invalid',
        'need account access', 'account suspended', 'password reset required',
        'cannot access account', 'account not found', 'authentication failed',
        'user account issue', 'login problem', 'account security question',
        
        # Other/General
        'general inquiry', 'need help', 'question about system',
        'training request', 'documentation needed', 'policy question'
    ],
    'category': [
        # Hardware (18 items)
        'Hardware', 'Hardware', 'Hardware', 'Hardware', 'Hardware', 'Hardware',
        'Hardware', 'Hardware', 'Hardware', 'Hardware', 'Hardware', 'Hardware',
        'Hardware', 'Hardware', 'Hardware', 'Hardware', 'Hardware', 'Hardware',
        
        # Software (18 items)
        'Software', 'Software', 'Software', 'Software', 'Software', 'Software',
        'Software', 'Software', 'Software', 'Software', 'Software', 'Software',
        'Software', 'Software', 'Software', 'Software', 'Software', 'Software',
        
        # Network (18 items)
        'Network', 'Network', 'Network', 'Network', 'Network', 'Network',
        'Network', 'Network', 'Network', 'Network', 'Network', 'Network',
        'Network', 'Network', 'Network', 'Network', 'Network', 'Network',
        
        # Account (18 items)
        'Account', 'Account', 'Account', 'Account', 'Account', 'Account',
        'Account', 'Account', 'Account', 'Account', 'Account', 'Account',
        'Account', 'Account', 'Account', 'Account', 'Account', 'Account',
        
        # Other (6 items)
        'Other', 'Other', 'Other', 'Other', 'Other', 'Other'
    ]
}

# Convert to DataFrame
df = pd.DataFrame(training_data)

def get_model():
    """
    Get or create the trained model (singleton pattern).
    This avoids retraining on every function call.
    """
    global _model
    if _model is None:
        # Build the Model Pipeline
        # Using TfidfVectorizer for text feature extraction and MultinomialNB for classification
        _model = make_pipeline(
            TfidfVectorizer(max_features=1000, ngram_range=(1, 2), stop_words='english'),
            MultinomialNB(alpha=0.1)
        )
        # Train the Model
        if sys.stderr:
            print("Training AI classifier model...", file=sys.stderr)
        _model.fit(df['text'], df['category'])
        if sys.stderr:
            print("Model training completed.", file=sys.stderr)
    return _model

def classify_ticket(title="", description=""):
    """
    Classify a ticket based on its title and description.
    
    Args:
        title (str): The ticket title
        description (str): The ticket description
        
    Returns:
        str: The predicted category (Hardware, Software, Network, Account, or Other)
    """
    # Combine title and description for classification
    combined_text = f"{title} {description}".strip()
    
    if not combined_text:
        return "Other"
    
    # Get the trained model
    model = get_model()
    
    # Predict category
    prediction = model.predict([combined_text])[0]
    return prediction

def get_prediction_confidence(title="", description=""):
    """
    Get the prediction confidence score for a classification.
    
    Args:
        title (str): The ticket title
        description (str): The ticket description
        
    Returns:
        dict: Contains 'category' and 'confidence' (0-1 score)
    """
    combined_text = f"{title} {description}".strip()
    
    if not combined_text:
        return {"category": "Other", "confidence": 0.0}
    
    # Get the trained model
    model = get_model()
    
    # Get prediction probabilities
    probabilities = model.predict_proba([combined_text])[0]
    categories = model.classes_
    
    # Find the highest probability
    max_idx = probabilities.argmax()
    predicted_category = categories[max_idx]
    confidence = float(probabilities[max_idx])
    
    return {
        "category": predicted_category,
        "confidence": confidence
    }

if __name__ == "__main__":
    # Command-line usage
    if len(sys.argv) > 1:
        # If JSON input is provided
        try:
            input_data = json.loads(sys.argv[1])
            title = input_data.get('title', '')
            description = input_data.get('description', '')
        except json.JSONDecodeError:
            # If it's just a plain string, treat as description
            title = ""
            description = sys.argv[1]
    else:
        # Read from stdin
        try:
            input_data = json.load(sys.stdin)
            title = input_data.get('title', '')
            description = input_data.get('description', '')
        except (json.JSONDecodeError, EOFError):
            title = ""
            description = ""
    
    # Initialize model (will train on first call)
    get_model()
    
    # Classify the ticket
    category = classify_ticket(title, description)
    confidence_data = get_prediction_confidence(title, description)
    
    # Output as JSON for n8n or other integrations
    result = {
        "predicted_category": category,
        "confidence": confidence_data["confidence"],
        "title": title,
        "description": description
    }
    
    print(json.dumps(result))
