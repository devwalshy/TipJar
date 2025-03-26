# TipJar App (Gradio Version)

A Gradio-based web application for automating tip calculations and cash distribution for Starbucks service teams, optimized for mobile devices.

## Features

- Process partner hours from PDF or image files
- Calculate individual tips based on hours worked
- Distribute cash bills equitably among partners
- Display detailed distribution breakdowns
- Mobile-optimized interface

## Mobile-Friendly Features

- **Responsive Design**: Automatically adapts to screen size
- **Touch-Optimized Controls**: Larger buttons and inputs for easy interaction
- **Tab-Based Navigation**: Simplified interface with tabs instead of complex layouts
- **Collapsible Sections**: Accordion panels to save screen space
- **Home Screen Installation**: Can be added to mobile home screens like a native app
- **Application Manifest**: Proper web app capabilities for mobile devices
- **Custom Loading Screen**: Professional loading experience

## Installation

1. **Clone the repository (if you haven't already)**

2. **Navigate to the gradio_app directory**
   ```bash
   cd gradio_app
   ```

3. **Create a virtual environment (optional but recommended)**
   ```bash
   python -m venv venv
   
   # On Windows:
   venv\Scripts\activate
   
   # On macOS/Linux:
   source venv/bin/activate
   ```

4. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

5. **Set up API keys**
   Create a `.env` file in the gradio_app directory with the following content:
   ```
   MISTRAL_API_KEY=your_mistral_api_key
   GEMINI_API_KEY=your_gemini_api_key
   ```

## Usage

1. **Start the application**
   ```bash
   python app.py
   ```

2. **Access the app**
   The app will be available at http://localhost:7860 in your web browser.

   For the best mobile experience, open index.html which provides a mobile-optimized wrapper.

3. **Using the app**
   - Select the AI provider (Mistral or Gemini)
   - Choose between PDF or Image file types using the tabs
   - Upload your file
   - Enter the total tips amount and available bills
   - Click "Process Tips" to generate the tip distribution

4. **On Mobile Devices**
   - Visit the app URL on your mobile browser
   - For the best experience, add to your home screen when prompted
   - Use in full-screen mode for an app-like experience

## Why Gradio?

Gradio offers several advantages over Streamlit for this application:

1. **Better mobile responsiveness** - Gradio provides a more optimized mobile experience
2. **Simpler interface** - Cleaner UI with fewer distractions
3. **Faster loading times** - Gradio apps typically load faster than Streamlit
4. **More control over layout** - Greater flexibility in UI component arrangement
5. **Easy deployment** - Simple deployment options, including Hugging Face Spaces integration

## Notes on Tip Calculation

- The hourly tip rate is calculated precisely without rounding
- Each partner's tip amount is rounded only to the nearest cent (e.g., $43.1725 → $43.17)
- The display also shows the dollar-rounded amount for quick reference ($43.17 → $43)
- Cash distribution uses the cent-precise amounts for accuracy

## Note

This is a converted version of the original Streamlit app. Both versions provide the same core functionality, but this Gradio version is optimized for mobile use.

## Deployment Options

### 1. Standalone Gradio Deployment

To deploy the Gradio app as a standalone application:

```bash
# Navigate to the gradio_app directory
cd gradio_app

# Install dependencies
pip install -r requirements.txt

# Launch the app
python app.py
```

### 2. Streamlit Integration

This app can also be deployed through Streamlit using the included wrapper:

```bash
# Navigate to the gradio_app directory
cd gradio_app

# Install Streamlit-specific requirements
pip install -r requirements-streamlit.txt

# Launch the Streamlit wrapper
streamlit run streamlit_wrapper.py
```

### 3. GitHub Deployment

The app is already set up to be deployed directly from GitHub:

1. **For Streamlit Cloud**:
   - Connect your GitHub repository to Streamlit Cloud
   - Set the main file path to `gradio_app/streamlit_wrapper.py`
   - Configure your API keys as secrets in the Streamlit dashboard

2. **For Hugging Face Spaces**:
   - Create a new Gradio Space
   - Connect to your GitHub repository
   - Set the file path to `gradio_app/app.py`
   - Add your API keys as secrets 