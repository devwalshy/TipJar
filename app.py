from nicegui import ui
import os
import base64
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
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")

# Configure Gemini with safety settings
if GEMINI_API_KEY:
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

# Initialize state variables
class State:
    def __init__(self):
        self.ocr_result = None
        self.preview_src = None
        self.image_bytes = None
        self.tips_calculated = False
        self.week_counter = 1
        self.tips_history = []
        self.gemini_chat = None
        self.partner_data = []
        self.total_hours = 0
        self.total_tip_amount = 0
        self.hourly_rate = 0
        self.distributed_tips = []
        self.document_total_hours = None

state = State()

# Create custom CSS
custom_css = """
:root {
    --primary: #00704A;
    --primary-light: #e6f2ee;
    --text-on-primary: white;
    --background: #f8f9fa;
    --card-bg: white;
    --border-radius: 10px;
    --box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
    --font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
}

body {
    font-family: var(--font-family);
    background-color: var(--background);
    margin: 0;
    padding: 0;
}

.app-container {
    max-width: 1200px;
    margin: 0 auto;
    padding: 1rem;
}

.header {
    text-align: center;
    margin-bottom: 2rem;
}

.header h1 {
    color: var(--primary);
    font-size: 2.6rem;
    margin: 0;
}

.header p {
    color: var(--primary);
    font-style: italic;
    font-size: 1.2rem;
    margin: 0.5rem 0;
}

.card {
    background-color: var(--card-bg);
    border-radius: var(--border-radius);
    box-shadow: var(--box-shadow);
    padding: 1.5rem;
    margin-bottom: 1.5rem;
}

.primary-button {
    background-color: var(--primary) !important;
    color: var(--text-on-primary) !important;
    font-weight: 500;
    border-radius: 20px !important;
    padding: 0.5rem 1.5rem !important;
}

.partner-card {
    background-color: var(--card-bg);
    border: 1px solid var(--primary);
    border-radius: var(--border-radius);
    padding: 1rem;
    margin-bottom: 1rem;
}

.partner-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 0.5rem;
}

.partner-name {
    font-weight: bold;
    font-size: 1.1rem;
    color: var(--primary);
}

.partner-amount {
    font-weight: bold;
    font-size: 1.5rem;
    color: var(--primary);
}

.partner-hours {
    font-size: 0.9rem;
    margin-bottom: 0.5rem;
}

.calculation {
    background-color: var(--background);
    padding: 0.5rem;
    border-radius: 5px;
    margin-bottom: 0.5rem;
    font-size: 0.9rem;
}

.bills {
    display: flex;
    flex-wrap: wrap;
    gap: 0.5rem;
    background-color: var(--primary-light);
    padding: 0.5rem;
    border-radius: 5px;
}

.bill-chip {
    background-color: var(--primary);
    color: var(--text-on-primary);
    padding: 0.3rem 0.6rem;
    border-radius: 15px;
    font-size: 0.8rem;
    white-space: nowrap;
}

.info-box {
    background-color: var(--primary-light);
    border-left: 4px solid var(--primary);
    padding: 1rem;
    border-radius: 5px;
    margin-bottom: 1rem;
}

@media (max-width: 768px) {
    .app-container {
        padding: 0.5rem;
    }
    
    .card {
        padding: 1rem;
    }
    
    .header h1 {
        font-size: 2rem;
    }
    
    .calculation, .bills {
        font-size: 0.8rem;
    }
}
"""

# Function to process uploaded image
async def process_image(file_data):
    try:
        # Initialize Gemini model
        model = genai.GenerativeModel(
            'gemini-1.5-flash',
            generation_config=generation_config,
            safety_settings=safety_settings
        )
        
        # Store image bytes
        state.image_bytes = file_data
        image = Image.open(io.BytesIO(state.image_bytes))
        
        # Create structured prompt for OCR
        prompt = """Please analyze this image and:
        1. Extract all visible text, especially focusing on names and hours worked
        2. Maintain the original formatting and structure
        3. Preserve any important visual context
        4. Make sure to clearly identify all partner/employee names and their corresponding hours
        
        Extract and format the text clearly:"""
        
        # Process with Gemini
        response = model.generate_content([prompt, image])
        response.resolve()
        state.ocr_result = response.text
        
        # Initialize chat model
        state.gemini_chat = genai.GenerativeModel(
            'gemini-1.5-pro',
            generation_config=generation_config,
            safety_settings=safety_settings
        ).start_chat(history=[])
        
        state.tips_calculated = False
        await refresh_ui()
        
    except Exception as e:
        ui.notify(f"Error processing with Gemini: {str(e)}", type="negative")

# Function to extract partner data
async def extract_partner_data():
    try:
        prompt = f"""
        From the following text, extract partner names and their hours worked. Format as JSON:
        
        {state.ocr_result}
        
        Return a JSON array of objects with 'name' and 'hours' fields. Example:
        [
            {{"name": "John Smith", "hours": 32.5}},
            {{"name": "Jane Doe", "hours": 28.75}}
        ]
        
        Only include valid partners with hours. Output ONLY the JSON array, nothing else.
        """
        
        response = state.gemini_chat.send_message(prompt)
        partner_data_str = response.text
        
        # Also extract total hours
        total_hours_prompt = f"""
        From the following text, extract ONLY the total tippable hours (or total hours) mentioned in the document.
        Return ONLY the number. If you find multiple totals, return the one that's labeled as "Total Tippable Hours" or similar.
        
        {state.ocr_result}
        """
        
        total_hours_response = state.gemini_chat.send_message(total_hours_prompt)
        document_total_hours_str = total_hours_response.text.strip()
        
        # Extract JSON
        pattern = r'\[\s*{.*}\s*\]'
        json_match = re.search(pattern, partner_data_str, re.DOTALL)
        
        if json_match:
            partner_data_str = json_match.group(0)
        
        partner_data = json.loads(partner_data_str)
        
        # Add partner numbers
        for i, partner in enumerate(partner_data):
            partner["number"] = i + 1
        
        state.partner_data = partner_data
        
        # Calculate total hours
        state.total_hours = sum(float(partner["hours"]) for partner in partner_data)
        
        # Compare with document total if available
        try:
            # Clean up extracted total
            document_total_hours_str = re.sub(r'[^\d.]', '', document_total_hours_str)
            if document_total_hours_str:
                state.document_total_hours = float(document_total_hours_str)
        except:
            state.document_total_hours = None
            
        await refresh_ui()
        ui.notify("Partner data extracted successfully", type="positive")
        
    except Exception as e:
        ui.notify(f"Error extracting partner data: {str(e)}", type="negative")

# Function to save manual partner data
def save_manual_partner_data():
    manual_partner_data = []
    
    for i in range(len(partner_inputs)):
        name = partner_inputs[i]['name'].value
        hours = partner_inputs[i]['hours'].value
        
        if name:
            manual_partner_data.append({"name": name, "number": i+1, "hours": hours})
    
    if all(partner["name"] for partner in manual_partner_data):
        state.partner_data = manual_partner_data
        state.total_hours = sum(float(partner["hours"]) for partner in manual_partner_data)
        ui.notify("Partner data saved successfully", type="positive")
        refresh_ui()
    else:
        ui.notify("Please provide names for all partners", type="negative")

# Function to calculate tips
def calculate_tips():
    try:
        total_tip_amount = tip_amount_input.value
        
        if total_tip_amount <= 0:
            ui.notify("Please enter a valid tip amount", type="negative")
            return
            
        # Store total tip amount
        state.total_tip_amount = total_tip_amount
        
        # Calculate hourly rate
        hourly_rate = total_tip_amount / state.total_hours
        
        # Truncate to hundredths place
        hourly_rate = int(hourly_rate * 100) / 100
        state.hourly_rate = hourly_rate
        
        # Calculate tips for each partner
        partner_data = state.partner_data
        
        for partner in partner_data:
            # Calculate exact tip amount
            exact_amount = float(partner["hours"]) * hourly_rate
            
            # Store exact amounts
            partner["raw_tip_amount"] = exact_amount
            partner["exact_tip_amount"] = exact_amount
            
            # Round to nearest dollar
            partner["tip_amount"] = round(exact_amount)
        
        # Distribute bills
        denominations = [20, 10, 5, 1]
        
        # Determine starting partner based on rotation
        num_partners = len(partner_data)
        start_index = (state.week_counter - 1) % num_partners
        
        # Calculate remaining amounts
        remaining_amounts = {}
        for partner in partner_data:
            remaining_amounts[partner["number"]] = partner["tip_amount"]
        
        # Initialize bill counts
        for partner in partner_data:
            partner["bills"] = {20: 0, 10: 0, 5: 0, 1: 0}
        
        # Distribute by denomination
        for denomination in denominations:
            # Create order of partners
            partner_order = [(start_index + i) % num_partners for i in range(num_partners)]
            
            # Keep distributing bills while possible
            while True:
                distributed = False
                for idx in partner_order:
                    partner_num = partner_data[idx]["number"]
                    if remaining_amounts[partner_num] >= denomination:
                        # Give this partner a bill
                        partner_data[idx]["bills"][denomination] += 1
                        remaining_amounts[partner_num] -= denomination
                        distributed = True
                
                # If no more bills distributed, move to next denomination
                if not distributed:
                    break
        
        # Format bill distribution
        for partner in partner_data:
            bills_text = []
            for denom in [20, 10, 5, 1]:
                if partner["bills"][denom] > 0:
                    bills_text.append(f"{partner['bills'][denom]}x${denom}")
            
            partner["bills_text"] = ", ".join(bills_text)
            
            # Format for copy-paste
            partner["formatted_output"] = (
                f"Partner Name: {partner['name']} | #: {partner['number']} | "
                f"Hours: {partner['hours']} | Exact: ${partner['exact_tip_amount']:.2f} | "
                f"Cash: ${partner['tip_amount']} | Bills: {partner['bills_text']}"
            )
        
        # Save tips to state
        state.distributed_tips = partner_data
        state.tips_calculated = True
        
        # Increment week counter for next allocation
        state.week_counter += 1
        
        refresh_ui()
        ui.notify("Tips calculated successfully", type="positive")
        
    except Exception as e:
        ui.notify(f"Error calculating tips: {str(e)}", type="negative")

# Function to save distribution to history
def save_to_history():
    distribution = {
        "week": state.week_counter - 1,
        "total_amount": state.total_tip_amount,
        "total_hours": state.total_hours,
        "partners": state.distributed_tips
    }
    
    state.tips_history.append(distribution)
    ui.notify("Distribution saved to history", type="positive")
    refresh_ui()

# Function to download results
def download_ocr_text():
    if state.ocr_result:
        b64 = base64.b64encode(state.ocr_result.encode()).decode()
        return f"data:file/txt;base64,{b64}"
    return "#"

# Function to generate HTML table for download
def generate_html_table():
    if not state.tips_calculated:
        return ""
        
    tip_data = []
    for partner in state.distributed_tips:
        exact_amount = partner['exact_tip_amount']
        calculation = f"{partner['hours']} × ${state.hourly_rate:.2f} = ${exact_amount:.2f}"
        
        tip_data.append({
            "Partner Name": partner["name"],
            "#": partner["number"],
            "Hours": partner["hours"],
            "Calculation": calculation,
            "Cash Amount": f"${partner['tip_amount']}",
            "Bills": partner["bills_text"]
        })
    
    html = """
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>TipJar Results</title>
        <style>
            body {
                font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
                margin: 20px;
                padding: 0;
                color: #333;
            }
            h1 {
                color: #00704A;
                text-align: center;
            }
            .info {
                margin: 10px 0;
                background-color: #f8f9fa;
                padding: 10px;
                border-radius: 8px;
            }
            table {
                width: 100%;
                border-collapse: collapse;
                margin-top: 20px;
                border-radius: 8px;
                overflow: hidden;
            }
            th, td {
                border: 1px solid #ddd;
                padding: 12px 8px;
                text-align: left;
            }
            th {
                background-color: #00704A;
                color: white;
            }
            tr:nth-child(even) {
                background-color: #f2f2f2;
            }
            .calculation {
                color: #666;
                font-size: 0.9em;
            }
            .cash-amount {
                font-weight: bold;
                color: #00704A;
            }
            @media (max-width: 600px) {
                th, td {
                    padding: 8px 4px;
                    font-size: 14px;
                }
            }
        </style>
    </head>
    <body>
        <h1>Tip Distribution Results</h1>
        <div class="info">
            <p><strong>Hourly Rate Calculation:</strong> $""" + f"{state.total_tip_amount:.2f} ÷ {state.total_hours:.2f} = ${state.hourly_rate:.2f}" + """ per hour</p>
        </div>
        <table>
            <thead>
                <tr>
                    <th>#</th>
                    <th>Partner Name</th>
                    <th>Hours</th>
                    <th>Calculation</th>
                    <th>Cash</th>
                    <th>Bills</th>
                </tr>
            </thead>
            <tbody>
    """
    
    for partner in tip_data:
        html += f"""
                <tr>
                    <td>{partner['#']}</td>
                    <td>{partner['Partner Name']}</td>
                    <td>{partner['Hours']}</td>
                    <td class="calculation">{partner['Calculation']}</td>
                    <td class="cash-amount">{partner['Cash Amount']}</td>
                    <td>{partner['Bills']}</td>
                </tr>
        """
    
    html += """
            </tbody>
        </table>
    </body>
    </html>
    """
    
    html_b64 = base64.b64encode(html.encode()).decode()
    return f"data:text/html;base64,{html_b64}"

# Function to refresh UI based on state
def refresh_ui():
    ui.update()

# Add custom CSS
ui.add_head_html(f'<style>{custom_css}</style>')

# App title and header
with ui.card().classes('header'):
    ui.markdown('# TipJar')
    ui.markdown('*"If theres a Will, Theres a Way!" -Lauren 2025*')

# Main container
with ui.column().classes('app-container'):
    
    # Check for API key
    if not GEMINI_API_KEY:
        with ui.card().classes('card'):
            ui.markdown('## Configuration Error')
            ui.label('Gemini API key is not configured in the .env file. Please add it and restart the application.')
            ui.button('Restart App', on_click=lambda: ui.navigate.reload())
    else:
        # File upload card
        with ui.card().classes('card'):
            ui.markdown('## Upload Image')
            file_picker = ui.upload(
                label='Upload an Image file', 
                auto_upload=True,
                max_files=1
            ).props('accept=".jpg,.jpeg,.png"')
            
            @file_picker.on_upload
            async def handle_upload(e):
                try:
                    # Read the entire file content
                    file_data = e.content.read() if hasattr(e.content, 'read') else e.content
                    
                    # Process the image
                    await process_image(file_data)
                except Exception as ex:
                    ui.notify(f"Error processing upload: {str(ex)}", type="negative")
            
            ui.button('Process', on_click=lambda: ui.notify('Please upload an image first', type='warning') if not state.image_bytes else None).classes('primary-button').props('full-width')
        
        # Results section (only shown when OCR result is available)
        ocr_result_card = ui.card().classes('card')
        with ocr_result_card:
            ui.markdown('## Image Preview')
            preview_image = ui.image().props('contain')
            ui.markdown('## Extracted Tippable Hours')
            ocr_text = ui.markdown()
            
            extract_btn = ui.button('Extract Partner Data', on_click=extract_partner_data).classes('primary-button').props('full-width')
        
        # Hide by default
        ocr_result_card.set_visibility(False)
        
        # Manual partner data entry
        manual_entry_card = ui.card().classes('card')
        with manual_entry_card:
            ui.markdown('## Manually Enter Partner Data')
            num_partners_input = ui.number(label='Number of Partners', value=3, min=1, max=20).props('outlined')
            
            partner_inputs = []
            partner_container = ui.column()
            
            def update_partner_inputs():
                partner_container.clear()
                partner_inputs.clear()
                
                with partner_container:
                    for i in range(int(num_partners_input.value)):
                        with ui.card().classes('partner-card'):
                            ui.markdown(f'### Partner {i+1}')
                            name_input = ui.input(label='Name').props('outlined')
                            hours_input = ui.number(label='Hours', value=0, min=0, step=0.25).props('outlined')
                            partner_inputs.append({'name': name_input, 'hours': hours_input})
            
            update_partner_inputs()
            num_partners_input.on('update:model-value', update_partner_inputs)
            
            ui.button('Save Partner Data', on_click=save_manual_partner_data).classes('primary-button').props('full-width')
        
        # Hide by default
        manual_entry_card.set_visibility(False)
        
        # Tip calculation section
        tip_calculation_card = ui.card().classes('card')
        with tip_calculation_card:
            ui.markdown('## Calculate Tips')
            
            # Display partner data summary
            partner_summary = ui.markdown()
            
            # Input for tip amount
            tip_amount_input = ui.number(label='Enter total tip amount for the week: $', value=0, min=0, step=10).props('outlined')
            
            # Calculate button
            calculate_btn = ui.button('Calculate Tips', on_click=calculate_tips).classes('primary-button').props('full-width')
        
        # Hide by default
        tip_calculation_card.set_visibility(False)
        
        # Results section
        results_card = ui.card().classes('card')
        with results_card:
            ui.markdown('## Tip Distribution Results')
            
            # Hourly rate info
            hourly_rate_info = ui.markdown()
            
            # Partner results
            results_container = ui.column()
            
            # Copy-paste format
            with ui.expansion('Copy-paste format'):
                copy_paste_text = ui.markdown()
            
            # Save to history button
            save_history_btn = ui.button('Save to History', on_click=save_to_history).classes('primary-button').props('full-width')
            
            # Download options
            ui.markdown('## Download Options')
            download_row = ui.row()
            with download_row:
                ui.button('Download OCR Text', on_click=lambda: ui.download(name='ocr_result.txt', url=download_ocr_text())).classes('primary-button')
                ui.button('Download as Table', on_click=lambda: ui.download(name='tip_distribution.html', url=generate_html_table())).classes('primary-button')
        
        # Hide by default
        results_card.set_visibility(False)
        
        # History section
        history_card = ui.card().classes('card')
        with history_card:
            ui.markdown('## Distribution History')
            history_container = ui.column()
        
        # Hide by default
        history_card.set_visibility(False)
        
        # Function to update UI based on state
        def refresh_ui():
            # Update image preview
            if state.image_bytes:
                ocr_result_card.set_visibility(True)
                preview_image.set_source(f'data:image/jpeg;base64,{base64.b64encode(state.image_bytes).decode()}')
            else:
                ocr_result_card.set_visibility(False)
            
            # Update OCR text
            if state.ocr_result:
                ocr_text.set_content(f'```\n{state.ocr_result}\n```')
            
            # Update manual entry visibility
            manual_entry_card.set_visibility(True)
            
            # Update tip calculation section
            if state.partner_data:
                tip_calculation_card.set_visibility(True)
                
                # Update partner summary
                summary_text = f"**Total Hours: {state.total_hours}**\n\n"
                summary_text += "**Partner Data:**\n"
                for partner in state.partner_data:
                    summary_text += f"- {partner['name']} - {partner['hours']} hours\n"
                
                # Add validation if document total is available
                if state.document_total_hours:
                    summary_text += "\n**Hours Validation**\n"
                    if abs(state.document_total_hours - state.total_hours) < 0.01:
                        summary_text += f"✅ Validation passed! Document total ({state.document_total_hours}) matches calculated total ({state.total_hours})."
                    else:
                        summary_text += f"⚠️ Validation check: Document shows {state.document_total_hours} total hours, but calculated total is {state.total_hours}."
                        summary_text += "\nThis discrepancy might be due to OCR errors or missing partners. Please verify manually."
                
                partner_summary.set_content(summary_text)
            else:
                tip_calculation_card.set_visibility(False)
            
            # Update results section
            if state.tips_calculated:
                results_card.set_visibility(True)
                
                # Update hourly rate info
                hourly_rate_info.set_content(f"""
                **Calculation:**  
                Total Tips: ${state.total_tip_amount:.2f} ÷ Total Hours: {state.total_hours:.2f} = **${state.hourly_rate:.2f}** per hour
                """)
                
                # Update results container
                results_container.clear()
                for partner in state.distributed_tips:
                    exact_amount = partner['exact_tip_amount']
                    calculation = f"{partner['hours']} × ${state.hourly_rate:.2f} = ${exact_amount:.2f}"
                    
                    with results_container:
                        with ui.card().classes('partner-card'):
                            with ui.row().classes('partner-header'):
                                ui.label(partner['name']).classes('partner-name')
                                ui.label(f"${partner['tip_amount']}").classes('partner-amount')
                            
                            ui.label(f"{partner['hours']} hours").classes('partner-hours')
                            
                            with ui.label().classes('calculation'):
                                ui.html(f"{calculation} → ${partner['tip_amount']}")
                            
                            with ui.column().classes('bills'):
                                ui.label('Bills:')
                                with ui.row():
                                    for bill in partner['bills_text'].split(','):
                                        if bill.strip():
                                            ui.label(bill.strip()).classes('bill-chip')
                
                # Update copy-paste text
                copy_paste_content = ""
                for partner in state.distributed_tips:
                    copy_paste_content += f"{partner['formatted_output']}\n"
                copy_paste_text.set_content(f"```\n{copy_paste_content}\n```")
            else:
                results_card.set_visibility(False)
            
            # Update history section
            if state.tips_history:
                history_card.set_visibility(True)
                
                # Update history container
                history_container.clear()
                for i, dist in enumerate(state.tips_history):
                    with history_container:
                        with ui.card().classes('partner-card'):
                            ui.label(f"Week {dist['week']}").classes('partner-name')
                            ui.label(f"Total: ${dist['total_amount']} for {dist['total_hours']} hours")
                            
                            for partner in dist["partners"]:
                                ui.label(f"{partner['name']} | #{partner['number']} | {partner['hours']} hours | ${partner['tip_amount']} | {partner['bills_text']}")
                            
                            ui.separator()
            else:
                history_card.set_visibility(False)

# Footer
with ui.footer().style('background-color: #f8f9fa; margin-top: 2rem; padding: 1rem; text-align: center;'):
    ui.label('Made by William Walsh').style('color: #00704A; margin: 0;')
    ui.label('Starbucks Store# 69600').style('color: #00704A; margin: 0;')

# Run the app
ui.run(title="TipJar - Tip Distribution Tool", favicon="💰") 