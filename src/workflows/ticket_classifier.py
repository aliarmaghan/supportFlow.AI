import openai
from typing import Dict, Any, List
from models.ticket_models import TicketClassification
from tools.knowledge_base import KnowledgeBaseSearch, KnowledgeArticle
import json

class TicketClassifier:
    def __init__(self, api_key: str):
        self.client = openai.OpenAI(api_key=api_key)
        self.knowledge_base = KnowledgeBaseSearch()
    
    def classify_and_search(self, customer_message: str, customer_context: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Full workflow: Classify ticket AND search knowledge base
        This demonstrates SO + TU integration
        """
        
        # Step 1: Classify the ticket (Structured Output)
        classification = self.classify_ticket(customer_message, customer_context)
        
        # Step 2: Search knowledge base based on classification (Tool Use)
        search_terms = self._extract_search_terms(customer_message, classification)
        relevant_articles = self.knowledge_base.search_articles(
            query_terms=search_terms,
            category=classification.category
        )
        
        # Step 3: Generate suggested response using found articles
        suggested_response = self._generate_response(
            customer_message, 
            classification, 
            relevant_articles
        )
        
        return {
            "classification": classification,
            "relevant_articles": relevant_articles,
            "suggested_response": suggested_response,
            "search_terms_used": search_terms
        }
    
    def classify_ticket(self, customer_message: str, customer_context: Dict[str, Any] = None) -> TicketClassification:
        """
        Classify incoming customer message using OpenAI structured output
        """
        
        # Build context about customer if available
        context_info = ""
        if customer_context:
            context_info = f"""
            Customer Context:
            - Plan: {customer_context.get('plan', 'Unknown')}
            - Account Age: {customer_context.get('account_age_months', 'Unknown')} months
            - Previous Tickets: {customer_context.get('previous_tickets', 0)}
            """
        
        system_prompt = f"""You are a SaaS customer support classification expert. 

        Analyze customer messages and classify them accurately for routing to the right team.

        Consider these SaaS-specific factors:
        - Technical issues often need escalation
        - Billing issues are time-sensitive 
        - Feature requests are lower priority unless from enterprise customers
        - Integration problems can impact business operations

        {context_info}

        Return your analysis as structured data following the provided schema."""
        
        response = self.client.beta.chat.completions.parse(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"Customer message: {customer_message}"}
            ],
            response_format=TicketClassification,
            temperature=0.1
        )
        
        return response.choices[0].message.parsed
    
    def _extract_search_terms(self, message: str, classification: TicketClassification) -> List[str]:
        """Extract relevant search terms from message and classification"""
        terms = []
        
        # Add category as search term
        terms.append(classification.category)
        
        # Extract key terms from message (simple approach)
        keywords = ["stripe", "payment", "billing", "invoice", "integration", "api", "webhook", 
                   "feature", "dark mode", "dashboard", "charge", "subscription", "failing",
                   "error", "troubleshooting", "setup"]
        
        for keyword in keywords:
            if keyword.lower() in message.lower():
                terms.append(keyword)
        
        return list(set(terms))  # Remove duplicates
    
    def _generate_response(self, original_message: str, classification: TicketClassification, 
                          articles: List[KnowledgeArticle]) -> str:
        """Generate a suggested response using found articles"""
        
        articles_context = ""
        if articles:
            articles_context = "Relevant knowledge base articles:\n"
            for article in articles:
                articles_context += f"- {article.title}: {article.content[:200]}...\n"
        
        system_prompt = f"""You are a helpful SaaS support agent. 
        Generate a professional, helpful response to the customer.
        
        Ticket Classification: {classification.category} - {classification.priority} priority
        Customer Sentiment: {classification.sentiment}
        Requires Escalation: {classification.requires_human_escalation}
        
        {articles_context}
        
        Guidelines:
        - Keep response professional, empathetic, and actionable
        - If articles are available, reference the relevant information
        - If escalation is required, mention that a specialist will follow up
        - For urgent issues, acknowledge the business impact
        - Provide specific next steps when possible"""
        
        response = self.client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"Customer message: {original_message}"}
            ],
            temperature=0.7,
            max_tokens=400
        )
        
        return response.choices[0].message.content