from workflows.ticket_classifier import TicketClassifier
import os
from dotenv import load_dotenv

load_dotenv()

def test_full_workflow():
    classifier = TicketClassifier(api_key=os.getenv("OPENAI_API_KEY"))
    
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

def test_additional_cases():
    """Test additional scenarios"""
    classifier = TicketClassifier(api_key=os.getenv("OPENAI_API_KEY"))
    
    test_cases = [
        {
            "name": "API Integration Crisis",
            "message": """URGENT: Our production API calls are returning 500 errors. 
            Our mobile app is completely down and customers are complaining on social media. 
            This started 2 hours ago and we can't figure out what changed.""",
            "context": {"plan": "Enterprise", "account_age_months": 18, "previous_tickets": 12, "user_role": "CTO"}
        },
        {
            "name": "Feature Request",
            "message": """Hi team! Love the product so far. 
            Would it be possible to add bulk export functionality? 
            It would save us tons of time for our monthly reports.""",
            "context": {"plan": "Starter", "account_age_months": 2, "previous_tickets": 1, "user_role": "User"}
        }
    ]
    
    for i, case in enumerate(test_cases, 1):
        print(f"\n{'='*60}")
        print(f"Additional Test Case {i}: {case['name']}")
        print(f"{'='*60}")
        
        result = classifier.classify_and_search(case['message'], case['context'])
        
        print("\n1. CLASSIFICATION:")
        classification = result["classification"]
        print(f"   Category: {classification.category}")
        print(f"   Priority: {classification.priority}")
        print(f"   Escalation: {classification.requires_human_escalation}")
        print(f"   Sentiment: {classification.sentiment}")
        
        print(f"\n2. SEARCH TERMS: {result['search_terms_used']}")
        
        print("\n3. RELEVANT ARTICLES:")
        for article in result["relevant_articles"]:
            print(f"   - {article.title}")
        
        print("\n4. SUGGESTED RESPONSE:")
        print(f"   {result['suggested_response']}")

if __name__ == "__main__":
    test_full_workflow()
    test_additional_cases()