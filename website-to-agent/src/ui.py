import streamlit as st
import asyncio

from src.config import DEFAULT_MAX_URLS, DEFAULT_USE_FULL_TEXT
from src.llms_text import extract_website_content
from src.agents import extract_domain_knowledge, create_domain_agent
from src.models import DomainKnowledge
from agents import Runner

# Initialize session state
def init_session_state():
    if 'domain_agent' not in st.session_state:
        st.session_state.domain_agent = None
    if 'domain_knowledge' not in st.session_state:
        st.session_state.domain_knowledge = None
    if 'messages' not in st.session_state:
        st.session_state.messages = []
    if 'extraction_status' not in st.session_state:
        st.session_state.extraction_status = None

def run_app():
    # Initialize session state
    init_session_state()
    
    # App title and description in main content area
    st.title("KnowledgeForge")
    st.subheader("Extract domain knowledge from any website and create specialized AI agents.")
    
    # Display welcome message using AI chat message component
    if not st.session_state.domain_agent:
        with st.chat_message("assistant"):
            st.markdown("👋 Welcome! Enter a website URL in the sidebar, and I'll transform it into an AI agent you can chat with.")
    
    # Form elements in sidebar
    st.sidebar.title("Create your agent")
    
    website_url = st.sidebar.text_input("Enter website URL", placeholder="https://example.com")
    
    max_pages = st.sidebar.slider("Maximum pages to analyze", 1, 100, DEFAULT_MAX_URLS, 
                         help="More pages means more comprehensive knowledge but longer processing time")
    
    use_full_text = st.sidebar.checkbox("Use comprehensive text extraction", value=DEFAULT_USE_FULL_TEXT,
                                help="Extract full contents of each page (may increase processing time)")
    
    submit_button = st.sidebar.button("Create agent", type="primary")
    
    # Display current status in sidebar if extraction is in progress
    if st.session_state.extraction_status == "extracting":
        st.sidebar.info("Extraction in progress...")
    elif st.session_state.extraction_status == "complete":
        st.sidebar.success("Agent created successfully!")
    elif st.session_state.extraction_status == "failed":
        st.sidebar.error("Extraction failed. Please try again.")
    
    # Process form submission
    if submit_button and website_url:
        st.session_state.extraction_status = "extracting"
        
        try:
            with st.spinner("Extracting website content with Firecrawl..."):
                content = extract_website_content(
                    url=website_url, 
                    max_urls=max_pages,
                    show_full_text=use_full_text
                )
                
                # Show content sample
                with st.expander("View extracted content sample"):
                    st.text(content['llmstxt'][:1000] + "...")
                
                # Process content to extract knowledge
                with st.spinner("Analyzing content and generating knowledge model..."):
                    domain_knowledge = asyncio.run(extract_domain_knowledge(
                        content['llmstxt'] if not use_full_text else content['llmsfulltxt'],
                        website_url
                    ))
                    
                    # Store in session state
                    st.session_state.domain_knowledge = domain_knowledge
                
                # Create specialized agent
                with st.spinner("Creating specialized agent..."):
                    domain_agent = create_domain_agent(domain_knowledge)
                    
                    # Store in session state
                    st.session_state.domain_agent = domain_agent
                    
                    st.session_state.extraction_status = "complete"
                    st.success("Agent created successfully!")
        
        except Exception as e:
            st.error(f"Error: {str(e)}")
            st.session_state.extraction_status = "failed"
    
    # Chat interface
    if st.session_state.domain_agent:
        display_chat_interface()

def display_chat_interface():
    """Display chat interface for interacting with the domain agent."""
    st.subheader("Chat with your domain expert")
    
    # Display chat history
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])
    
    # Chat input
    if prompt := st.chat_input("Ask a question about this domain..."):
        # Add user message to chat history
        st.session_state.messages.append({"role": "user", "content": prompt})
        
        # Display user message
        with st.chat_message("user"):
            st.markdown(prompt)
        
        # Get agent response
        with st.chat_message("assistant"):
            message_placeholder = st.empty()
            full_response = ""
            
            # Process with agent
            with st.spinner("Thinking..."):
                result = asyncio.run(Runner.run(st.session_state.domain_agent, prompt))
                full_response = result.final_output
            
            message_placeholder.markdown(full_response)
            
        # Add assistant response to chat history
        st.session_state.messages.append({"role": "assistant", "content": full_response})

if __name__ == "__main__":
    run_app()
