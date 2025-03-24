import streamlit as st
import os
import base64
from mistralai import Mistral
import google.generativeai as genai
from PIL import Image
import io
import requests
import re
import math
import json
# From python-dotenv package:
from dotenv import load_dotenv

# Configure page - MUST BE THE FIRST STREAMLIT COMMAND
st.set_page_config(layout="wide", page_title="TipJar", page_icon="💰")

# Load environment variables from .env file
load_dotenv()

# Add custom CSS for better responsiveness
st.markdown("""
<style>
    /* Hide sidebar completely */
    [data-testid="stSidebar"] {
        display: none !important;
        visibility: hidden !important;
        width: 0 !important;
        margin: 0 !important;
        padding: 0 !important;
    }
    
    /* Ensure main content spans full width */
    .stApp > header + div > div {
        width: 100% !important;
    }
    
    /* Base styles for all devices */
    .stApp {
        max-width: 100%;
        --primary-color: #00704A;
        --accent-color: #f7c36b;
        --secondary-color: #1e3932;
        --light-bg: #f9f9f9;
        --card-shadow: 0 4px 8px rgba(0,0,0,0.08);
        --border-color: #e6e6e6;
    }
    
    /* Professional styling and centering */
    h1 {
        color: var(--primary-color) !important;
        text-align: center !important;
        margin-bottom: 0 !important;
        padding-bottom: 0 !important;
        font-weight: 700 !important;
        font-size: 2.4rem !important;
        letter-spacing: -0.5px;
    }
    
    .caption {
        text-align: center !important;
        color: white !important;
        margin-top: 0 !important;
        padding-top: 0 !important;
    }
    
    .header-container {
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        padding: 1.5rem 0;
        margin-bottom: 2rem;
        border-bottom: 1px solid var(--border-color);
        background: linear-gradient(180deg, var(--primary-color) 0%, var(--secondary-color) 100%);
    }
    
    /* Professional subheadings */
    h2, h3, h4 {
        color: var(--primary-color) !important;
        margin-top: 1.5rem !important;
        margin-bottom: 1rem !important;
        font-weight: 600 !important;
    }
    
    h2 {
        font-size: 1.8rem !important;
        border-bottom: 2px solid var(--accent-color);
        padding-bottom: 0.5rem;
        display: inline-block;
    }
    
    h3 {
        font-size: 1.4rem !important;
    }
    
    /* Custom button styling */
    .stButton > button {
        border-radius: 50px !important;
        background: var(--primary-color) !important;
        color: white !important;
        font-weight: 500 !important;
        padding: 0.5rem 2rem !important;
        border: none !important;
        box-shadow: 0 2px 5px rgba(0,0,0,0.1) !important;
        transition: all 0.2s ease !important;
    }
    
    .stButton > button:hover {
        background: var(--secondary-color) !important;
        box-shadow: 0 4px 8px rgba(0,0,0,0.15) !important;
        transform: translateY(-1px) !important;
    }
    
    .stButton > button:active {
        transform: translateY(1px) !important;
        box-shadow: 0 1px 3px rgba(0,0,0,0.1) !important;
    }
    
    /* Enhanced form controls */
    input[type="text"], input[type="number"], .stSelectbox > div > div {
        border-radius: 8px !important;
        border-color: var(--border-color) !important;
        transition: all 0.2s ease !important;
    }
    
    input[type="text"]:focus, input[type="number"]:focus {
        border-color: var(--primary-color) !important;
        box-shadow: 0 0 0 1px var(--primary-color) !important;
    }
    
    /* Radio buttons - remove white background boxes */
    .stRadio > div {
        background-color: transparent !important;
        border-radius: 0 !important;
        padding: 0.5rem !important;
        box-shadow: none !important;
    }
    
    /* Make radio button labels more visible */
    .stRadio label {
        color: white !important;
        font-weight: 500 !important;
    }
    
    /* Highlight selected radio options */
    .stRadio label[data-baseweb="radio"] input:checked + div {
        border-color: var(--accent-color) !important;
    }
    
    /* Section headers */
    .section-header {
        color: white !important;
        font-weight: 500;
        margin-bottom: 0.5rem;
    }
    
    /* File uploader */
    .stFileUploader > div {
        background-color: white !important;
        border-radius: 10px !important;
        padding: 1rem !important;
        border: 2px dashed var(--border-color) !important;
        transition: all 0.2s ease !important;
    }
    
    .stFileUploader > div:hover {
        border-color: var(--primary-color) !important;
    }
    
    /* Mobile detection and responsive design */
    @media (max-width: 768px) {
        /* Apply mobile styles automatically based on viewport */
        .element-container {
            max-width: 95vw !important;
        }
        
        /* Improve button touch targets */
        button, [role="button"] {
            min-height: 48px !important;
            padding: 12px !important;
        }
        
        /* Better spacing for mobile UI */
        .row-widget.stRadio > div {
            flex-direction: row !important;
            margin-bottom: 10px !important;
        }
        
        /* Ensure font size is legible on mobile */
        .stTextInput input, .stNumberInput input {
            font-size: 16px !important; /* Prevents iOS zoom on focus */
        }
        
        /* Full width containers on mobile */
        .block-container, .css-18e3th9 {
            padding-left: 10px !important;
            padding-right: 10px !important;
            max-width: 95vw !important;
        }
        
        h1 {
            font-size: 2rem !important;
        }
        
        h2 {
            font-size: 1.5rem !important;
        }
    }
    
    /* Enhanced table styling */
    table {
        width: 100%;
        border-collapse: separate;
        border-spacing: 0;
        border-radius: 10px;
        overflow: hidden;
        box-shadow: var(--card-shadow);
    }
    
    table th {
        background-color: var(--secondary-color);
        color: white;
        padding: 12px;
        text-align: left;
        font-weight: 600;
    }
    
    table tr:nth-child(even) {
        background-color: var(--light-bg);
    }
    
    table td {
        padding: 12px;
        border-bottom: 1px solid var(--border-color);
    }
    
    table tr:last-child td {
        border-bottom: none;
    }
    
    /* App description styling */
    .app-description {
        background-color: transparent;
        padding: 15px;
        margin: 20px 0;
        text-align: center;
    }
    
    .app-description ul {
        display: inline-block;
        text-align: left;
        margin: 15px auto;
        padding-left: 20px;
    }
    
    .app-description li {
        margin-bottom: 8px;
        position: relative;
        padding-left: 10px;
    }
    
    .app-description li:before {
        content: "•";
        color: var(--primary-color);
        font-weight: bold;
        position: absolute;
        left: -12px;
    }
    
    /* Visual separator */
    .separator {
        height: 1px;
        background: linear-gradient(90deg, transparent, var(--border-color), transparent);
        margin: 30px auto;
        width: 80%;
    }
    
    /* Policy callout box */
    .policy-box {
        background-color: #f8f9fa;
        border-left: 4px solid var(--accent-color);
        padding: 15px;
        border-radius: 8px;
        margin-bottom: 20px;
        font-size: 0.9rem;
    }
    
    .policy-box strong {
        color: var(--secondary-color);
    }
    
    /* Loading spinner */
    .stSpinner > div {
        border-color: var(--primary-color) transparent;
    }
</style>
""", unsafe_allow_html=True)

# Function to detect if we're on a mobile device (used for conditional layouts)
def is_mobile():
    # Simple width-based detection
    # We'll use a session state variable to track this
    return st.session_state.get('mobile_detected', False)

# Detect device type based on user agent or viewport
if 'mobile_detected' not in st.session_state:
    # Initialize as false - will be detected through viewport size by CSS
    st.session_state['mobile_detected'] = False

    # Add a custom component to allow users to manually toggle mobile view for testing
    # This is hidden in the UI but accessible for debugging if needed
    st.markdown("""
    <div style="display:none">
        <button onclick="
            const isMobile = window.innerWidth < 768;
            window.parent.postMessage({
                type: 'streamlit:setComponentValue',
                value: isMobile
            }, '*');
        ">Auto-detect mobile</button>
    </div>
    """, unsafe_allow_html=True)

# Title section with enhanced visuals
st.markdown('<div class="header-container">', unsafe_allow_html=True)
st.image("https://upload.wikimedia.org/wikipedia/en/thumb/d/d3/Starbucks_Corporation_Logo_2011.svg/150px-Starbucks_Corporation_Logo_2011.svg.png", width=100)
st.markdown('<h1>TipJar</h1>', unsafe_allow_html=True)
st.markdown('<p class="caption">Made by William Walsh</p>', unsafe_allow_html=True)
st.markdown('<p class="caption">Starbucks Store# 69600</p>', unsafe_allow_html=True)
st.markdown('</div>', unsafe_allow_html=True)

# App description with simplified styling
st.markdown('<div class="app-description">', unsafe_allow_html=True)
st.markdown("""
<h3 style="margin-top:0;">Tips Distribution</h3>

**Key features:**
<ul>
<li>📝 Process partner hours from PDF/image input</li>
<li>💰 Calculate individual tips based on hours worked</li>
<li>💵 Distribute bills equitably among partners</li>
<li>📊 Output detailed distribution breakdown per partner</li>
</ul>
""", unsafe_allow_html=True)
st.markdown('</div>', unsafe_allow_html=True)

# Initialize session state variables
if "ocr_result" not in st.session_state:
    st.session_state["ocr_result"] = None
if "preview_src" not in st.session_state:
    st.session_state["preview_src"] = None
if "image_bytes" not in st.session_state:
    st.session_state["image_bytes"] = None
if "tips_calculated" not in st.session_state:
    st.session_state["tips_calculated"] = False
if "week_counter" not in st.session_state:
    st.session_state["week_counter"] = 1
if "tips_history" not in st.session_state:
    st.session_state["tips_history"] = []
if "gemini_chat" not in st.session_state:
    st.session_state["gemini_chat"] = None

# Get API keys from environment variables
MISTRAL_API_KEY = os.getenv("MISTRAL_API_KEY", "")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")

# Choose AI Provider - different layout for mobile vs desktop
if is_mobile():
    # More compact layout for mobile
    st.markdown('<p class="section-header">Select AI Provider:</p>', unsafe_allow_html=True)
    ai_provider = st.radio("", ("Mistral", "Gemini"), horizontal=True, label_visibility="collapsed")
    
    # For mobile, stack the file type and source type selection vertically
    st.markdown('<p class="section-header">File type:</p>', unsafe_allow_html=True)
    file_type = st.radio("", ("PDF", "Image"), horizontal=True, label_visibility="collapsed")
    
    st.markdown('<p class="section-header">Source:</p>', unsafe_allow_html=True)
    source_type = st.radio("", ("URL", "Local Upload"), horizontal=True, label_visibility="collapsed")
else:
    # Desktop layout
    st.markdown('<p class="section-header">Select AI Provider</p>', unsafe_allow_html=True)
    ai_provider = st.radio("", ("Mistral", "Gemini"), label_visibility="collapsed")
    
    # Side-by-side for desktop
    col1, col2 = st.columns(2)
    with col1:
        st.markdown('<p class="section-header">Select file type</p>', unsafe_allow_html=True)
        file_type = st.radio("", ("PDF", "Image"), label_visibility="collapsed")
    with col2:
        st.markdown('<p class="section-header">Select source type</p>', unsafe_allow_html=True)
        source_type = st.radio("", ("URL", "Local Upload"), label_visibility="collapsed")

# Check if selected provider's API key is available
if ai_provider == "Mistral":
    if not MISTRAL_API_KEY:
        st.error("Mistral API key is not configured in the .env file. Please add it and restart the application.")
        st.stop()
else:  # Gemini
    if not GEMINI_API_KEY:
        st.error("Gemini API key is not configured in the .env file. Please add it and restart the application.")
        st.stop()
    
    # Configure Gemini with safety settings
    genai.configure(api_key=GEMINI_API_KEY)
    generation_config = {
        "temperature": 0.7,
        "top_p": 0.9,
        "top_k": 40,
        "max_output_tokens": 2048,
    }
    safety_settings = [
        {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
        {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
        {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
        {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
    ]

input_url = ""
uploaded_file = None

# URL or upload section - adapt based on device type
if source_type == "URL":
    if file_type == "PDF":
        input_url = st.text_input("Enter PDF URL")
    else:
        input_url = st.text_input("Enter Image URL")
else:
    if file_type == "PDF":
        uploaded_file = st.file_uploader("Upload a PDF file", type=["pdf"])
    else:
        uploaded_file = st.file_uploader("Upload an Image file", type=["jpg", "jpeg", "png"])

# Process Button & OCR Handling
if st.button("Process", use_container_width=is_mobile()):
    if source_type == "URL" and not input_url:
        st.error("Please enter a valid URL.")
    elif source_type == "Local Upload" and not uploaded_file:
        st.error("Please upload a file.")
    else:
        with st.spinner("Processing the document..."):
            if ai_provider == "Mistral":
                client = Mistral(api_key=MISTRAL_API_KEY)
                # Existing Mistral processing code
                if file_type == "PDF":
                    if source_type == "URL":
                        document = {
                            "type": "document_url",
                            "document_url": input_url
                        }
                        preview_src = input_url
                    else:
                        file_bytes = uploaded_file.read()
                        encoded_pdf = base64.b64encode(file_bytes).decode("utf-8")
                        preview_src = f"data:application/pdf;base64,{encoded_pdf}"
                        document = {
                            "type": "document_url",
                            "document_url": preview_src
                        }
                        st.session_state["image_bytes"] = file_bytes
                else:  # Image
                    if source_type == "URL":
                        document = {
                            "type": "image_url",
                            "image_url": input_url
                        }
                        preview_src = input_url
                    else:
                        file_bytes = uploaded_file.read()
                        mime_type = uploaded_file.type
                        encoded_image = base64.b64encode(file_bytes).decode("utf-8")
                        document = {
                            "type": "image_url",
                            "image_url": f"data:{mime_type};base64,{encoded_image}"
                        }
                        preview_src = f"data:{mime_type};base64,{encoded_image}"
                        st.session_state["image_bytes"] = file_bytes

                ocr_response = client.ocr.process(
                    model="mistral-ocr-latest",
                    document=document,
                    include_image_base64=True
                )
                try:
                    if hasattr(ocr_response, "pages"):
                        pages = ocr_response.pages
                    elif isinstance(ocr_response, list):
                        pages = ocr_response
                    else:
                        pages = []
                    result_text = "\n\n".join(page.markdown for page in pages)
                    if not result_text:
                        result_text = "No text found in the document."
                except Exception as e:
                    result_text = f"Error extracting text: {str(e)}"

            else:  # Gemini
                try:
                    if file_type == "Image":
                        # Initialize Gemini 1.5 Flash model for vision tasks
                        model = genai.GenerativeModel(
                            'gemini-1.5-flash',
                            generation_config=generation_config,
                            safety_settings=safety_settings
                        )
                        
                        if source_type == "Local Upload":
                            # Store the original file bytes for preview
                            st.session_state["image_bytes"] = uploaded_file.read()
                            image = Image.open(io.BytesIO(st.session_state["image_bytes"]))
                            preview_src = None
                        else:  # URL
                            response = requests.get(input_url)
                            st.session_state["image_bytes"] = response.content
                            image = Image.open(io.BytesIO(response.content))
                            preview_src = input_url
                        
                        # Create structured prompt for better OCR
                        prompt = """Please analyze this image and:
                        1. Extract all visible text, especially focusing on names and hours worked
                        2. Maintain the original formatting and structure
                        3. Preserve any important visual context
                        4. Make sure to clearly identify all partner/employee names and their corresponding hours
                        
                        Extract and format the text clearly:"""
                        
                        response = model.generate_content([prompt, image])
                        response.resolve()
                        result_text = response.text

                    else:  # PDF
                        st.error("PDF processing with Gemini is not supported yet. Please use Mistral for PDFs.")
                        st.stop()
                    
                    # Initialize chat model for processing with Gemini 1.5 Pro
                    st.session_state["gemini_chat"] = genai.GenerativeModel(
                        'gemini-1.5-pro',
                        generation_config=generation_config,
                        safety_settings=safety_settings
                    ).start_chat(history=[])
                    
                except Exception as e:
                    st.error(f"Error processing with Gemini: {str(e)}")
                    st.stop()
            
            st.session_state["ocr_result"] = result_text
            st.session_state["preview_src"] = preview_src
            st.session_state["tips_calculated"] = False

# Display Preview and OCR Result
if st.session_state["ocr_result"]:
    # Use different layouts for mobile and desktop
    if is_mobile():
        # For mobile: stack the preview and OCR result vertically
        st.subheader("Preview")
        if file_type == "PDF":
            try:
                # For PDFs, use object tag with mobile-friendly height
                pdf_embed_html = f'''
                    <object data="{st.session_state["preview_src"]}" 
                            type="application/pdf" 
                            width="100%" 
                            height="400">
                        <p>Unable to display PDF file. <a href="{st.session_state["preview_src"]}">Download</a> instead.</p>
                    </object>
                '''
                st.markdown(pdf_embed_html, unsafe_allow_html=True)
            except Exception as e:
                st.error(f"Error displaying PDF: {str(e)}")
        else:
            # For images on mobile, limit height
            if source_type == "Local Upload" and st.session_state["image_bytes"]:
                st.image(st.session_state["image_bytes"], use_column_width=True)
            else:
                st.image(st.session_state["preview_src"], use_column_width=True)
        
        st.subheader("Extracted Hours Data")
        st.write(st.session_state["ocr_result"])
    
    else:
        # For desktop: use columns for side-by-side view
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("Preview")
            if file_type == "PDF":
                try:
                    # For PDFs, use object tag
                    pdf_embed_html = f'''
                        <object data="{st.session_state["preview_src"]}" 
                                type="application/pdf" 
                                width="100%" 
                                height="800">
                            <p>Unable to display PDF file. <a href="{st.session_state["preview_src"]}">Download</a> instead.</p>
                        </object>
                    '''
                    st.markdown(pdf_embed_html, unsafe_allow_html=True)
                except Exception as e:
                    st.error(f"Error displaying PDF: {str(e)}")
            else:
                # For images, display using st.image
                if source_type == "Local Upload" and st.session_state["image_bytes"]:
                    st.image(st.session_state["image_bytes"])
                else:
                    st.image(st.session_state["preview_src"])
        
        with col2:
            st.subheader("Extracted Hours Data")
            st.write(st.session_state["ocr_result"])
    
    # Extract partner data with AI assistance
    if st.button("Extract Partner Data", use_container_width=is_mobile()):
        with st.spinner("Extracting partner data..."):
            try:
                if ai_provider == "Mistral":
                    client = Mistral(api_key=MISTRAL_API_KEY)
                    prompt = f"""
                    From the following text, extract partner names and their hours worked. Format as JSON:
                    
                    {st.session_state["ocr_result"]}
                    
                    Return a JSON array of objects with 'name' and 'hours' fields. Example:
                    [
                        {{"name": "John Smith", "hours": 32.5}},
                        {{"name": "Jane Doe", "hours": 28.75}}
                    ]
                    
                    Only include valid partners with hours. Output ONLY the JSON array, nothing else.
                    """
                    
                    chat_response = client.chat.complete(
                        model="mistral-large-latest",
                        messages=[{"role": "user", "content": prompt}]
                    )
                    partner_data_str = chat_response.choices[0].message.content
                    
                    # Also extract the total tippable hours from the document if available
                    total_hours_prompt = f"""
                    From the following text, extract ONLY the total tippable hours (or total hours) mentioned in the document.
                    Return ONLY the number. If you find multiple totals, return the one that's labeled as "Total Tippable Hours" or similar.
                    
                    {st.session_state["ocr_result"]}
                    """
                    
                    total_hours_response = client.chat.complete(
                        model="mistral-large-latest",
                        messages=[{"role": "user", "content": total_hours_prompt}]
                    )
                    document_total_hours_str = total_hours_response.choices[0].message.content.strip()
                    
                else:  # Gemini
                    prompt = f"""
                    From the following text, extract partner names and their hours worked. Format as JSON:
                    
                    {st.session_state["ocr_result"]}
                    
                    Return a JSON array of objects with 'name' and 'hours' fields. Example:
                    [
                        {{"name": "John Smith", "hours": 32.5}},
                        {{"name": "Jane Doe", "hours": 28.75}}
                    ]
                    
                    Only include valid partners with hours. Output ONLY the JSON array, nothing else.
                    """
                    
                    response = st.session_state["gemini_chat"].send_message(prompt)
                    partner_data_str = response.text
                    
                    # Also extract the total tippable hours from the document if available
                    total_hours_prompt = f"""
                    From the following text, extract ONLY the total tippable hours (or total hours) mentioned in the document.
                    Return ONLY the number. If you find multiple totals, return the one that's labeled as "Total Tippable Hours" or similar.
                    
                    {st.session_state["ocr_result"]}
                    """
                    
                    total_hours_response = st.session_state["gemini_chat"].send_message(total_hours_prompt)
                    document_total_hours_str = total_hours_response.text.strip()
                
                # Extract the JSON from the response
                pattern = r'\[\s*{.*}\s*\]'
                json_match = re.search(pattern, partner_data_str, re.DOTALL)
                
                if json_match:
                    partner_data_str = json_match.group(0)
                
                partner_data = json.loads(partner_data_str)
                
                # Add partner numbers
                for i, partner in enumerate(partner_data):
                    partner["number"] = i + 1
                
                st.session_state["partner_data"] = partner_data
                
                # Calculate total hours
                total_hours = sum(float(partner["hours"]) for partner in partner_data)
                st.session_state["total_hours"] = total_hours
                
                # Display partner data
                st.write(f"Total Hours: {total_hours}")
                st.write("Partner Data:")
                for partner in partner_data:
                    st.write(f"{partner['name']} - {partner['hours']} hours")
                
                # Compare with document's total hours if available
                try:
                    # Clean up the extracted total hours string
                    document_total_hours_str = re.sub(r'[^\d.]', '', document_total_hours_str)
                    if document_total_hours_str:
                        document_total_hours = float(document_total_hours_str)
                        st.session_state["document_total_hours"] = document_total_hours
                        
                        # Display the comparison
                        st.markdown("### Hours Validation")
                        
                        if abs(document_total_hours - total_hours) < 0.01:  # Small threshold for float comparison
                            st.success(f"✅ Validation passed! Document total ({document_total_hours}) matches calculated total ({total_hours}).")
                        else:
                            st.warning(f"⚠️ Validation check: Document shows {document_total_hours} total hours, but calculated total is {total_hours}.")
                            st.info("This discrepancy might be due to OCR errors or missing partners. Please verify manually.")
                except Exception as e:
                    st.info("Could not extract or validate total hours from the document.")
                
            except Exception as e:
                st.error(f"Error extracting partner data: {str(e)}")
                st.error("Please try again or manually enter partner data.")
    
    # Manual Partner Data Entry Option - make more mobile-friendly
    with st.expander("Or Manually Enter Partner Data"):
        num_partners = st.number_input("Number of Partners", min_value=1, max_value=20, value=3)
        manual_partner_data = []
        
        for i in range(num_partners):
            # Different column layout for mobile vs desktop
            if is_mobile():
                # Stack fields vertically on mobile
                name = st.text_input(f"Partner {i+1} Name", key=f"name_{i}")
                hours = st.number_input(f"Partner {i+1} Hours", min_value=0.0, step=0.25, key=f"hours_{i}")
            else:
                # Side-by-side on desktop
                col1, col2 = st.columns(2)
                with col1:
                    name = st.text_input(f"Partner {i+1} Name", key=f"name_{i}")
                with col2:
                    hours = st.number_input(f"Partner {i+1} Hours", min_value=0.0, step=0.25, key=f"hours_{i}")
            
            if name:  # Only add if name is provided
                manual_partner_data.append({"name": name, "number": i+1, "hours": hours})
        
        if st.button("Save Partner Data", use_container_width=is_mobile()):
            if all(partner["name"] for partner in manual_partner_data):
                st.session_state["partner_data"] = manual_partner_data
                st.session_state["total_hours"] = sum(float(partner["hours"]) for partner in manual_partner_data)
                st.success("Partner data saved successfully!")
            else:
                st.error("Please provide names for all partners.")
    
    # Tip Allocation Section
    if "partner_data" in st.session_state and not st.session_state["tips_calculated"]:
        st.subheader("Tip Allocation")
        total_tip_amount = st.number_input("Enter total tip amount for the week: $", min_value=0.0, step=10.0)
        
        if st.button("Calculate Tips", use_container_width=is_mobile()):
            if total_tip_amount > 0:
                # Process Week Counter
                if "week_counter" not in st.session_state:
                    st.session_state["week_counter"] = 1
                
                # Calculate individual tips
                partner_data = st.session_state["partner_data"]
                total_hours = st.session_state["total_hours"]
                
                for partner in partner_data:
                    # Calculate exact tip amount (hours/total_hours * total_tips)
                    exact_amount = (float(partner["hours"]) / total_hours) * total_tip_amount
                    # Store both exact and rounded amounts
                    partner["exact_tip_amount"] = exact_amount
                    # Calculate hourly rate
                    partner["hourly_rate"] = exact_amount / float(partner["hours"])
                    # Round to nearest dollar (Starbucks policy)
                    # Examples: $23.89 rounds to $24, $12.12 rounds to $12
                    partner["tip_amount"] = round(exact_amount)
                
                # Add a note about the rounding policy
                st.info("Following Starbucks policy, tip amounts are rounded to the nearest dollar for simplicity in distribution.")
                
                # Distribute bills
                denominations = [20, 10, 5, 1]
                
                # Determine starting partner index based on rotation
                num_partners = len(partner_data)
                start_index = (st.session_state["week_counter"] - 1) % num_partners
                
                # Process each partner's distribution
                remaining_amounts = {}
                for partner in partner_data:
                    remaining_amounts[partner["number"]] = partner["tip_amount"]
                
                # Initialize bill counts for each partner
                for partner in partner_data:
                    partner["bills"] = {20: 0, 10: 0, 5: 0, 1: 0}
                
                # Distribute by denomination, starting with largest
                for denomination in denominations:
                    # Create an order of partners, starting with the rotation partner
                    partner_order = [(start_index + i) % num_partners for i in range(num_partners)]
                    
                    # Keep distributing bills of this denomination while possible
                    while True:
                        distributed = False
                        for idx in partner_order:
                            partner_num = partner_data[idx]["number"]
                            if remaining_amounts[partner_num] >= denomination:
                                # Give this partner a bill of this denomination
                                partner_data[idx]["bills"][denomination] += 1
                                remaining_amounts[partner_num] -= denomination
                                distributed = True
                        
                        # If we couldn't distribute any more of this denomination, move to next
                        if not distributed:
                            break
                
                # Add the bill distribution to each partner's data
                for partner in partner_data:
                    bills_text = []
                    for denom in [20, 10, 5, 1]:
                        if partner["bills"][denom] > 0:
                            bills_text.append(f"{partner['bills'][denom]}x${denom}")
                    
                    partner["bills_text"] = ",".join(bills_text)
                    
                    # Format for copy-paste
                    partner["formatted_output"] = (
                        f"Partner Name: {partner['name']} | #: {partner['number']} | "
                        f"Hours: {partner['hours']} | Rate: ${partner['hourly_rate']:.2f}/hr | "
                        f"Exact: ${partner['exact_tip_amount']:.2f} | "
                        f"Rounded: ${partner['tip_amount']} | Bills: {partner['bills_text']}"
                    )
                
                # Save to session state
                st.session_state["distributed_tips"] = partner_data
                st.session_state["total_tip_amount"] = total_tip_amount
                st.session_state["tips_calculated"] = True
                
                # Increment week counter for the next allocation
                st.session_state["week_counter"] += 1
            else:
                st.error("Please enter a valid tip amount.")
    
    # Display Tip Distribution Results
    if st.session_state.get("tips_calculated", False):
        st.markdown('<div class="separator"></div>', unsafe_allow_html=True)
        st.markdown('<h2 style="text-align:center;">Tip Distribution Results</h2>', unsafe_allow_html=True)
        
        # Add explanation about rounding policy with enhanced styling
        st.markdown("""
        <div class="policy-box">
            <strong>🔄 Rounding Policy:</strong> Following Starbucks standard practice, tip amounts are rounded to the nearest dollar.
            For example, $23.89 rounds up to $24, while $12.12 rounds down to $12.
        </div>
        """, unsafe_allow_html=True)
        
        # Adapt table display for mobile
        tip_data = []
        for partner in st.session_state["distributed_tips"]:
            tip_data.append({
                "Partner Name": partner["name"],
                "#": partner["number"],
                "Hours": partner["hours"],
                "Hourly Rate": f"${partner['hourly_rate']:.2f}",
                "Exact Amount": f"${partner['exact_tip_amount']:.2f}",
                "Rounded": f"${partner['tip_amount']}",
                "Bills": partner["bills_text"]
            })
        
        # For mobile, use simplified view
        if is_mobile():
            for partner in tip_data:
                with st.container():
                    st.markdown(f"""
                    <div style="margin-bottom: 15px; padding: 10px; border-left: 4px solid var(--primary-color);">
                        <h4 style="margin: 0; color: var(--primary-color);">👤 {partner['Partner Name']} <span style="color: #666; font-size: 0.9em;">#{partner['#']}</span></h4>
                        <div style="font-size: 1.5rem; font-weight: bold; color: var(--secondary-color);">{partner['Rounded']}</div>
                        <div style="display: flex; justify-content: space-between; color: #666; font-size: 0.9rem; margin-top: 5px;">
                            <div>{partner['Hours']} hours</div>
                            <div>Rate: {partner['Hourly Rate']}/hr</div>
                        </div>
                        <hr style="margin: 10px 0; border: 0; height: 1px; background: #eee;">
                        <div style="display: flex; justify-content: space-between; color: #666; font-size: 0.9rem; margin-top: 5px;">
                            <div>
                                <span style="color: #666;">Exact: ${"{:.2f}".format(float(partner['Exact Amount'][1:]))}</span>
                            </div>
                            <div>💵 {partner['Bills']}</div>
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
        else:
            # Desktop gets the enhanced table
            st.table(tip_data)
        
        # Save distribution to history with improved button styling
        col1, col2, col3 = st.columns([1,2,1])
        with col2:
            if st.button("💾 Save to History", use_container_width=True):
                distribution = {
                    "week": st.session_state["week_counter"] - 1,
                    "total_amount": st.session_state["total_tip_amount"],
                    "total_hours": st.session_state["total_hours"],
                    "partners": st.session_state["distributed_tips"]
                }
                
                if "tips_history" not in st.session_state:
                    st.session_state["tips_history"] = []
                
                st.session_state["tips_history"].append(distribution)
                st.success("✅ Distribution saved to history!")
    
    # History section with enhanced styling
    if "tips_history" in st.session_state and st.session_state["tips_history"]:
        st.markdown('<div class="separator"></div>', unsafe_allow_html=True)
        with st.expander("📜 View Distribution History"):
            for i, dist in enumerate(st.session_state["tips_history"]):
                st.markdown(f"""
                <div style="margin-bottom: 20px;">
                    <h3 style="margin-top:0;">Week {dist['week']}</h3>
                    <p><strong>Total:</strong> ${dist['total_amount']} for {dist['total_hours']} hours</p>
                    <div style="background-color: var(--light-bg); border-radius: 8px; padding: 10px; margin-top: 10px;">
                """, unsafe_allow_html=True)
                
                for partner in dist["partners"]:
                    st.markdown(f"""
                    <p style="margin: 5px 0; padding-bottom: 5px; border-bottom: 1px solid #eee;">
                        <span style="font-weight: 500;">{partner['name']}</span> | 
                        #{partner['number']} | 
                        {partner['hours']} hrs | 
                        <span style="color: var(--primary-color); font-weight: 500;">${partner['tip_amount']}</span> | 
                        <span style="color: #666; font-size: 0.9em;">{partner['bills_text']}</span>
                    </p>
                    """, unsafe_allow_html=True)
                
                st.markdown("</div></div>", unsafe_allow_html=True)
    
    # Footer with improved styling
    st.markdown('<div class="separator"></div>', unsafe_allow_html=True)
    st.markdown("""
    <div style="text-align: center; color: #666; padding: 10px; font-size: 0.8em;">
        <p>TipJar | &copy; 2023-2024 | Designed for Starbucks Partners</p>
        <p style="font-size: 0.9em;">💰 Making tip distribution fair and transparent</p>
    </div>
    """, unsafe_allow_html=True)

    # Download link for OCR result with improved styling
    if st.session_state.get("ocr_result"):
        b64 = base64.b64encode(st.session_state["ocr_result"].encode()).decode()
        st.markdown(f"""
        <div style="text-align: center; margin-top: 20px;">
            <a href="data:file/txt;base64,{b64}" 
               download="ocr_result.txt"
               style="text-decoration: none; color: var(--primary-color); font-size: 0.9em;">
               📄 Download OCR Result
            </a>
        </div>
        """, unsafe_allow_html=True) 