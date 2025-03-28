"""
app.py

Streamlit application for LegalWhiz - Smart Contract Risk Analyzer
This is the main entry point for the application that provides a modern UI
and connects the document parsing and analysis components.
"""

import streamlit as st
import os
import io
from dotenv import load_dotenv
import time
import re

# Import our custom modules - Note that we're now using local_contract_analyzer
import azure_form_parser as parser
# Import our local analyzer instead of the OpenAI one
import local_contract_analyzer as analyzer

# Load environment variables
load_dotenv()

# Custom CSS for styling
def local_css():
    st.markdown("""
    <style>
        /* Main theme colors */
        :root {
            --primary-color: #2563EB;
            --secondary-color: #3B82F6;
            --accent-color: #DBEAFE;
            --text-color: #E5E7EB;
            --background-color: #111827;
            --card-background: #1F2937;
            --success-color: #10B981;
            --warning-color: #F59E0B;
            --danger-color: #EF4444;
        }
        
        /* Dark mode base styles */
        .stApp {
            background-color: var(--background-color);
            color: var(--text-color);
        }

        /* Main container styling */
        .main .block-container {
            padding-top: 1rem;
            padding-bottom: 1rem;
        }

        /* Headers styling */
        h1, h2, h3 {
            color: var(--secondary-color);
            font-weight: 600;
        }
        
        h1 {
            font-size: 2rem;
            margin-bottom: 1.5rem;
        }
        
        h2 {
            font-size: 1.5rem;
            margin-top: 1rem;
            margin-bottom: 1rem;
        }
        
        h3 {
            font-size: 1.2rem;
            margin-top: 0.8rem;
            margin-bottom: 0.8rem;
        }

        /* Card styling */
        .card {
            background-color: var(--card-background);
            border-radius: 0.5rem;
            padding: 1.5rem;
            box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
            margin-bottom: 1rem;
            border: none;
        }
        
        /* Risk level indicators */
        .risk-high {
            color: var(--danger-color);
            font-weight: 600;
        }
        
        .risk-medium {
            color: var(--warning-color);
            font-weight: 600;
        }
        
        .risk-low {
            color: var(--success-color);
            font-weight: 600;
        }
        
        /* Clause container */
        .clause-container {
            background-color: #374151;
            border-radius: 0.5rem;
            padding: 1rem;
            margin: 0.5rem 0;
            font-family: monospace;
            white-space: pre-wrap;
        }
        
        /* Button styling */
        .stButton > button {
            background-color: var(--primary-color);
            color: white;
            border-radius: 0.3rem;
            border: none;
            padding: 0.5rem 1rem;
            font-weight: 500;
        }
        
        .stButton > button:hover {
            background-color: var(--secondary-color);
        }
        
        /* File uploader styling */
        .css-1x8cf1d {
            background-color: var(--card-background) !important;
            color: var(--text-color) !important;
            border-color: #374151 !important;
        }
        
        /* Secondary button */
        .secondary-button > button {
            background-color: var(--card-background);
            color: var(--secondary-color);
            border: 1px solid var(--secondary-color);
        }
        
        .secondary-button > button:hover {
            background-color: #374151;
            color: var(--secondary-color);
        }
        
        /* Sidebar styling */
        .css-1d391kg, .css-16idsys p {
            background-color: var(--card-background) !important;
            color: var(--text-color) !important;
        }
        
        .sidebar .sidebar-content {
            background-color: var(--card-background) !important;
            color: var(--text-color) !important;
        }
        
        /* Tab styling for better visibility */
        .stTabs [data-baseweb="tab-list"] {
            gap: 1rem;
            background-color: #1F2937;
        }
        
        .stTabs [data-baseweb="tab"] {
            height: 3rem;
            white-space: pre-wrap;
            background-color: #1F2937;
            color: #E5E7EB;
            border-radius: 0.5rem 0.5rem 0 0;
            gap: 0.5rem;
            padding-top: 0.5rem;
            padding-bottom: 0.5rem;
        }
        
        .stTabs [aria-selected="true"] {
            background-color: #2563EB;
            color: white;
            border-bottom: 2px solid #60A5FA;
        }
        
        /* Contract text styling */
        .contract-text-container {
            max-height: 70vh;
            overflow-y: auto;
            padding: 1rem;
            background-color: var(--card-background);
            border: 1px solid #374151;
            border-radius: 0.5rem;
        }
        
        .contract-text {
            font-family: 'Courier New', monospace;
            white-space: pre-wrap;
            line-height: 1.5;
            color: var(--text-color);
        }
        
        .contract-section {
            font-weight: bold;
            color: #60A5FA;
            margin-top: 1rem;
            margin-bottom: 0.5rem;
        }
        
        .contract-subsection {
            font-weight: bold;
            color: #93C5FD;
            margin-top: 0.8rem;
            margin-bottom: 0.3rem;
        }
        
        /* Logo styling */
        .logo-container {
            display: flex;
            align-items: center;
            margin-bottom: 1.5rem;
        }
        
        .logo-text {
            font-size: 1.8rem;
            font-weight: 600;
            margin-left: 0.5rem;
        }
        
        /* Success alert styling */
        .success-alert {
            background-color: #065F46;
            border: 1px solid #059669;
            color: white;
            padding: 1rem;
            border-radius: 0.5rem;
            margin: 1rem 0;
        }
        
        /* Warning alert styling */
        .warning-alert {
            background-color: #92400E;
            border: 1px solid #D97706;
            color: white;
            padding: 1rem;
            border-radius: 0.5rem;
            margin: 1rem 0;
        }
        
        /* Error alert styling */
        .error-alert {
            background-color: #7F1D1D;
            border: 1px solid #DC2626;
            color: white;
            padding: 1rem;
            border-radius: 0.5rem;
            margin: 1rem 0;
        }
    </style>
    """, unsafe_allow_html=True)

# Function to format contract text for better display
def format_contract_text(text):
    """Format contract text with highlighting for sections and subsections."""
    if not text:
        return ""
    
    # Split text into lines
    formatted_lines = text.split('\n')
    formatted_text = ""
    
    # Define patterns for identifying section headers and subsections
    section_regex = r'^(\d+\.|\s*[A-Z\s]{5,}|\s*ARTICLE\s+[\dIVXLC]+:?|\s*SECTION\s+[\d\.]+:?).*$'
    subsection_regex = r'^\s*(\d+\.\d+|\([a-z]\)|\([0-9]+\)|\s*[A-Z][a-z].*:).*$'
    
    section_header_pattern = re.compile(section_regex)
    subsection_pattern = re.compile(subsection_regex)
    
    for line in formatted_lines:
        line = line.rstrip()
        
        # Skip empty lines
        if not line.strip():
            formatted_text += "<br>\n"
            continue
            
        # Check if this line is a section header
        if section_header_pattern.match(line):
            formatted_text += '<div class="contract-section" style="color: #60A5FA;">' + line + '</div>\n'
        # Check if this line is a subsection
        elif subsection_pattern.match(line):
            formatted_text += '<div class="contract-subsection" style="color: #93C5FD;">' + line + '</div>\n'
        # Regular paragraph text
        else:
            formatted_text += line + '<br>\n'
    
    return formatted_text

# Page configuration
st.set_page_config(
    page_title="LegalWhiz - Smart Contract Risk Analyzer",
    page_icon="⚖️",
    layout="wide",
    initial_sidebar_state="expanded",
    menu_items={
        'About': "# LegalWhiz\nSmart Contract Risk Analyzer built for Microsoft Hackathon."
    }
)

# Apply custom CSS
local_css()

# Sidebar with application information
with st.sidebar:
    # Logo and title
    st.markdown(
        '<div class="logo-container">'
        '<span style="font-size:2rem;">⚖️</span>'
        '<span class="logo-text" style="color:#E5E7EB;">LegalWhiz</span>'
        '</div>', 
        unsafe_allow_html=True
    )
    
    # Sidebar with clean navigation look
    st.markdown("---")
    
    st.markdown(
        '<p style="color: white; font-size: 1.1rem; font-weight: 500;">Smart Contract Risk Analyzer</p>',
        unsafe_allow_html=True
    )
    
    st.markdown(
        '<div style="color: #E0E7FF; margin-top: 1rem;">'
        '<p>Analyze legal contracts instantly:</p>'
        '<ul>'
        '<li>Identify risky clauses</li>'
        '<li>Get plain English explanations</li>'
        '<li>Ask questions about your contract</li>'
        '</ul>'
        '</div>',
        unsafe_allow_html=True
    )

    # Application credits
    st.markdown("---")
    st.markdown(
        '<div style="color: #E0E7FF; font-size: 0.8rem; margin-top: 30px;">'
        'Built for Microsoft Hackathon<br>'
        'Powered by Document Intelligence'
        '</div>', 
        unsafe_allow_html=True
    )

# Main application content
st.markdown('<h1 style="color: #3B82F6;">LegalWhiz - Smart Contract Risk Analyzer</h1>', unsafe_allow_html=True)

# Session state initialization
if 'extracted_text' not in st.session_state:
    st.session_state.extracted_text = ""
if 'analysis_result' not in st.session_state:
    st.session_state.analysis_result = None
if 'file_processed' not in st.session_state:
    st.session_state.file_processed = False
if 'file_name' not in st.session_state:
    st.session_state.file_name = ""
if 'processing' not in st.session_state:
    st.session_state.processing = False

# Function to process the uploaded file
def process_uploaded_file(uploaded_file):
    if uploaded_file is not None:
        # Set processing state
        st.session_state.processing = True
        
        # Get file details
        file_details = {
            "filename": uploaded_file.name,
            "filetype": uploaded_file.type,
            "filesize": uploaded_file.size
        }
        
        # Store filename for display
        st.session_state.file_name = uploaded_file.name
        
        # Determine file type
        file_extension = os.path.splitext(uploaded_file.name)[1].lower()
        if file_extension == ".pdf":
            file_type = "pdf"
        elif file_extension == ".docx":
            file_type = "docx"
        else:
            st.markdown(
                '<div class="error-alert">Unsupported file type. Please upload a PDF or DOCX file.</div>', 
                unsafe_allow_html=True
            )
            st.session_state.processing = False
            return False
        
        # Read file bytes
        file_bytes = uploaded_file.getvalue()
        
        try:
            # Extract text from the document
            extracted_text = parser.parse_document(file_bytes, file_type)
            
            # Store the extracted text in session state
            st.session_state.extracted_text = extracted_text
            
            # Analyze the contract if text was extracted
            if extracted_text:
                # Use local analyzer to analyze the contract
                analysis_result = analyzer.analyze_contract(extracted_text)
                
                # Store analysis result in session state
                st.session_state.analysis_result = analysis_result
                st.session_state.file_processed = True
                st.session_state.processing = False
                return True
            else:
                st.markdown(
                    '<div class="error-alert">No text could be extracted from the document. Please try a different file.</div>', 
                    unsafe_allow_html=True
                )
                st.session_state.processing = False
                return False
                
        except Exception as e:
            st.markdown(
                '<div class="error-alert">Error processing document: ' + str(e) + '</div>', 
                unsafe_allow_html=True
            )
            st.session_state.processing = False
            return False
    return False

# File upload section with modern layout matching mockup
if not st.session_state.file_processed:
    st.markdown('<div class="card">', unsafe_allow_html=True)
    
    col1, col2 = st.columns([3, 2])
    
    with col1:
        st.markdown(
            '<h3 style="color: #3B82F6;"><span style="margin-right: 8px;">🔗</span> Upload Your Contract Document</h3>', 
            unsafe_allow_html=True
        )
        st.markdown('Upload a legal contract to analyze potential risks and get simplified explanations.')
        
        # File uploader with custom styling
        uploaded_file = st.file_uploader("", type=["pdf", "docx"])
        
        # Process the uploaded file
        if uploaded_file is not None:
            if st.button("Analyze Contract"):
                process_uploaded_file(uploaded_file)
    
    with col2:
        st.markdown('<div style="height: 30px;"></div>', unsafe_allow_html=True)
        st.markdown(
            '<div style="background-color: #1F2937; border-radius: 8px; padding: 1rem;">'
            '<p style="font-weight: 500; color: #E5E7EB;">Supported file types:</p>'
            '<p style="color: #E5E7EB;">• PDF (.pdf)</p>'
            '<p style="color: #E5E7EB;">• Microsoft Word (.docx)</p>'
            '<p style="font-size: 0.8rem; color: #9CA3AF; margin-top: 1rem;">Files are processed securely and not stored permanently.</p>'
            '</div>', 
            unsafe_allow_html=True
        )
    
    st.markdown('</div>', unsafe_allow_html=True)
    
    # Example capabilities card matching mockup
    st.markdown('<div class="card" style="margin-top: 1.5rem;">', unsafe_allow_html=True)
    st.markdown('<h3 style="color: #3B82F6;">What You Can Do With LegalWhiz</h3>', unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.markdown(
            '<div style="text-align: center;">'
            '<span style="font-size: 2rem;">🔍</span>'
            '<p style="font-weight: 500; margin: 0.5rem 0; color: #E5E7EB;">Risk Detection</p>'
            '<p style="color: #9CA3AF; font-size: 0.9rem;">Automatically identify risky clauses like auto-renewal, termination penalties, and liability limitations.</p>'
            '</div>', 
            unsafe_allow_html=True
        )
    
    with col2:
        st.markdown(
            '<div style="text-align: center;">'
            '<span style="font-size: 2rem;">🔄</span>'
            '<p style="font-weight: 500; margin: 0.5rem 0; color: #E5E7EB;">Plain English Translation</p>'
            '<p style="color: #9CA3AF; font-size: 0.9rem;">Get simplified explanations of complex legal language in terms anyone can understand.</p>'
            '</div>', 
            unsafe_allow_html=True
        )
    
    with col3:
        st.markdown(
            '<div style="text-align: center;">'
            '<span style="font-size: 2rem;">❓</span>'
            '<p style="font-weight: 500; margin: 0.5rem 0; color: #E5E7EB;">Contract Q&A</p>'
            '<p style="color: #9CA3AF; font-size: 0.9rem;">Ask specific questions about your contract and get accurate answers based on the document text.</p>'
            '</div>', 
            unsafe_allow_html=True
        )
    
    st.markdown('</div>', unsafe_allow_html=True)

# Show spinner during processing
if st.session_state.processing:
    with st.spinner("Processing your contract... This may take a moment."):
        time.sleep(0.1)  # Small delay to ensure spinner displays

# Reset button with better positioning and styling
if st.session_state.file_processed:
    col1, col2 = st.columns([6, 1])
    with col1:
        st.markdown(
            '<div style="background-color: #065F46; border-radius: 0.5rem; padding: 1rem; border: 1px solid #059669;">'
            '<p style="margin: 0; color: white; font-weight: 500;">Successfully analyzed: <strong>' + st.session_state.file_name + '</strong></p>'
            '</div>',
            unsafe_allow_html=True
        )
    with col2:
        if st.button("New Contract"):
            st.session_state.extracted_text = ""
            st.session_state.analysis_result = None
            st.session_state.file_processed = False
            st.session_state.file_name = ""
            st.experimental_rerun()

# Display the analysis results if a file has been processed
if st.session_state.file_processed and st.session_state.analysis_result:
    # Create tabs for different views with icons matching mockup
    tabs = st.tabs([
        "🚨 Risk Analysis", 
        "📄 Contract Text", 
        "❓ Ask Questions"
    ])
    
    with tabs[0]:  # Risk Analysis tab
        st.markdown('<h2 style="color: #3B82F6;">Contract Risk Analysis</h2>', unsafe_allow_html=True)
        
        # Create two columns for better layout
        col1, col2 = st.columns([2, 1])
        
        with col1:
            # Display risky clauses with improved styling
            st.markdown('<h3 style="color: #3B82F6;">Risky Clauses</h3>', unsafe_allow_html=True)
            risky_clauses = st.session_state.analysis_result.get("risky_clauses", [])
            
            if not risky_clauses:
                st.markdown(
                    '<div style="background-color: #059669; border-radius: 0.5rem; padding: 1rem; border-left: 4px solid #10B981;">'
                    '<p style="margin: 0; color: white; font-weight: 500;">No significant risks identified</p>'
                    '<p style="margin-top: 0.5rem; color: white;">This contract appears to have no major high-risk clauses based on our analysis.</p>'
                    '</div>',
                    unsafe_allow_html=True
                )
            else:
                # Sort clauses by risk level (highest first)
                sorted_clauses = sorted(risky_clauses, key=lambda x: x.get("risk_level", 0), reverse=True)
                
                for i, clause in enumerate(sorted_clauses):
                    risk_level = clause.get("risk_level", 0)
                    risk_class = "risk-high" if risk_level >= 4 else "risk-medium" if risk_level >= 2 else "risk-low"
                    risk_color = "#EF4444" if risk_level >= 4 else "#F59E0B" if risk_level >= 2 else "#10B981"
                    
                    # Create an expander for each clause
                    with st.expander(f"{clause.get('category', 'Unnamed')} - Risk Level: {risk_level}/5"):
                        # Original text
                        st.markdown('<p style="font-weight: 500;">Original Text:</p>', unsafe_allow_html=True)
                        st.markdown(
                            '<div class="clause-container">' + clause.get("text", "No text available") + '</div>', 
                            unsafe_allow_html=True
                        )
                        
                        # Risk explanation
                        st.markdown(
                            '<p style="font-weight: 500; margin-top: 1rem;">Why this is risky:</p>', 
                            unsafe_allow_html=True
                        )
                        st.markdown(
                            '<p style="color: '+risk_color+';">' + clause.get("explanation", "No explanation available") + '</p>', 
                            unsafe_allow_html=True
                        )
                        
                        # Add option to get simpler explanation
                        if st.button(f"Explain in Simpler Terms", key=f"explain_{i}"):
                            # Get simplified explanation (either from the clause or generate it)
                            simple_explanation = clause.get("simplified", "")
                            if not simple_explanation:
                                simple_explanation = analyzer.get_simple_explanation(clause.get('text', ''))
                                
                            st.markdown('<p style="font-weight: 500; margin-top: 1rem;">Simple Explanation:</p>', unsafe_allow_html=True)
                            st.markdown(
                                '<div style="background-color: #1F2937; padding: 1rem; border-radius: 0.5rem;">' + 
                                simple_explanation + 
                                '</div>', 
                                unsafe_allow_html=True
                            )
        
        with col2:
            # Display contract summary with improved styling
            st.markdown('<h3 style="color: #3B82F6;">Summary</h3>', unsafe_allow_html=True)
            summary_points = st.session_state.analysis_result.get("contract_summary", [])
            
            if summary_points:
                st.markdown(
                    '<div style="background-color: #1F2937; border-radius: 0.5rem; padding: 1rem; border: 1px solid #374151;">',
                    unsafe_allow_html=True
                )
                
                for point in summary_points:
                    st.markdown('<p style="margin-bottom: 0.8rem;">• ' + point + '</p>', unsafe_allow_html=True)
                
                st.markdown('</div>', unsafe_allow_html=True)
            else:
                st.info("No summary available for this contract.")
    
    with tabs[1]:  # Contract Text tab
        st.markdown('<h2 style="color: #3B82F6;">Contract Text</h2>', unsafe_allow_html=True)
        
        # Use better text formatting for the contract
        formatted_text = format_contract_text(st.session_state.extracted_text)
        
        st.markdown(
            '<div class="contract-text-container" style="background-color: #1F2937; border: 1px solid #374151;">'
            '<div class="contract-text" style="color: #E5E7EB;">' + formatted_text + '</div>'
            '</div>', 
            unsafe_allow_html=True
        )
    
    with tabs[2]:  # Ask Questions tab
        st.markdown('<h2 style="color: #3B82F6;">Ask Questions About This Contract</h2>', unsafe_allow_html=True)
        
        # Improved question input layout
        st.markdown(
            '<div style="background-color: #1F2937; border-radius: 0.5rem; padding: 1.5rem; border: 1px solid #374151; margin-bottom: 1.5rem;">'
            '<p style="margin-bottom: 1rem;">Enter any question about your contract, and LegalWhiz will provide an answer based on the contract content.</p>'
            '</div>',
            unsafe_allow_html=True
        )
        
        # Question input with better styling
        user_question = st.text_input("Your question:", placeholder="E.g., What's the notice period for termination?")
        
        col1, col2 = st.columns([6, 1])
        with col2:
            # Answer button with better styling
            ask_button = st.button("Ask LegalWhiz", disabled=not user_question)
        
        # Display examples of questions
        if not user_question:
            st.markdown('<p style="color: #9CA3AF; margin-top: 1rem; font-size: 0.9rem;">Example questions:</p>', unsafe_allow_html=True)
            col1, col2 = st.columns(2)
            
            with col1:
                st.markdown(
                    '<ul style="color: #9CA3AF; font-size: 0.9rem;">'
                    '<li>What is the termination clause?</li>'
                    '<li>Can I cancel this contract without penalties?</li>'
                    '<li>What happens if I\'m late with a payment?</li>'
                    '</ul>',
                    unsafe_allow_html=True
                )
            
            with col2:
                st.markdown(
                    '<ul style="color: #9CA3AF; font-size: 0.9rem;">'
                    '<li>Are there any auto-renewal terms?</li>'
                    '<li>What are my obligations under this contract?</li>'
                    '<li>What jurisdiction governs this agreement?</li>'
                    '</ul>',
                    unsafe_allow_html=True
                )
        
        # Process question when button is clicked
        if user_question and ask_button:
            with st.spinner("Finding your answer..."):
                answer = analyzer.answer_question(user_question, st.session_state.extracted_text)
                
                # Display the answer with improved styling
                st.markdown(
                    '<div style="margin-top: 1.5rem;">'
                    '<p style="font-weight: 500; font-size: 1.1rem;">Answer:</p>'
                    '<div style="background-color: #1F2937; border-radius: 0.5rem; padding: 1.5rem; border: 1px solid #374151; border-left: 4px solid #3B82F6;">'
                    + answer +
                    '</div>'
                    '</div>',
                    unsafe_allow_html=True
                )

# Footer with privacy information matching mockup
st.markdown(
    '<div style="margin-top: 30px; border-top: 1px solid #374151; padding-top: 20px;">'
    '<p style="color: #9CA3AF; font-size: 0.85rem;">LegalWhiz analyzes contracts locally and does not store your documents. Your data remains on your device and is not sent to external services.</p>'
    '</div>',
    unsafe_allow_html=True
)