import streamlit as st
import gradio as gr
import os
from app import demo

# Configure page
st.set_page_config(layout="wide", page_title="TipJar", page_icon="💰")

# Custom CSS to hide Streamlit elements and make Gradio take full width
st.markdown("""
<style>
    /* Hide Streamlit elements */
    header {display: none !important;}
    #MainMenu {display: none !important;}
    footer {display: none !important;}
    .stDeployButton {display: none !important;}
    
    /* Make Gradio take full width */
    .main > div {
        max-width: 100% !important;
        padding-top: 0 !important;
        padding-left: 0 !important;
        padding-right: 0 !important;
    }
    
    .stApp {
        margin: 0 auto;
    }

    iframe {
        width: 100%;
        height: 100vh;
        border: none;
    }
</style>
""", unsafe_allow_html=True)

# Title only shows momentarily before the iframe loads
st.title("TipJar (Gradio Version)")
st.caption("Loading Gradio interface...")

# Launch the Gradio interface
gr_app = gr.TabbedInterface.from_gradio_blocks(demo)

# Mount the Gradio app in an iframe
# First create a local port with the Gradio app
gradio_app = gr_app.launch(share=False, prevent_thread_lock=True)

# Get the local URL where the Gradio app is running
gradio_url = gradio_app.local_url

# Embed the Gradio app in an iframe
st.components.v1.iframe(gradio_url, height=900, scrolling=True)

# Add a note at the bottom
st.markdown("""
---
**Note**: This is the Gradio version of TipJar embedded in Streamlit. For the best mobile experience, access the Gradio app directly.
""") 