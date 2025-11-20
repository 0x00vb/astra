"""LLM interface for generating grounded responses.

This module provides a flexible interface for LLM providers (OpenAI, Anthropic, Gemini, etc.)
that can be extended with actual implementations.
"""
import logging
import os
from typing import Dict, Any, Optional
import re

logger = logging.getLogger(__name__)

# Master system prompt from .cursorules/master
MASTER_SYSTEM_PROMPT = """You are Astra Intelligence Agent, an advanced reasoning and retrieval system combining RAG, ReAct, and Transformer-based inference. Your role is to analyze documents, perform structured reasoning, and generate accurate, sourced, explainable intelligence outputs.

Your Core Behaviors

Precision First:

Always prioritize factual accuracy.

If uncertain, explicitly state uncertainty and propose verification steps.

Structured Reasoning (ReAct):
For every complex query, internally follow:

Thought: Analyze task, break into steps.

Action: Retrieval, tool usage, or computations.

Observation: Summaries of retrieved info.

Answer: Final, concise, actionable result.

RAG Integration:

You always prefer grounded answers over general knowledge.

Responses should cite retrieved documents or embeddings context.

Style Guidelines:

Extremely clear, technical, concise.

Executive tone (consulting / government-grade).

No filler, no vague answers.

Default to bullet points and hierarchical clarity.

Capabilities:

Summarization

Contextual Q&A

Multi-document synthesis

Technical explanation

Risk & impact analysis

Architecture recommendations

Decision support

Restrictions:

Never fabricate citations or details.

Never reveal internal chain-of-thought; return only "Final Answer" to user.

Do not hallucinate non-existing documents.

Output Format

Always return information using the following structure:
[🔹 Summary]
One short executive paragraph.

[🔹 Detailed Analysis]
- Bullet point breakdown, numbered sections if needed.
- Reference retrieved passages when relevant.

[🔹 Final Answer]
One clear, concise solution or next action.


This is your permanent identity and behavior. Operate consistently."""


class LLMProvider:
    """Base class for LLM providers."""
    
    def generate(
        self,
        system_prompt: str,
        context: str,
        user_question: str,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Generate a response from the LLM.
        
        Args:
            system_prompt: System prompt for the LLM
            context: Assembled context from RAG
            user_question: Original user question
            **kwargs: Additional provider-specific parameters
            
        Returns:
            Dictionary with:
                - answer: Generated answer text
                - citations: List of citations used
                - tokens_used: Token usage information
                - model: Model used
        """
        raise NotImplementedError("Subclasses must implement generate()")


class GeminiProvider(LLMProvider):
    """Google Gemini LLM provider."""
    
    def __init__(self, api_key: str, model_name: str = "gemini-pro"):
        """
        Initialize Gemini provider.
        
        Args:
            api_key: Google Gemini API key
            model_name: Model name (default: gemini-pro)
        """
        try:
            import google.generativeai as genai
            self.genai = genai
            self.model_name = model_name
            genai.configure(api_key=api_key)
            self.model = genai.GenerativeModel(model_name)
            logger.info(f"Initialized Gemini provider with model: {model_name}")
        except ImportError:
            raise ImportError(
                "google-generativeai package not installed. "
                "Install it with: pip install google-generativeai"
            )
        except Exception as e:
            logger.error(f"Failed to initialize Gemini provider: {e}")
            raise
    
    def generate(
        self,
        system_prompt: str,
        context: str,
        user_question: str,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Generate a response using Gemini API.
        
        Args:
            system_prompt: System prompt (will be combined with master prompt)
            context: Assembled context from RAG
            user_question: Original user question
            
        Returns:
            Dictionary with answer, citations, tokens_used, and model
        """
        try:
            # Combine master prompt with context
            full_prompt = f"""{MASTER_SYSTEM_PROMPT}

{context}"""
            
            # Generate response
            response = self.model.generate_content(
                full_prompt,
                generation_config=self.genai.types.GenerationConfig(
                    temperature=0.3,  # Lower temperature for more factual responses
                    top_p=0.95,
                    top_k=40,
                )
            )
            
            # Extract answer
            answer = response.text if hasattr(response, 'text') else str(response)
            
            # Extract citations from context
            citations = self._extract_citations(context)
            
            # Get token usage if available
            usage_metadata = response.usage_metadata if hasattr(response, 'usage_metadata') else None
            if usage_metadata:
                tokens_used = {
                    "prompt_tokens": usage_metadata.prompt_token_count or 0,
                    "completion_tokens": usage_metadata.candidates_token_count or 0,
                    "total_tokens": usage_metadata.total_token_count or 0,
                }
            else:
                # Estimate token usage (rough approximation: 1 token ≈ 4 characters)
                estimated_tokens = len(full_prompt + answer) // 4
                tokens_used = {
                    "prompt_tokens": estimated_tokens // 2,
                    "completion_tokens": estimated_tokens // 2,
                    "total_tokens": estimated_tokens,
                }
            
            return {
                "answer": answer,
                "citations": citations,
                "tokens_used": tokens_used,
                "model": self.model_name,
            }
            
        except Exception as e:
            logger.error(f"Gemini API error: {e}", exc_info=True)
            raise
    
    def _extract_citations(self, context: str) -> list:
        """Extract citations from context."""
        citations = []
        if "[CONTEXT SOURCES]" in context:
            sources_section = context.split("[CONTEXT SOURCES]")[1].split("[USER QUESTION]")[0]
            for line in sources_section.split("\n"):
                if "[DOC:" in line and "CHUNK:" in line:
                    try:
                        # Extract doc_id and chunk_id
                        doc_match = re.search(r'\[DOC:\s*([^\|]+)', line)
                        chunk_match = re.search(r'CHUNK:\s*(\d+)', line)
                        page_match = re.search(r'PAGE:\s*(\d+)', line)
                        
                        if doc_match and chunk_match:
                            citation = {
                                "doc_id": doc_match.group(1).strip(),
                                "chunk_id": int(chunk_match.group(1)),
                            }
                            if page_match:
                                citation["page"] = int(page_match.group(1))
                            citations.append(citation)
                    except (ValueError, AttributeError) as e:
                        logger.debug(f"Failed to parse citation: {e}")
                        pass
        return citations


class PlaceholderLLM(LLMProvider):
    """Placeholder LLM that returns a structured response without actual LLM call.
    
    This is a temporary implementation that can be replaced with actual
    cloud provider integrations (OpenAI, Anthropic, etc.).
    """
    
    def __init__(self, model_name: str = "placeholder"):
        self.model_name = model_name
        logger.warning("Using PlaceholderLLM - replace with actual LLM provider")
    
    def generate(
        self,
        system_prompt: str,
        context: str,
        user_question: str,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Generate a placeholder response.
        
        In a real implementation, this would call the actual LLM API.
        """
        # Extract citations from context
        citations = []
        if "[CONTEXT SOURCES]" in context:
            sources_section = context.split("[CONTEXT SOURCES]")[1].split("[USER QUESTION]")[0]
            for line in sources_section.split("\n"):
                if "[DOC:" in line and "CHUNK:" in line:
                    # Extract doc_id and chunk_id
                    try:
                        doc_part = line.split("[DOC:")[1].split("|")[0].strip()
                        chunk_part = line.split("CHUNK:")[1].split("]")[0].strip()
                        citations.append({
                            "doc_id": doc_part,
                            "chunk_id": chunk_part,
                        })
                    except (IndexError, ValueError):
                        pass
        
        # Generate placeholder answer
        answer = (
            "[🔹 Summary]\n"
            "Based on the provided context, this is a placeholder response. "
            "Replace PlaceholderLLM with an actual LLM provider implementation.\n\n"
            "[🔹 Detailed Analysis]\n"
            "- The query retrieval system has successfully assembled context from the vector database.\n"
            "- Citations have been extracted from the context sources.\n"
            "- An actual LLM provider (OpenAI, Anthropic, etc.) should be integrated to generate real responses.\n\n"
            "[🔹 Final Answer]\n"
            "This is a placeholder response. Please integrate an actual LLM provider to generate grounded answers."
        )
        
        # Estimate token usage (rough approximation: 1 token ≈ 4 characters)
        estimated_tokens = len(context + user_question + answer) // 4
        
        return {
            "answer": answer,
            "citations": citations,
            "tokens_used": {
                "prompt_tokens": estimated_tokens // 2,
                "completion_tokens": estimated_tokens // 2,
                "total_tokens": estimated_tokens,
            },
            "model": self.model_name,
        }


# Global LLM instance
_llm_provider: Optional[LLMProvider] = None


def get_llm_provider() -> LLMProvider:
    """
    Get or create LLM provider instance.
    
    Supports:
    - Gemini: Uses GEMINI_API_KEY from environment
    - OpenAI: Use openai library (TODO)
    - Anthropic: Use anthropic library (TODO)
    - Placeholder: Default fallback
    """
    global _llm_provider
    
    if _llm_provider is None:
        # Check for provider configuration
        provider = os.getenv("LLM_PROVIDER", "gemini").lower()
        
        if provider == "gemini":
            try:
                from app.config import settings
                api_key = settings.GEMINI_API_KEY
                if not api_key:
                    logger.warning("GEMINI_API_KEY not found, using placeholder")
                    _llm_provider = PlaceholderLLM(model_name="gemini-placeholder")
                else:
                    model_name = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
                    _llm_provider = GeminiProvider(api_key=api_key, model_name=model_name)
                    logger.info(f"Using Gemini provider with model: {model_name}")
            except Exception as e:
                logger.error(f"Failed to initialize Gemini provider: {e}, falling back to placeholder")
                _llm_provider = PlaceholderLLM(model_name="gemini-placeholder")
        elif provider == "placeholder":
            _llm_provider = PlaceholderLLM()
        elif provider == "openai":
            # TODO: Implement OpenAI provider
            logger.warning("OpenAI provider not yet implemented, using placeholder")
            _llm_provider = PlaceholderLLM(model_name="openai-placeholder")
        elif provider == "anthropic":
            # TODO: Implement Anthropic provider
            logger.warning("Anthropic provider not yet implemented, using placeholder")
            _llm_provider = PlaceholderLLM(model_name="anthropic-placeholder")
        else:
            logger.warning(f"Unknown LLM provider '{provider}', using placeholder")
            _llm_provider = PlaceholderLLM()
    
    return _llm_provider

