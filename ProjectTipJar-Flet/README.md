# TipJar Flet App

A Flet-based application for automating tip allocation and cash distribution for service teams.

## Features

- Document OCR with AI support (Mistral and Gemini)
- PDF and Image processing
- Partner data extraction
- Tip calculation (hours-based or equal split)
- Cash distribution with bill denomination breakdown
- Distribution history tracking
- Downloadable reports (OCR text and HTML tables)

## Setup

1. Clone the repository
2. Install dependencies:
   ```
   pip install -r requirements.txt
   ```
3. Create a `.env` file with your API keys:
   ```
   MISTRAL_API_KEY=your_mistral_api_key
   GEMINI_API_KEY=your_gemini_api_key
   ```
4. Run the application:
   ```
   python main.py
   ```

## Usage

1. **Input Section**: Upload a document or provide a URL, select AI provider
2. **OCR Section**: Review extracted text and preview the document
3. **Partner Data**: Enter or verify partner information
4. **Tip Allocation**: Enter total tips and distribution method
5. **Results**: View calculated distribution with bill breakdown
6. **History**: Access previous tip distributions

## Requirements

- Python 3.8+
- See requirements.txt for package dependencies

## Credits

Made by William Walsh - Starbucks Store# 69600

"If there's a Will, There's a Way!" -Lauren 2025 