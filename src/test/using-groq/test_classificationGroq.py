"""
This test script runs the full workflow of classifying a support ticket using Groq,
"""

from workflows.ticket_classifierGroq import TicketClassifier
import os
from dotenv import load_dotenv

load_dotenv()

def test_full_workflow():
    classifier = TicketClassifier(api_key=os.getenv("GROQ_API_KEY"))
    
    # Sample 1: Billing Issue
    sample_message = """Hi, I just tried to upgrade our plan but my payment was declined. 
    I'm sure the card has sufficient funds and isn't expired. 
    We need the higher limits for an important client project starting tomorrow."""

    customer_context = {
        "plan": "Business",
        "account_age_months": 3,
        "previous_tickets": 0,
        "user_role": "Admin"
    }
    
    print("=== Full Workflow Test ===")
    result = classifier.classify_and_search(sample_message, customer_context)
    
    print("\n1. CLASSIFICATION:")
    print(result["classification"].model_dump_json(indent=2))
    
    print(f"\n2. SEARCH TERMS USED: {result['search_terms_used']}")
    
    print("\n3. RELEVANT ARTICLES:")
    for article in result["relevant_articles"]:
        print(f"- {article.title}")
    
    print("\n4. SUGGESTED RESPONSE:")
    print(result["suggested_response"])

if __name__ == "__main__":
    test_full_workflow()