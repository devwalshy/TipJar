import streamlit as st
import os
import base64
from mistralai import Mistral
import google.generativeai as genai
from PIL import Image
import io
import requests

# Configure page
st.set_page_config(layout="wide", page_title="Document OCR & QA App", page_icon="🖥️")
st.title("Document OCR & Question Answering App")
with st.expander("Expand Me"):
    st.markdown("""
    This application allows you to extract information from pdf/image and ask questions about the content using either Mistral or Gemini AI.
    """)

# Initialize session state variables
if "ocr_result" not in st.session_state:
    st.session_state["ocr_result"] = None
if "preview_src" not in st.session_state:
    st.session_state["preview_src"] = None
if "image_bytes" not in st.session_state:
    st.session_state["image_bytes"] = None
if "qa_history" not in st.session_state:
    st.session_state["qa_history"] = []
if "gemini_chat" not in st.session_state:
    st.session_state["gemini_chat"] = None

# Choose AI Provider
ai_provider = st.radio("Select AI Provider", ("Mistral", "Gemini"))

# API Key Input based on provider
if ai_provider == "Mistral":
    api_key = st.text_input("Enter your Mistral API Key", type="password")
    if not api_key:
        st.info("Please enter your Mistral API key to continue.")
        st.stop()
else:
    gemini_key = st.text_input("Enter your Google Gemini API Key", type="password")
    if not gemini_key:
        st.info("Please enter your Gemini API key to continue.")
        st.stop()
    
    # Configure Gemini with safety settings
    genai.configure(api_key=gemini_key)
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

# File type and source selection
file_type = st.radio("Select file type", ("PDF", "Image"))
source_type = st.radio("Select source type", ("URL", "Local Upload"))

input_url = ""
uploaded_file = None

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
if st.button("Process"):
    if source_type == "URL" and not input_url:
        st.error("Please enter a valid URL.")
    elif source_type == "Local Upload" and not uploaded_file:
        st.error("Please upload a file.")
    else:
        with st.spinner("Processing the document..."):
            if ai_provider == "Mistral":
                client = Mistral(api_key=api_key)
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
                        1. Extract all visible text
                        2. Maintain the original formatting and structure
                        3. Preserve any important visual context
                        4. Include any relevant details about text layout or positioning
                        
                        Extract and format the text clearly:"""
                        
                        response = model.generate_content([prompt, image])
                        response.resolve()
                        result_text = response.text

                    else:  # PDF
                        st.error("PDF processing with Gemini is not supported yet. Please use Mistral for PDFs.")
                        st.stop()
                    
                    # Initialize chat model for QA with Gemini 1.5 Pro
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

# Display Preview and OCR Result
if st.session_state["ocr_result"]:
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("Preview")
        if file_type == "PDF":
            try:
                # For PDFs, use object tag instead of iframe for better compatibility
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
        st.subheader("OCR Result")
        st.write(st.session_state["ocr_result"])
        
        # Question answering section
        st.subheader("Ask Questions")
        user_question = st.text_input("Ask a question about the document:")
        
        if user_question:
            with st.spinner("Generating answer..."):
                try:
                    if ai_provider == "Mistral":
                        client = Mistral(api_key=api_key)
                        prompt = f"""Context: {st.session_state["ocr_result"]}
                        
                        Question: {user_question}
                        
                        Please provide a clear and concise answer based on the context above."""
                        
                        chat_response = client.chat.complete(
                            model="mistral-large-latest",
                            messages=[
                                {
                                    "role": "user",
                                    "content": prompt
                                }
                            ]
                        )
                        answer = chat_response.choices[0].message.content
                    else:  # Gemini
                        # Use the chat model for better context retention
                        prompt = f"""Based on this context: {st.session_state["ocr_result"]}
                        
                        Answer this question: {user_question}
                        
                        Provide a clear and accurate answer using only the information from the context."""
                        
                        response = st.session_state["gemini_chat"].send_message(prompt)
                        answer = response.text
                    
                    st.session_state["qa_history"].append({"question": user_question, "answer": answer})
                    
                except Exception as e:
                    st.error(f"Error generating answer: {str(e)}")
        
        # Display QA history
        if st.session_state["qa_history"]:
            st.subheader("Question & Answer History")
            for qa in st.session_state["qa_history"]:
                st.write(f"Q: {qa['question']}")
                st.write(f"A: {qa['answer']}")
                st.markdown("---")
        
        # Download link for OCR result
        b64 = base64.b64encode(st.session_state["ocr_result"].encode()).decode()
        href = f'<a href="data:file/txt;base64,{b64}" download="ocr_result.txt">Download OCR Result</a>'
        st.markdown(href, unsafe_allow_html=True) 