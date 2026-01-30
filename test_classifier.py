#!/usr/bin/env python
"""Quick test script for the ticket classifier"""

from ticket_classifier import classify_ticket, get_prediction_confidence

# Test cases
test_cases = [
    ("laptop screen flickering", "screen keeps flickering"),
    ("cannot login to email", "I cannot access my email account"),
    ("wifi is slow", "internet connection is very slow"),
    ("reset my password", "I need to reset my password"),
]

print("Testing Ticket Classifier\n" + "=" * 50)

for title, description in test_cases:
    category = classify_ticket(title, description)
    confidence = get_prediction_confidence(title, description)
    
    print(f"\nTitle: {title}")
    print(f"Description: {description}")
    print(f"Predicted Category: {category}")
    print(f"Confidence: {confidence['confidence']:.2%}")

print("\n" + "=" * 50)
print("All tests completed!")
