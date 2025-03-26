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
    }
    
    /* Mobile detection and responsive design */
    @media (max-width: 768px) {
        /* Apply mobile styles automatically based on viewport */
        .element-container {
            max-width: 95vw !important;
        }
        
        /* Improve button touch targets */
        button, [role="button"] {
            min-height: 44px !important;
            padding: 10px !important;
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
    }
    
    /* Starbucks brand styling */
    .stButton button {
        border-radius: 20px;
        background-color: #00704A !important;
        color: white !important;
        font-weight: 500;
    }
    
    /* Custom text colors */
    h1, h2, h3 {
        color: #00704A !important;
    }
    
    /* Consistent table styling */
    table {
        width: 100%;
    }
    
    /* Container styling */
    .custom-card {
        border: 1px solid rgba(49, 51, 63, 0.2);
        border-radius: 10px;
        padding: 10px;
        margin-bottom: 10px;
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

# Title section with centered elements for all devices
st.markdown("""
<div style="display: flex; flex-direction: column; align-items: center; justify-content: center; margin-bottom: 1rem;">
    <img src="https://upload.wikimedia.org/wikipedia/en/thumb/d/d3/Starbucks_Corporation_Logo_2011.svg/150px-Starbucks_Corporation_Logo_2011.svg.png" width="100" style="margin-bottom: 0.5rem;">
    <h1 style="margin: 0.5rem 0; color: #00704A; text-align: center;">TipJar</h1>
    <p style="margin: 0.2rem 0; color: #444; text-align: center;">Made by William Walsh</p>
    <p style="margin: 0.2rem 0; color: #444; text-align: center;">Starbucks Store# 69600</p>
</div>
""", unsafe_allow_html=True)

st.markdown("""<div style="font-size: 1.5rem; font-style: italic; margin: 1.5rem 0; color: #00704A; text-align: center;">\"If theres a Will, Theres a Way!\" -Lauren 2025</div>""", unsafe_allow_html=True)
st.markdown("""
Key functions:
1. Process partner hours from PDF/image input
2. Calculate individual tips based on hours worked
3. Distribute bills equitably among partners
4. Output detailed distribution breakdown per partner
""")

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
    ai_provider = st.radio("Select AI Provider:", ("Mistral", "Gemini"), horizontal=True)
    
    # For mobile, stack the file type and source type selection vertically
    file_type = st.radio("File type:", ("PDF", "Image"), horizontal=True)
    source_type = st.radio("Source:", ("URL", "Local Upload"), horizontal=True)
else:
    # Desktop layout
    ai_provider = st.radio("Select AI Provider", ("Mistral", "Gemini"))
    
    # Side-by-side for desktop
    col1, col2 = st.columns(2)
    with col1:
        file_type = st.radio("Select file type", ("PDF", "Image"))
    with col2:
        source_type = st.radio("Select source type", ("URL", "Local Upload"))

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
                
                # Calculate hourly tip rate - DO NOT round this
                hourly_rate = total_tip_amount / total_hours
                
                for partner in partner_data:
                    # Calculate exact tip amount (hours * hourly_rate)
                    exact_amount = float(partner["hours"]) * hourly_rate
                    
                    # Store the exact amount without rounding
                    partner["raw_tip_amount"] = exact_amount
                    
                    # Store the amount rounded to cents (e.g., $43.1725 → $43.17)
                    partner["exact_tip_amount"] = round(exact_amount, 2)
                    
                    # Round to nearest dollar for cash distribution (e.g., $43.17 → $43)
                    partner["tip_amount"] = round(partner["exact_tip_amount"])
                
                # Add information about the hourly rate and rounding policy
                st.info(f"""
                **Hourly Rate**: ${hourly_rate:.2f} per hour
                
                **Rounding Policy**: 
                1. First calculate exact amount (hours × hourly rate)
                2. Round to cents (e.g., $43.1725 → $43.17)
                3. Round to nearest dollar for cash distribution (e.g., $43.17 → $43)
                """)
                
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
                        f"Hours: {partner['hours']} | Exact: ${partner['exact_tip_amount']:.2f} | "
                        f"Rounded: ${partner['tip_amount']} | Bills: {partner['bills_text']}"
                    )
                
                # Save to session state
                st.session_state["distributed_tips"] = partner_data
                st.session_state["total_tip_amount"] = total_tip_amount
                st.session_state["hourly_rate"] = hourly_rate
                st.session_state["tips_calculated"] = True
                
                # Increment week counter for the next allocation
                st.session_state["week_counter"] += 1
            else:
                st.error("Please enter a valid tip amount.")
    
    # Display Tip Distribution Results
    if st.session_state.get("tips_calculated", False):
        st.subheader("Tip Distribution Results")
        
        # Display the hourly rate
        st.markdown(f"**Hourly Rate**: ${st.session_state['hourly_rate']:.2f} per hour")
        
        # Add explanation about rounding policy
        st.markdown("""
        <div style="background-color: #f8f9fa; padding: 10px; border-radius: 5px; margin-bottom: 15px;">
            <strong>Rounding Policy:</strong> Tip amounts are calculated precisely, rounded to cents, and then to the nearest dollar for cash distribution.
            For example, 24.67 hours × $1.75/hour = $43.1725 → rounded to $43.17 → cash distribution of $43.
        </div>
        """, unsafe_allow_html=True)
        
        # Adapt table display for mobile
        tip_data = []
        for partner in st.session_state["distributed_tips"]:
            tip_data.append({
                "Partner Name": partner["name"],
                "#": partner["number"],
                "Hours": partner["hours"],
                "Amount (Cents)": f"${partner['exact_tip_amount']:.2f}",
                "Amount (Cash)": f"${partner['tip_amount']}",
                "Bills": partner["bills_text"]
            })
        
        # For mobile, we can use a simplified view
        if is_mobile():
            for partner in tip_data:
                with st.container():
                    st.markdown(f"""
                    <div class="custom-card">
                        <h4 style="margin: 0; color: #00704A;">{partner['Partner Name']} <span style="color: #666;">#{partner['#']}</span></h4>
                        <div style="display: flex; justify-content: space-between; margin-top: 5px;">
                            <div>{partner['Hours']} hours</div>
                            <div>
                                <span style="font-weight: bold;">{partner['Amount (Cents)']}</span> → 
                                <span style="color: #00704A; font-weight: bold;">{partner['Amount (Cash)']}</span>
                            </div>
                        </div>
                        <div style="margin-top: 5px;">
                            <small>Bills: {partner['Bills']}</small>
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
        else:
            # Desktop gets the full table
            st.table(tip_data)
        
        # Display copy-paste ready format
        st.subheader("Copy-paste ready format:")
        for partner in st.session_state["distributed_tips"]:
            st.text(partner["formatted_output"])
        
        # Save distribution to history
        if st.button("Save to History", use_container_width=is_mobile()):
            distribution = {
                "week": st.session_state["week_counter"] - 1,
                "total_amount": st.session_state["total_tip_amount"],
                "total_hours": st.session_state["total_hours"],
                "partners": st.session_state["distributed_tips"]
            }
            
            if "tips_history" not in st.session_state:
                st.session_state["tips_history"] = []
            
            st.session_state["tips_history"].append(distribution)
            st.success("Distribution saved to history!")
    
    # History section
    if "tips_history" in st.session_state and st.session_state["tips_history"]:
        with st.expander("View Distribution History"):
            for i, dist in enumerate(st.session_state["tips_history"]):
                st.write(f"### Week {dist['week']}")
                st.write(f"Total: ${dist['total_amount']} for {dist['total_hours']} hours")
                
                for partner in dist["partners"]:
                    st.write(f"{partner['name']} | #{partner['number']} | {partner['hours']} hours | ${partner['tip_amount']} | {partner['bills_text']}")
                
                st.markdown("---")
    
    # Download link for OCR result
    b64 = base64.b64encode(st.session_state["ocr_result"].encode()).decode()
    href = f'<a href="data:file/txt;base64,{b64}" download="ocr_result.txt">Download OCR Result</a>'
    st.markdown(href, unsafe_allow_html=True) 

# Add Starbucks-themed footer
st.markdown("---")
st.markdown(
    """
    <div style="text-align: center; color: #00704A; margin-top: 30px;">
        <p>TipJar v1.2 | Made with 💚 by William Walsh</p>
        <p>Starbucks Store# 69600</p>
    </div>
    """, 
    unsafe_allow_html=True
) 