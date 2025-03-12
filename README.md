# Document OCR & Question Answering App

A Streamlit application that combines OCR (Optical Character Recognition) capabilities with question-answering functionality using Mistral and Gemini AI.

## Features

- **Dual AI Provider Support**: 
  - Mistral AI for both PDF and Image OCR
  - Gemini AI for Image OCR and enhanced question answering

- **Multiple Document Types**:
  - PDF documents (Mistral only)
  - Images (JPG, JPEG, PNG)

- **Flexible Input Methods**:
  - URL input for online documents
  - Local file upload

- **Interactive Features**:
  - Real-time document preview
  - Text extraction with OCR
  - Question-answering based on extracted content
  - Chat history tracking
  - Download OCR results

## Installation

1. Clone the repository:
```bash
git clone <repository-url>
cd <repository-directory>
```

2. Create and activate a virtual environment:
```bash
python -m venv venv
# On Windows
venv\Scripts\activate
# On Unix or MacOS
source venv/bin/activate
```

3. Install the required packages:
```bash
pip install -r requirements.txt
```

## API Keys Required

- **Mistral AI**: Get your API key from [Mistral AI Platform](https://mistral.ai)
- **Gemini AI**: Get your API key from [Google AI Studio](https://makersuite.google.com/app/apikey)

## Usage

1. Run the Streamlit app:
```bash
streamlit run main.py
```

2. Select your preferred AI provider (Mistral or Gemini)

3. Enter your API key for the selected provider

4. Choose document type (PDF/Image) and source type (URL/Local Upload)

5. Process your document and ask questions about its content

## Features in Detail

### OCR Processing
- **Mistral OCR**: 
  - Supports both PDF and image processing
  - Maintains document structure and formatting
  - Works with both local files and URLs

- **Gemini Vision**: 
  - Specialized in image processing
  - Provides detailed text extraction with context
  - Currently does not support PDFs

### Question Answering
- Interactive Q&A interface
- Context-aware responses
- History tracking of all Q&A interactions
- Support for complex queries about document content

### Document Preview
- Built-in PDF viewer
- Image preview support
- Handles both local and URL-based documents

## Limitations

- Gemini AI does not currently support PDF processing
- PDF preview may require browser PDF plugin support
- Maximum file size limits apply based on the AI provider's restrictions

## Troubleshooting

If you encounter issues:

1. **PDF Preview Not Working**:
   - Ensure your browser supports PDF viewing
   - Try using a different browser
   - Check if the PDF URL is accessible

2. **OCR Not Working**:
   - Verify your API key is correct
   - Check if the document is in a supported format
   - Ensure the document is readable and not corrupted

3. **Image Processing Issues**:
   - Confirm the image format is supported (JPG, JPEG, PNG)
   - Check if the image URL is accessible
   - Verify the image file is not corrupted

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is licensed under the MIT License - see the LICENSE file for details. 
