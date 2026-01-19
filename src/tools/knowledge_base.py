import json
import os
from typing import List, Dict, Any
from dataclasses import dataclass

@dataclass
class KnowledgeArticle:
    id: str
    title: str
    category: str
    content: str
    tags: List[str]



class KnowledgeBaseSearch:
    def __init__(self, knowledge_base_path: str = "src/data/FAQs.json"):
        self.knowledge_base_path = knowledge_base_path
        self.articles = self._load_knowledge_base()
    
    def _load_knowledge_base(self) -> List[KnowledgeArticle]:
        """Load knowledge base from your JSON file"""
        try:
            with open(self.knowledge_base_path, 'r', encoding='utf-8') as file:
                json_data = json.load(file)
            
            articles = []
            
            # Make sure your JSON structure is like:

            for item in json_data:
                article = KnowledgeArticle(
                    id=str(item.get('id', len(articles) + 1)),
                    title=item.get('title', 'Unknown Question'),  # Use question as title
                    category=item.get('category', 'general').lower(),
                    content=item.get('content', ''),  # Use answer as content
                    tags=self._extract_tags_from_text(item.get('title', '') + ' ' + item.get('content', ''))
                )
                articles.append(article)
            
            print(f"Loaded {len(articles)} articles from {self.knowledge_base_path}")
            return articles
            
        except FileNotFoundError:
            print(f"Knowledge base file not found: {self.knowledge_base_path}")
            return self._get_fallback_articles()
        except json.JSONDecodeError as e:
            print(f"Error parsing JSON: {e}")
            return self._get_fallback_articles()
    
    def _extract_tags_from_text(self, text: str) -> List[str]:
        """Extract common SaaS keywords as tags"""
        saas_keywords = [
            'stripe', 'payment', 'billing', 'invoice', 'subscription',
            'api', 'integration', 'webhook', 'dashboard', 'user',
            'account', 'login', 'password', 'feature', 'bug', 
            'performance', 'security', 'backup', 'export', 'import'
        ]
        
        text_lower = text.lower()
        found_tags = [keyword for keyword in saas_keywords if keyword in text_lower]
        return found_tags[:5]  # Limit to 5 most relevant tags
    
    def _get_fallback_articles(self) -> List[KnowledgeArticle]:
        """Fallback articles if JSON loading fails"""
        return [
            KnowledgeArticle(
                id="fallback-1",
                title="General Support",
                category="general",
                content="Please contact support for assistance.",
                tags=["support", "help"]
            )
        ]
    
    # Keep your existing search_articles method unchanged
    def search_articles(self, query_terms: List[str], category: str = None) -> List[KnowledgeArticle]:
        """Search knowledge base by terms and optionally filter by category"""
        results = []
        
        for article in self.articles:
            if category and article.category != category.lower():
                continue
                
            searchable_text = f"{article.title} {article.content} {' '.join(article.tags)}".lower()
            
            score = 0
            for term in query_terms:
                if term.lower() in searchable_text:
                    score += searchable_text.count(term.lower())
            
            if score > 0:
                results.append(article)
        
        return sorted(results, key=lambda x: sum(term.lower() in f"{x.title} {x.content}".lower() 
                                                for term in query_terms), reverse=True)[:3]