import gradio as gr
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
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Get API keys from environment variables
MISTRAL_API_KEY = os.getenv("MISTRAL_API_KEY", "")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")

# Mobile viewport meta tag
MOBILE_META = """
<meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
<meta name="theme-color" content="#00704A">
<meta name="apple-mobile-web-app-capable" content="yes">
<meta name="mobile-web-app-capable" content="yes">
"""

# Configure Gemini
def setup_gemini():
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
    return generation_config, safety_settings

# Function to process document with Mistral
def process_with_mistral(file_path, file_type, is_url=False):
    client = Mistral(api_key=MISTRAL_API_KEY)
    
    if is_url:
        document = {
            "type": "document_url",
            "document_url": file_path
        }
    else:
        # For local files
        if file_type == "pdf":
            with open(file_path, "rb") as f:
                file_bytes = f.read()
            encoded_file = base64.b64encode(file_bytes).decode("utf-8")
            document = {
                "type": "document_base64",
                "document_base64": {
                    "data": encoded_file,
                    "mime_type": "application/pdf"
                }
            }
        else:  # image
            with open(file_path, "rb") as f:
                file_bytes = f.read()
            encoded_file = base64.b64encode(file_bytes).decode("utf-8")
            document = {
                "type": "document_base64",
                "document_base64": {
                    "data": encoded_file,
                    "mime_type": "image/jpeg" if file_path.endswith(('.jpg', '.jpeg')) else "image/png"
                }
            }
    
    # Prompt for extracting hour information
    prompt = """
    Extract partner work hours from this document. Output should be in JSON format with:
    1. Each partner's name as key
    2. Their total hours as value
    Example: {"John Doe": 25.5, "Jane Smith": 32.0}
    Only include partners with hours worked. Round to nearest quarter hour.
    """
    
    # Call Mistral API
    try:
        response = client.chat(
            messages=[
                {"role": "user", "content": prompt}
            ],
            tools=[document]
        )
        result = response.choices[0].message.content
        return result
    except Exception as e:
        return f"Error processing with Mistral: {str(e)}"

# Function to process document with Gemini
def process_with_gemini(file_path, file_type, is_url=False):
    generation_config, safety_settings = setup_gemini()
    
    # Process the file
    if is_url:
        try:
            response = requests.get(file_path)
            if file_type == "pdf":
                file_bytes = response.content
            else:  # image
                image = Image.open(io.BytesIO(response.content))
        except Exception as e:
            return f"Error fetching URL: {str(e)}"
    else:
        # Local file
        try:
            if file_type == "pdf":
                with open(file_path, "rb") as f:
                    file_bytes = f.read()
            else:  # image
                image = Image.open(file_path)
        except Exception as e:
            return f"Error opening file: {str(e)}"
    
    # Prompt for extracting hour information
    prompt = """
    Extract partner work hours from this document. Output should be in JSON format with:
    1. Each partner's name as key
    2. Their total hours as value
    Example: {"John Doe": 25.5, "Jane Smith": 32.0}
    Only include partners with hours worked. Round to nearest quarter hour.
    """
    
    # Call Gemini API
    try:
        if file_type == "pdf":
            # For PDFs, we'd need to use text extraction first
            # This is a simplified approach
            return "PDF processing with Gemini is not implemented in this demo."
        else:
            # For images
            model = genai.GenerativeModel('gemini-pro-vision',
                                          generation_config=generation_config,
                                          safety_settings=safety_settings)
            response = model.generate_content([prompt, image])
            return response.text
    except Exception as e:
        return f"Error processing with Gemini: {str(e)}"

# Function to calculate tips based on hours
def calculate_tips(hours_data, total_tips):
    try:
        # Convert to dict if it's not already
        if isinstance(hours_data, str):
            # Try to extract JSON from the string
            match = re.search(r'\{.*\}', hours_data, re.DOTALL)
            if match:
                json_str = match.group(0)
                hours_dict = json.loads(json_str)
            else:
                return "Could not extract JSON data from the response."
        else:
            hours_dict = hours_data
        
        # Calculate total hours
        total_hours = sum(hours_dict.values())
        
        # Calculate tip per hour - DO NOT ROUND
        tip_per_hour = total_tips / total_hours if total_hours > 0 else 0
        
        # Calculate individual tips
        tips_dict = {}
        for partner, hours in hours_dict.items():
            # Calculate exact amount rounded to cents only
            exact_amount = round(hours * tip_per_hour, 2)
            
            # Store the exact amount (rounded to cents)
            tips_dict[partner] = exact_amount
        
        return tips_dict
    except Exception as e:
        return f"Error calculating tips: {str(e)}"

# Function to distribute cash bills
def distribute_cash(tips_dict, bills_info):
    try:
        # Parse bills information
        bills = {}
        for bill_type, count in bills_info.items():
            if count > 0:
                bills[float(bill_type)] = count
        
        # Sort bill denominations in descending order
        sorted_bills = sorted(bills.keys(), reverse=True)
        
        # Initialize result
        distribution = {}
        
        # Distribute bills to partners
        remaining_tips = {partner: amount for partner, amount in tips_dict.items()}
        
        # First pass: assign bills to partners
        for bill in sorted_bills:
            bill_count = bills[bill]
            
            while bill_count > 0:
                # Find partner with highest remaining amount
                max_partner = max(remaining_tips.items(), key=lambda x: x[1])
                partner, amount = max_partner
                
                if amount >= bill:
                    # Assign bill to partner
                    if partner not in distribution:
                        distribution[partner] = {}
                    
                    if bill not in distribution[partner]:
                        distribution[partner][bill] = 0
                    
                    distribution[partner][bill] += 1
                    remaining_tips[partner] -= bill
                    bill_count -= 1
                else:
                    break
        
        # Calculate total distributed and remaining for each partner
        results = {}
        for partner, tip_amount in tips_dict.items():
            distributed = sum(bill * count for bill_dict in [distribution.get(partner, {})] 
                            for bill, count in bill_dict.items())
            remaining = round(tip_amount - distributed, 2)
            
            results[partner] = {
                "total": tip_amount,
                "distributed": distributed,
                "remaining": remaining,
                "bills": distribution.get(partner, {})
            }
        
        return results
    except Exception as e:
        return f"Error distributing cash: {str(e)}"

# Process file and calculate tips
def process_file(ai_provider, file_obj, file_type, total_tips, twenties, tens, fives, ones):
    if file_obj is None:
        return "Please upload a file first."
    
    # Save the uploaded file temporarily
    temp_path = "temp_file"
    if file_type == "pdf":
        temp_path += ".pdf"
    else:
        temp_path += ".jpg"
    
    with open(temp_path, "wb") as f:
        f.write(file_obj)
    
    # Process with selected AI
    if ai_provider == "Mistral":
        if not MISTRAL_API_KEY:
            return "Mistral API key is not configured."
        result = process_with_mistral(temp_path, file_type)
    else:  # Gemini
        if not GEMINI_API_KEY:
            return "Gemini API key is not configured."
        result = process_with_gemini(temp_path, file_type)
    
    # Clean up temp file
    os.remove(temp_path)
    
    # Extract hours data
    try:
        # Try to extract JSON from the result
        match = re.search(r'\{.*\}', result, re.DOTALL)
        if match:
            hours_data = json.loads(match.group(0))
        else:
            return f"Could not extract hours data. Raw result: {result}"
        
        # Calculate total hours
        total_hours = sum(hours_data.values())
        
        # Calculate tip per hour - DO NOT ROUND
        tip_per_hour = total_tips / total_hours if total_hours > 0 else 0
        
        # Calculate tips
        tips_result = calculate_tips(hours_data, float(total_tips))
        
        # Distribute cash
        bills_info = {
            "20": int(twenties),
            "10": int(tens),
            "5": int(fives),
            "1": int(ones)
        }
        distribution = distribute_cash(tips_result, bills_info)
        
        # Format the output
        output = "## Hours Extracted\n\n"
        for partner, hours in hours_data.items():
            output += f"- {partner}: {hours} hours\n"
        
        output += f"\n## Hourly Rate: ${tip_per_hour:.2f}\n\n"
        
        output += "## Tips Calculation\n\n"
        for partner, amount in tips_result.items():
            # Display exact amount (to cents)
            output += f"- {partner}: ${amount:.2f} (${round(amount):,.0f} rounded)\n"
        
        output += "\n## Cash Distribution\n\n"
        for partner, info in distribution.items():
            output += f"### {partner}\n"
            output += f"- Total: ${info['total']:.2f}\n"
            output += f"- Distributed: ${info['distributed']:.2f}\n"
            output += f"- Remaining: ${info['remaining']:.2f}\n"
            output += "- Bills:\n"
            for bill, count in info['bills'].items():
                output += f"  - ${bill}: {count}\n"
            output += "\n"
        
        return output
    except Exception as e:
        return f"Error processing result: {str(e)}\n\nRaw result: {result}"

# Create the Gradio interface
with gr.Blocks(css="style.css", theme=gr.themes.Soft(primary_hue="green")) as demo:
    # Add mobile viewport meta tag
    gr.HTML(MOBILE_META)
    
    # Header with logo and title
    gr.Markdown("""
    <div style="display: flex; flex-direction: column; align-items: center; justify-content: center; margin-bottom: 1rem;">
        <img src="https://upload.wikimedia.org/wikipedia/en/thumb/d/d3/Starbucks_Corporation_Logo_2011.svg/150px-Starbucks_Corporation_Logo_2011.svg.png" width="100" style="margin-bottom: 0.5rem;">
        <h1 style="margin: 0.5rem 0; color: #00704A; text-align: center;">TipJar</h1>
        <p style="margin: 0.2rem 0; color: #444; text-align: center;">Made by William Walsh</p>
        <p style="margin: 0.2rem 0; color: #444; text-align: center;">Starbucks Store# 69600</p>
    </div>
    """)
    
    # Lauren's quote
    gr.Markdown("""<div class="starbucks-quote">\"If theres a Will, Theres a Way!\" -Lauren 2025</div>""")
    
    # App description - make it collapsible on mobile
    with gr.Accordion("App Functions", open=False):
        gr.Markdown("""
        Key functions:
        1. Process partner hours from PDF/image input
        2. Calculate individual tips based on hours worked
        3. Distribute bills equitably among partners
        4. Output detailed distribution breakdown per partner
        """)
    
    # Main content area
    with gr.Tabs():
        with gr.TabItem("Calculate Tips"):
            # Provider selection with larger touch targets for mobile
            ai_provider = gr.Radio(
                label="Select AI Provider", 
                choices=["Mistral", "Gemini"],
                value="Mistral",
                interactive=True
            )
            
            # Use Tabs for file type selection - better on mobile
            with gr.Tabs():
                with gr.TabItem("PDF"):
                    pdf_file = gr.File(
                        label="Upload PDF File",
                        file_types=[".pdf"],
                        elem_classes="mobile-upload"
                    )
                
                with gr.TabItem("Image"):
                    image_file = gr.File(
                        label="Upload Image File",
                        file_types=["image"],
                        elem_classes="mobile-upload"
                    )
            
            # Collapsible section for bill information
            with gr.Accordion("Tips & Cash Information", open=True):
                # Total tips amount
                total_tips = gr.Number(
                    label="Total Tips Amount ($)",
                    value=100,
                    precision=2
                )
                
                # Bill counts in mobile-friendly layout
                gr.Markdown("### Available Bills")
                
                with gr.Row():
                    with gr.Column(scale=1):
                        twenties = gr.Number(label="$20 Bills", value=2, precision=0, minimum=0)
                    
                    with gr.Column(scale=1):
                        tens = gr.Number(label="$10 Bills", value=3, precision=0, minimum=0)
                
                with gr.Row():
                    with gr.Column(scale=1):
                        fives = gr.Number(label="$5 Bills", value=4, precision=0, minimum=0)
                    
                    with gr.Column(scale=1):
                        ones = gr.Number(label="$1 Bills", value=10, precision=0, minimum=0)
            
            # Process button with mobile-friendly styling
            process_btn = gr.Button(
                "Process Tips",
                variant="primary",
                elem_classes="mobile-friendly-button"
            )
            
            # Results output
            output = gr.Markdown(
                label="Results",
                elem_classes="results-container"
            )
            
    # Process function definition
    def process_handler(provider, pdf, image, tips, twenties, tens, fives, ones):
        file_obj = pdf if pdf is not None else image
        file_type = "pdf" if pdf is not None else "image"
        
        if file_obj is None:
            return "Please upload a file first."
            
        return process_file(provider, file_obj, file_type, tips, twenties, tens, fives, ones)
    
    # Connect the process button
    process_btn.click(
        fn=process_handler,
        inputs=[ai_provider, pdf_file, image_file, total_tips, twenties, tens, fives, ones],
        outputs=output
    )
    
    # Footer
    gr.Markdown(
        """
        <div style="text-align: center; color: #00704A; margin-top: 30px;">
            <p>TipJar v1.2 | Made with 💚 by William Walsh</p>
            <p>Starbucks Store# 69600</p>
        </div>
        """
    )

# Launch the app
if __name__ == "__main__":
    demo.launch() 