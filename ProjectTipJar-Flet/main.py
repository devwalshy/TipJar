import flet as ft
import os
import base64
from mistralai.client import MistralClient
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

class TipJarApp(ft.UserControl):
    def __init__(self, page: ft.Page):
        super().__init__()
        self.page = page
        
        # Set page properties
        self.page.title = "TipJar"
        self.page.theme = ft.Theme(
            color_scheme=ft.ColorScheme(
                primary=ft.colors.GREEN,
                primary_container=ft.colors.GREEN_100,
            ),
            font_family="Roboto",
        )
        self.page.window_width = 1200
        self.page.window_height = 800
        self.page.scroll = ft.ScrollMode.AUTO
        
        # Initialize state variables
        self.ocr_result = None
        self.preview_src = None
        self.image_bytes = None
        self.tips_calculated = False
        self.week_counter = 1
        self.tips_history = []
        self.gemini_chat = None
        self.partner_data = None
        self.total_hours = 0
        self.hourly_rate = 0
        self.total_tip_amount = 0
        self.distributed_tips = None
        self.partner_rows = []
        
        # Create sections
        self.input_section = self.create_input_section()
        self.ocr_result_section = self.create_ocr_result_section()
        self.partner_data_section = self.create_partner_data_section()
        self.tip_allocation_section = self.create_tip_allocation_section()
        self.results_section = self.create_results_section()
        self.history_section = self.create_history_section()
        
        # Set initial visibility
        self.ocr_result_section.visible = False
        self.partner_data_section.visible = False
        self.tip_allocation_section.visible = False
        self.results_section.visible = False
        self.history_section.visible = False
        
        # Try to load history from local storage
        try:
            history_json = self.page.client_storage.get("tips_history")
            if history_json:
                self.tips_history = json.loads(history_json)
                self.update_history_section()
        except Exception as e:
            print(f"Error loading history: {e}")
        
    def build(self):
        # Create header
        header = ft.Container(
            content=ft.Column([
                ft.Text("TipJar", size=36, weight=ft.FontWeight.BOLD, color="#00704A"),
                ft.Row([
                    ft.Text("Made by William Walsh", italic=True),
                ]),
                ft.Text("Starbucks Store# 69600", italic=True),
                ft.Container(
                    content=ft.Text(
                        "\"If theres a Will, Theres a Way!\" -Lauren 2025",
                        style=ft.TextStyle(
                            italic=True,
                            color="#00704A",
                            size=18,
                        ),
                    ),
                    margin=ft.margin.symmetric(vertical=10),
                ),
            ]),
            padding=20,
            alignment=ft.alignment.center,
        )
        
        # Create key functions section
        key_functions = ft.Container(
            content=ft.Column([
                ft.Text("Key Functions:", weight=ft.FontWeight.BOLD),
                ft.Row([
                    ft.Icon(ft.icons.DOCUMENT_SCANNER, color="#00704A"),
                    ft.Text("OCR Scan of PDFs and Images"),
                ]),
                ft.Row([
                    ft.Icon(ft.icons.CALCULATE, color="#00704A"),
                    ft.Text("Automatic Tip Calculation"),
                ]),
                ft.Row([
                    ft.Icon(ft.icons.ATTACH_MONEY, color="#00704A"),
                    ft.Text("Cash Distribution"),
                ]),
                ft.Row([
                    ft.Icon(ft.icons.HISTORY, color="#00704A"),
                    ft.Text("History Tracking"),
                ]),
            ]),
            padding=20,
            bgcolor=ft.colors.BLACK.with_opacity(0.05),
            border_radius=10,
        )
        
        # Create footer
        footer = ft.Container(
            content=ft.Column([
                ft.Text("TipJar v1.2 | Made with 💚 by William Walsh", 
                        color="#00704A", 
                        text_align=ft.TextAlign.CENTER),
                ft.Text("Starbucks Store# 69600", 
                        color="#00704A", 
                        text_align=ft.TextAlign.CENTER),
            ]),
            padding=20,
            alignment=ft.alignment.center,
        )
        
        # Navigation buttons
        nav_buttons = ft.Row([
            ft.ElevatedButton(
                "Home",
                icon=ft.icons.HOME,
                on_click=lambda e: self.toggle_section_visibility(input_visible=True),
            ),
            ft.ElevatedButton(
                "History",
                icon=ft.icons.HISTORY,
                on_click=lambda e: self.toggle_section_visibility(history_visible=True),
            ),
        ], alignment=ft.MainAxisAlignment.CENTER)
        
        # Assemble main content
        main_content = ft.Column([
            # Header
            header,
            
            # Key functions
            key_functions,
            
            # Navigation
            nav_buttons,
            
            # Sections
            self.input_section,
            self.ocr_result_section,
            self.partner_data_section,
            self.tip_allocation_section,
            self.results_section,
            self.history_section,
            
            # Footer
            footer,
        ], spacing=20)
        
        # Return main container
        return ft.Container(
            content=main_content,
            padding=20,
        )

    def create_input_section(self):
        # AI Provider selection
        self.ai_provider_dropdown = ft.Dropdown(
            label="Select AI Provider",
            options=[
                ft.dropdown.Option("Mistral"),
                ft.dropdown.Option("Gemini"),
            ],
            value="Mistral",
            width=300,
        )
        
        # File type selection
        self.file_type_radio = ft.RadioGroup(
            value="PDF",
            content=ft.Row(
                [
                    ft.Radio(value="PDF", label="PDF"),
                    ft.Radio(value="Image", label="Image"),
                ],
            ),
        )
        
        # Source type selection
        self.source_type_radio = ft.RadioGroup(
            value="Local Upload",
            content=ft.Row(
                [
                    ft.Radio(value="URL", label="URL"),
                    ft.Radio(value="Local Upload", label="Local Upload"),
                ],
            ),
        )
        
        # URL input field (initially hidden)
        self.url_input = ft.TextField(
            label="Enter URL",
            visible=False,
            width=500,
        )
        
        # File picker for local uploads
        self.file_picker = ft.FilePicker(
            on_result=self.on_file_picked
        )
        self.page.overlay.append(self.file_picker)
        
        self.upload_button = ft.ElevatedButton(
            text="Choose File",
            icon=ft.icons.UPLOAD_FILE,
            on_click=lambda _: self.file_picker.pick_files(
                allowed_extensions=["pdf"] if self.file_type_radio.value == "PDF" else ["jpg", "jpeg", "png"]
            ),
        )
        
        self.selected_file_text = ft.Text("No file selected", color="grey")
        
        # Process button
        self.process_button = ft.ElevatedButton(
            "Process",
            icon=ft.icons.PLAY_ARROW,
            on_click=self.process_document,
            style=ft.ButtonStyle(
                color=ft.colors.WHITE,
                bgcolor="#00704A",
                shape=ft.RoundedRectangleBorder(radius=20),
            ),
        )
        
        # Container for the file selection elements
        self.file_input_container = ft.Container(
            content=ft.Column(
                [
                    ft.Row([self.upload_button, self.selected_file_text]),
                ],
                spacing=10,
            ),
        )
        
        # Listen for changes in source type to show/hide fields
        def source_type_changed():
            if self.source_type_radio.value == "URL":
                self.url_input.visible = True
                self.file_input_container.visible = False
            else:
                self.url_input.visible = False
                self.file_input_container.visible = True
            self.page.update()
        
        self.source_type_radio.on_change = lambda _: source_type_changed()
        
        # Check API key availability
        api_key_warning = None
        if not MISTRAL_API_KEY or not GEMINI_API_KEY:
            missing_keys = []
            if not MISTRAL_API_KEY:
                missing_keys.append("Mistral")
            if not GEMINI_API_KEY:
                missing_keys.append("Gemini")
            api_key_warning = ft.Text(
                f"Warning: {', '.join(missing_keys)} API key(s) not configured in .env file.",
                color="red",
            )
        
        return ft.Card(
            content=ft.Container(
                content=ft.Column(
                    [
                        ft.Text("Document Input", size=24, weight=ft.FontWeight.BOLD),
                        self.ai_provider_dropdown,
                        ft.Row(
                            [
                                ft.Text("File Type:"),
                                self.file_type_radio,
                            ],
                            alignment=ft.MainAxisAlignment.START,
                        ),
                        ft.Row(
                            [
                                ft.Text("Source:"),
                                self.source_type_radio,
                            ],
                            alignment=ft.MainAxisAlignment.START,
                        ),
                        self.url_input,
                        self.file_input_container,
                        self.process_button,
                    ] + ([api_key_warning] if api_key_warning else []),
                    spacing=16,
                ),
                padding=20,
            ),
        )
        
    def on_file_picked(self, e):
        if e.files and len(e.files) > 0:
            self.selected_file = e.files[0]
            self.selected_file_text.value = f"Selected: {self.selected_file.name}"
            self.page.update()
    
    def create_ocr_result_section(self):
        self.preview_image = ft.Image(
            width=400,
            fit=ft.ImageFit.CONTAIN,
        )
        
        self.preview_pdf = ft.Container(
            content=ft.Text("PDF preview not available in Flet. PDF will be processed."),
            padding=10,
            bgcolor=ft.colors.BLACK12,
            border_radius=5,
            width=400,
            height=200,
        )
        
        self.ocr_text = ft.TextField(
            label="Extracted Text",
            multiline=True,
            min_lines=10,
            max_lines=20,
            read_only=True,
            width=500,
        )
        
        self.extract_button = ft.ElevatedButton(
            "Extract Partner Data",
            icon=ft.icons.PERSON_SEARCH,
            on_click=self.extract_partner_data,
            style=ft.ButtonStyle(
                color=ft.colors.WHITE,
                bgcolor="#00704A",
                shape=ft.RoundedRectangleBorder(radius=20),
            ),
        )
        
        self.manual_entry_button = ft.OutlinedButton(
            "Manual Entry",
            icon=ft.icons.EDIT,
            on_click=self.show_manual_entry,
        )
        
        # Download button for OCR text
        self.download_ocr_button = ft.ElevatedButton(
            "Download OCR Text",
            icon=ft.icons.DOWNLOAD,
            on_click=self.download_ocr_text,
            visible=False,
        )
        
        return ft.Column(
            [
                ft.Text("Document Preview & OCR Result", size=24, weight=ft.FontWeight.BOLD),
                ft.Row(
                    [
                        ft.Column(
                            [
                                ft.Text("Preview", size=18, weight=ft.FontWeight.BOLD),
                                self.preview_image,
                                self.preview_pdf,
                            ],
                            spacing=10,
                            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                        ),
                        ft.VerticalDivider(width=1),
                        ft.Column(
                            [
                                ft.Text("Extracted Text", size=18, weight=ft.FontWeight.BOLD),
                                self.ocr_text,
                                ft.Row(
                                    [
                                        self.extract_button,
                                        self.manual_entry_button,
                                        self.download_ocr_button,
                                    ],
                                    spacing=10,
                                ),
                            ],
                            spacing=10,
                        ),
                    ],
                    spacing=20,
                    alignment=ft.MainAxisAlignment.CENTER,
                ),
            ],
            spacing=20,
        ) 

    def create_partner_data_section(self):
        # Create list view for partner data
        self.partner_data_list = ft.ListView(
            spacing=10,
            padding=20,
            auto_scroll=True,
        )
        
        # Create button to add another partner row
        self.add_partner_button = ft.ElevatedButton(
            "Add Partner",
            icon=ft.icons.ADD,
            on_click=self.add_partner_row,
        )
        
        # Create button to continue to tip allocation
        self.continue_to_tips_button = ft.ElevatedButton(
            "Continue to Tip Allocation",
            icon=ft.icons.ARROW_FORWARD,
            on_click=self.show_tip_allocation,
            style=ft.ButtonStyle(
                color=ft.colors.WHITE,
                bgcolor="#00704A",
                shape=ft.RoundedRectangleBorder(radius=20),
            ),
        )
        
        return ft.Column(
            [
                ft.Text("Partner Data", size=24, weight=ft.FontWeight.BOLD),
                ft.Text("Enter or verify partner information:"),
                ft.Container(
                    content=self.partner_data_list,
                    height=400,
                    border=ft.border.all(1, ft.colors.BLACK26),
                    border_radius=5,
                    padding=10,
                ),
                ft.Row(
                    [
                        self.add_partner_button,
                        self.continue_to_tips_button,
                    ],
                    alignment=ft.MainAxisAlignment.END,
                    spacing=10,
                ),
            ],
            spacing=20,
        )
    
    def add_partner_row(self, e=None, partner_data=None):
        """Add a row for partner data entry, optionally pre-populated"""
        # Create a unique ID for this row
        row_id = len(self.partner_rows)
        
        # Create text fields for partner data
        partner_number = ft.TextField(
            label="Partner #",
            value=partner_data["partner_number"] if partner_data else "",
            width=120,
        )
        
        partner_name = ft.TextField(
            label="Name",
            value=partner_data["partner_name"] if partner_data else "",
            width=200,
        )
        
        hours = ft.TextField(
            label="Hours",
            value=str(partner_data["hours"]) if partner_data else "",
            width=100,
            keyboard_type=ft.KeyboardType.NUMBER,
        )
        
        # Delete button
        delete_button = ft.IconButton(
            icon=ft.icons.DELETE,
            tooltip="Remove partner",
            on_click=lambda e, rid=row_id: self.remove_partner_row(rid),
        )
        
        # Create row container
        row_container = ft.Row(
            [
                partner_number,
                partner_name,
                hours,
                delete_button,
            ],
            spacing=10,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        )
        
        # Add row to list and store reference
        self.partner_data_list.controls.append(row_container)
        self.partner_rows.append({
            "id": row_id,
            "container": row_container,
            "partner_number": partner_number,
            "partner_name": partner_name,
            "hours": hours,
        })
        
        if e:  # Only update if this was triggered by a UI event
            self.page.update()
    
    def remove_partner_row(self, row_id):
        """Remove a partner row by its ID"""
        # Find the row with matching ID
        for i, row in enumerate(self.partner_rows):
            if row["id"] == row_id:
                # Remove from UI
                self.partner_data_list.controls.remove(row["container"])
                # Remove from our list
                self.partner_rows.pop(i)
                self.page.update()
                break
    
    def show_manual_entry(self, e):
        """Switch to manual entry mode"""
        # Clear existing partner rows
        self.partner_rows = []
        self.partner_data_list.controls.clear()
        
        # Add one empty row to start
        self.add_partner_row()
        
        # Show partner data section
        self.toggle_section_visibility(partner_data_visible=True)
    
    def extract_partner_data(self, e):
        """Extract partner data from OCR text"""
        ocr_text = self.ocr_text.value
        if not ocr_text:
            self.show_error("No OCR text to extract partner data from.")
            return
        
        # Clear existing partner rows
        self.partner_rows = []
        self.partner_data_list.controls.clear()
        
        try:
            # Use regex to extract partner data from OCR text
            # Pattern: Partner number (digits), name (letters), hours (digits with decimal)
            pattern = r"(\d+)\s+([A-Za-z\s]+)\s+(\d+\.?\d*)"
            matches = re.findall(pattern, ocr_text)
            
            if not matches:
                self.show_error("No partner data found in the OCR text. Try manual entry.")
                return
            
            # Add a row for each partner found
            for match in matches:
                partner_number, partner_name, hours = match
                self.add_partner_row(partner_data={
                    "partner_number": partner_number.strip(),
                    "partner_name": partner_name.strip(),
                    "hours": float(hours),
                })
            
            # Show partner data section
            self.toggle_section_visibility(partner_data_visible=True)
            
        except Exception as e:
            self.show_error(f"Error extracting partner data: {str(e)}")
            
    def show_error(self, message):
        """Display an error dialog"""
        dialog = ft.AlertDialog(
            title=ft.Text("Error"),
            content=ft.Text(message),
            actions=[
                ft.TextButton("OK", on_click=lambda e: self.close_dialog(e, dialog)),
            ],
        )
        self.page.dialog = dialog
        dialog.open = True
        self.page.update()
        
    def close_dialog(self, e, dialog):
        """Close a dialog"""
        dialog.open = False
        self.page.update()

    def show_tip_allocation(self, e):
        """Show tip allocation section after partner data is entered"""
        # Validate partner data
        if not self.partner_rows:
            self.show_error("Please add at least one partner.")
            return
            
        # Check that all fields are filled
        for row in self.partner_rows:
            if not row["partner_number"].value or not row["partner_name"].value or not row["hours"].value:
                self.show_error("Please fill in all partner data fields.")
                return
        
        # Show tip allocation section
        self.toggle_section_visibility(tip_allocation_visible=True)
        
    def calculate_distribution(self, e):
        """Calculate tip distribution based on user inputs"""
        try:
            # Get total tips
            total_tips = float(self.total_tips_input.value)
            if total_tips <= 0:
                self.show_error("Total tips must be greater than zero.")
                return
                
            # Get distribution method
            distribution_method = self.distribution_method.value
            
            # Get cash distribution setting
            cash_distribution = self.cash_distribution.value
            
            # Calculate distribution
            partner_data = []
            total_hours = 0
            
            # Gather partner data and calculate total hours
            for row in self.partner_rows:
                partner_number = row["partner_number"].value
                partner_name = row["partner_name"].value
                hours = float(row["hours"].value)
                
                if hours <= 0:
                    self.show_error(f"Hours for {partner_name} must be greater than zero.")
                    return
                    
                partner_data.append({
                    "partner_number": partner_number,
                    "partner_name": partner_name,
                    "hours": hours,
                })
                
                total_hours += hours
            
            # Calculate exact amounts
            for partner in partner_data:
                if distribution_method == "Based on Hours":
                    # Calculate proportion based on hours
                    partner["exact_amount"] = round(total_tips * (partner["hours"] / total_hours), 2)
                else:  # Equal Split
                    # Split evenly
                    partner["exact_amount"] = round(total_tips / len(partner_data), 2)
            
            # Handle cash distribution if enabled
            if cash_distribution:
                # Define bill denominations
                denominations = [100, 50, 20, 10, 5, 1]
                
                for partner in partner_data:
                    # Round down to nearest dollar
                    cash_amount = math.floor(partner["exact_amount"])
                    partner["cash_amount"] = cash_amount
                    
                    # Calculate bills breakdown
                    bills = {}
                    remaining = cash_amount
                    
                    for denom in denominations:
                        count = remaining // denom
                        if count > 0:
                            bills[denom] = count
                            remaining -= count * denom
                    
                    partner["bills"] = bills
            
            # Store the distribution data
            self.current_distribution = {
                "week": self.week_dropdown.value,
                "total_tips": total_tips,
                "total_hours": total_hours,
                "distribution_method": distribution_method,
                "partners": partner_data,
            }
            
            # Update results table
            self.update_results_table(partner_data, cash_distribution)
            
            # Show results section
            self.toggle_section_visibility(results_visible=True)
            
            # Show download buttons
            self.download_table_button.visible = True
            
        except ValueError:
            self.show_error("Please enter valid numbers for total tips and partner hours.")
        except Exception as e:
            self.show_error(f"Error calculating distribution: {str(e)}")
            
    def update_results_table(self, partner_data, cash_distribution):
        """Update the results table with the calculated distribution"""
        # Clear existing rows
        self.results_table.rows.clear()
        
        # Add rows for each partner
        for partner in partner_data:
            # Format bills display
            bills_display = ""
            if cash_distribution and "bills" in partner:
                bills_list = []
                for denom, count in partner["bills"].items():
                    bills_list.append(f"{count}x${denom}")
                bills_display = ", ".join(bills_list)
            
            # Create row
            row = ft.DataRow(
                cells=[
                    ft.DataCell(ft.Text(partner["partner_number"])),
                    ft.DataCell(ft.Text(partner["partner_name"])),
                    ft.DataCell(ft.Text(str(partner["hours"]))),
                    ft.DataCell(ft.Text(f"${partner['exact_amount']:.2f}")),
                    ft.DataCell(ft.Text(f"${partner['cash_amount']}" if cash_distribution else "N/A")),
                    ft.DataCell(ft.Text(bills_display if cash_distribution else "N/A")),
                ]
            )
            
            # Add row to table
            self.results_table.rows.append(row)
        
        # Update the page
        self.page.update()
        
    def save_distribution(self, e):
        """Save the current distribution to history"""
        if not hasattr(self, "current_distribution"):
            self.show_error("No distribution to save.")
            return
            
        # Initialize history if it doesn't exist
        if not hasattr(self, "tips_history"):
            self.tips_history = []
            
        # Add current distribution to history
        self.tips_history.append(self.current_distribution)
        
        # Save to local storage if available
        try:
            # Convert to JSON
            history_json = json.dumps(self.tips_history)
            # Save using page client storage
            self.page.client_storage.set("tips_history", history_json)
        except Exception as e:
            print(f"Error saving history: {e}")
            
        # Update history section
        self.update_history_section()
        
        # Show success message
        self.show_success("Distribution saved successfully!")
        
    def update_history_section(self):
        """Update the history section with saved distributions"""
        if not hasattr(self, "tips_history") or not self.tips_history:
            return
            
        # Clear existing history items
        self.history_list.controls.clear()
        
        # Add items for each saved distribution
        for i, dist in enumerate(self.tips_history):
            # Create expandable item for this distribution
            item = ft.ExpansionTile(
                title=ft.Text(f"{dist['week']} - ${dist['total_tips']:.2f} - {len(dist['partners'])} Partners"),
                subtitle=ft.Text(f"Total Hours: {dist['total_hours']} - Method: {dist['distribution_method']}"),
                controls=[
                    # Create a table for partner details
                    ft.DataTable(
                        columns=[
                            ft.DataColumn(ft.Text("Partner #")),
                            ft.DataColumn(ft.Text("Name")),
                            ft.DataColumn(ft.Text("Hours")),
                            ft.DataColumn(ft.Text("Amount")),
                        ],
                        rows=[
                            ft.DataRow(
                                cells=[
                                    ft.DataCell(ft.Text(partner["partner_number"])),
                                    ft.DataCell(ft.Text(partner["partner_name"])),
                                    ft.DataCell(ft.Text(str(partner["hours"]))),
                                    ft.DataCell(ft.Text(f"${partner['exact_amount']:.2f}")),
                                ]
                            ) for partner in dist["partners"]
                        ],
                        border=ft.border.all(1, ft.colors.BLACK38),
                        horizontal_lines=ft.border.all(1, ft.colors.BLACK12),
                    ),
                    # View details button
                    ft.ElevatedButton(
                        "View Full Details",
                        icon=ft.icons.VISIBILITY,
                        on_click=lambda e, idx=i: self.view_history_item(idx),
                    ),
                ],
            )
            
            # Add item to history list
            self.history_list.controls.append(item)
            
        # Update the page
        self.page.update()
        
    def view_history_item(self, index):
        """View details of a history item"""
        # Get the distribution
        dist = self.tips_history[index]
        
        # Update current distribution
        self.current_distribution = dist
        
        # Update results table
        self.update_results_table(dist["partners"], any("cash_amount" in partner for partner in dist["partners"]))
        
        # Show results section
        self.toggle_section_visibility(results_visible=True)
        
    def reset_app(self, e):
        """Reset the app to the initial state"""
        # Clear fields
        self.ocr_text.value = ""
        self.total_tips_input.value = ""
        
        # Clear partner rows
        self.partner_rows = []
        self.partner_data_list.controls.clear()
        
        # Clear results table
        self.results_table.rows.clear()
        
        # Show only input section
        self.toggle_section_visibility(input_visible=True)
        
        # Update the page
        self.page.update()
        
    def download_ocr_text(self, e):
        """Download the OCR text as a file"""
        if not self.ocr_text.value:
            self.show_error("No OCR text to download.")
            return
            
        # Create a temporary file
        self.page.launch_url(
            f"data:text/plain;charset=utf-8,{self.ocr_text.value.replace('\n', '%0A')}"
        )
        
    def download_as_table(self, e):
        """Download the distribution results as an HTML table"""
        if not hasattr(self, "current_distribution"):
            self.show_error("No distribution to download.")
            return
            
        try:
            # Generate HTML content
            html_content = self.generate_html_table()
            
            # Create a data URL for the file
            data_url = f"data:text/html;charset=utf-8,{html_content.replace(' ', '%20').replace('\n', '%0A')}"
            
            # Launch URL to download
            self.page.launch_url(data_url)
            
        except Exception as e:
            self.show_error(f"Error downloading table: {str(e)}")
            
    def generate_html_table(self):
        """Generate HTML table for download"""
        # Get current distribution
        dist = self.current_distribution
        
        # Create HTML content
        html = f"""
        <!DOCTYPE html>
        <html lang="en">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Tip Distribution - {dist['week']}</title>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 20px; }}
                h1, h2 {{ color: #00704A; }}
                table {{ width: 100%; border-collapse: collapse; margin: 20px 0; }}
                th {{ background-color: #00704A; color: white; padding: 10px; text-align: left; }}
                td {{ padding: 8px; border-bottom: 1px solid #ddd; }}
                tr:nth-child(even) {{ background-color: #f2f2f2; }}
                .summary {{ background-color: #f9f9f9; padding: 15px; border-radius: 5px; margin: 20px 0; }}
                @media print {{
                    body {{ font-size: 12pt; }}
                    .no-print {{ display: none; }}
                }}
            </style>
        </head>
        <body>
            <h1>Tip Distribution Details</h1>
            <div class="summary">
                <h2>Summary</h2>
                <p><strong>Week:</strong> {dist['week']}</p>
                <p><strong>Total Tips:</strong> ${dist['total_tips']:.2f}</p>
                <p><strong>Total Hours:</strong> {dist['total_hours']}</p>
                <p><strong>Distribution Method:</strong> {dist['distribution_method']}</p>
            </div>
            
            <h2>Partner Details</h2>
            <table>
                <thead>
                    <tr>
                        <th>Partner #</th>
                        <th>Name</th>
                        <th>Hours</th>
                        <th>Exact Amount</th>
                        <th>Cash Amount</th>
                        <th>Bills Distribution</th>
                    </tr>
                </thead>
                <tbody>
        """
        
        # Add rows for each partner
        for partner in dist['partners']:
            # Format bills display
            bills_display = ""
            if "bills" in partner:
                bills_list = []
                for denom, count in partner["bills"].items():
                    bills_list.append(f"{count}x${denom}")
                bills_display = ", ".join(bills_list)
                
            # Add row
            html += f"""
                    <tr>
                        <td>{partner['partner_number']}</td>
                        <td>{partner['partner_name']}</td>
                        <td>{partner['hours']}</td>
                        <td>${partner['exact_amount']:.2f}</td>
                        <td>${partner.get('cash_amount', 'N/A')}</td>
                        <td>{bills_display}</td>
                    </tr>
            """
            
        # Close table and HTML
        html += """
                </tbody>
            </table>
            
            <div class="no-print">
                <p><em>Generated by TipJar - Made by William Walsh - Starbucks Store# 69600</em></p>
            </div>
        </body>
        </html>
        """
        
        return html
        
    def show_success(self, message):
        """Display a success snackbar"""
        self.page.snack_bar = ft.SnackBar(
            content=ft.Text(message),
            bgcolor="#00704A",
        )
        self.page.snack_bar.open = True
        self.page.update()

    def process_document(self, e):
        """Process the uploaded document or URL"""
        # Check if we have something to process
        if self.source_type_radio.value == "URL" and not self.url_input.value:
            self.show_error("Please enter a URL.")
            return
        elif self.source_type_radio.value == "Local Upload" and not hasattr(self, "selected_file"):
            self.show_error("Please select a file.")
            return
            
        # Show loading indicator
        self.page.splash = ft.ProgressBar()
        self.page.update()
        
        try:
            # Process based on source type
            if self.source_type_radio.value == "URL":
                # Process URL
                url = self.url_input.value
                
                # Download the file
                response = requests.get(url, stream=True)
                response.raise_for_status()
                
                # Get content type
                content_type = response.headers.get("Content-Type", "")
                
                if "pdf" in content_type or url.lower().endswith(".pdf"):
                    # Handle PDF from URL
                    file_content = response.content
                    # Show PDF preview placeholder
                    self.preview_image.visible = False
                    self.preview_pdf.visible = True
                    
                    # Extract text based on AI provider
                    ocr_text = self.extract_text_from_pdf(file_content)
                    
                elif "image" in content_type or any(url.lower().endswith(ext) for ext in [".jpg", ".jpeg", ".png"]):
                    # Handle image from URL
                    file_content = response.content
                    # Show image preview
                    self.preview_image.src_base64 = base64.b64encode(file_content).decode("utf-8")
                    self.preview_image.visible = True
                    self.preview_pdf.visible = False
                    
                    # Extract text based on AI provider
                    ocr_text = self.extract_text_from_image(file_content)
                    
                else:
                    self.show_error(f"Unsupported content type: {content_type}")
                    self.page.splash = None
                    self.page.update()
                    return
                    
            else:  # Local Upload
                # Read file content
                with open(self.selected_file.path, "rb") as f:
                    file_content = f.read()
                
                if self.file_type_radio.value == "PDF":
                    # Show PDF preview placeholder
                    self.preview_image.visible = False
                    self.preview_pdf.visible = True
                    
                    # Extract text based on AI provider
                    ocr_text = self.extract_text_from_pdf(file_content)
                    
                else:  # Image
                    # Show image preview
                    self.preview_image.src_base64 = base64.b64encode(file_content).decode("utf-8")
                    self.preview_image.visible = True
                    self.preview_pdf.visible = False
                    
                    # Extract text based on AI provider
                    ocr_text = self.extract_text_from_image(file_content)
            
            # Update OCR text field
            self.ocr_text.value = ocr_text
            
            # Show download button for OCR text
            self.download_ocr_button.visible = True
            self.download_text_button.visible = True
            
            # Show OCR result section
            self.toggle_section_visibility(ocr_result_visible=True)
            
        except Exception as e:
            self.show_error(f"Error processing document: {str(e)}")
            
        finally:
            # Hide loading indicator
            self.page.splash = None
            self.page.update()
            
    def extract_text_from_pdf(self, pdf_content):
        """Extract text from PDF using selected AI provider"""
        if self.ai_provider_dropdown.value == "Mistral":
            return self.extract_text_with_mistral(pdf_content, "pdf")
        else:  # Gemini
            return self.extract_text_with_gemini(pdf_content, "pdf")
    
    def extract_text_from_image(self, image_content):
        """Extract text from image using selected AI provider"""
        if self.ai_provider_dropdown.value == "Mistral":
            return self.extract_text_with_mistral(image_content, "image")
        else:  # Gemini
            return self.extract_text_with_gemini(image_content, "image")
    
    def extract_text_with_mistral(self, content, content_type):
        """Extract text using Mistral AI"""
        try:
            # Create Mistral client
            client = MistralClient(api_key=MISTRAL_API_KEY)
            
            # Encode content as base64
            content_b64 = base64.b64encode(content).decode("utf-8")
            
            # Create prompt based on content type
            if content_type == "pdf":
                prompt = "This is a PDF containing partner information. Extract all text from this PDF, focusing on partner numbers, names, and hours worked."
            else:  # image
                prompt = "This is an image containing partner information. Extract all text from this image, focusing on partner numbers, names, and hours worked."
            
            # Make API call
            response = client.chat(
                model="mistral-large-latest",
                messages=[
                    {"role": "user", "content": [
                        {"type": "text", "text": prompt},
                        {"type": "image_url", "image_url": {"url": f"data:application/{content_type};base64,{content_b64}"}}
                    ]}
                ]
            )
            
            # Return extracted text
            return response.choices[0].message.content
            
        except Exception as e:
            return f"Error with Mistral AI: {str(e)}"
    
    def extract_text_with_gemini(self, content, content_type):
        """Extract text using Google Gemini"""
        try:
            # Configure Gemini
            genai.configure(api_key=GEMINI_API_KEY)
            
            # Create model
            model = genai.GenerativeModel('gemini-pro-vision')
            
            # Prepare image for Gemini
            if content_type == "image":
                image = Image.open(io.BytesIO(content))
            else:  # PDF
                # For PDFs, we'll use a placeholder image and include the PDF
                # as base64 in the prompt since Gemini doesn't directly support PDFs
                image = Image.new('RGB', (1, 1), color='white')
                
            # Create prompt
            if content_type == "pdf":
                prompt = "This is a PDF containing partner information. Extract all text from this PDF, focusing on partner numbers, names, and hours worked."
            else:  # image
                prompt = "This is an image containing partner information. Extract all text from this image, focusing on partner numbers, names, and hours worked."
            
            # Generate content
            response = model.generate_content([prompt, image])
            
            # Return extracted text
            return response.text
            
        except Exception as e:
            return f"Error with Gemini: {str(e)}"
            
    def toggle_section_visibility(self, input_visible=False, ocr_result_visible=False, 
                             partner_data_visible=False, tip_allocation_visible=False, 
                             results_visible=False, history_visible=False):
        """Toggle the visibility of different sections"""
        # Update visibility of each section
        self.input_section.visible = input_visible
        self.ocr_result_section.visible = ocr_result_visible
        self.partner_data_section.visible = partner_data_visible
        self.tip_allocation_section.visible = tip_allocation_visible
        self.results_section.visible = results_visible
        self.history_section.visible = history_visible
        
        # Update the page
        self.page.update()

def main(page: ft.Page):
    # Create the app
    app = TipJarApp(page)
    
    # Run the app
    page.add(app)

if __name__ == "__main__":
    ft.app(target=main, assets_dir="assets")