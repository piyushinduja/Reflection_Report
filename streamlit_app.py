import streamlit as st
from openai import OpenAI
from dotenv import load_dotenv
import os
from collections import defaultdict
import re
import json
import sys
import pandas as pd
import google.generativeai as genai
import io
from ghl_integration import GoHighLevelClient, fetch_participants_from_ghl, test_ghl_connection
from google_docs_integration import create_google_doc

try:
    from dotenv import load_dotenv
    load_dotenv("../../.env")
except:
    pass

# Initialize session state
if 'api_key' not in st.session_state:
    st.session_state.api_key = os.getenv("GEMINI_API_KEY", "")
if 'ghl_api_key' not in st.session_state:
    st.session_state.ghl_api_key = os.getenv("GHL_API_KEY", "")
if 'ghl_location_id' not in st.session_state:
    st.session_state.ghl_location_id = os.getenv("GHL_LOCATION_ID", "")

def process_innovators_table(transcripts, df, it_date, host_speaker):
    """Main processing function that mirrors the original logic"""
    
    # Initialize client with API key
    client = genai.Client(api_key=st.session_state.api_key)
    
    speaker_rsvp_details = {}
    for index, row in df.iterrows():
        speaker_rsvp_details[f"Speaker {index + 1}"] = {
            "name": row["First name"] + " " + row["Last name"],
            "company": row["Company Name"],
            "industry": row["Industry"],
            "role": row["Role"],
            "what_their_company_solves": row["What their company solves."],
            "challenge": row["What is the biggest challenge you are currently facing in your business?"],
            "superpower": row["What is your superpower—the one thing you do exceptionally well that could help others?"],
        }

    speaker_rsvp_details["Host"] = {
        "name": "Dalton Locke",
        "company": "MIT-45, PONO.AI, Spiritual Capitalist, Innovators Table",
        "industry": "Other",
        "role": "Owner/CEO",
        "superpower": "Helping business owners solve their biggest challenges.",
    }

    # Display speaker details
    st.subheader("Identified Speakers:")
    for speaker in speaker_rsvp_details:
        st.write(f"**{speaker}**: {speaker_rsvp_details[speaker]['name']}")

    # Process each speaker
    all_booklets = []
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    speakers_to_process = [s for s in speaker_rsvp_details if s != "Host"]
    total_speakers = len(speakers_to_process)
    
    for idx, speaker in enumerate(speakers_to_process):
        status_text.text(f"Processing {speaker}: {speaker_rsvp_details[speaker]['name']}...")
        
        st.write(f"\n### Extracting speaker transcripts for {speaker}...")

        response = client.models.generate_content(
            model="gemini-3-pro-preview",
            contents=f"""You are given a meeting transcipts of an event called the Innovators Table and the event has 7-10 people, including a host. The main purpose of the meeting is that each attendee share their biggest business challenges and the entire table tries to solve that. The host facilitates the meeting and ensures that each attendee gets a chance to share their challenge.
            
            You are also given the RSVP details of a speaker and your task is to extract the speaker's transcript from the meeting transcripts. Usually, the flow of the meeting is that each attendee starts by intorducing themselves, they talk about their business and share their biggest challenges. And we are interested in extracting the exact transcripts where the target attendee talks about their business and their biggest challenges.
            
            Target Attendee: {speaker_rsvp_details[speaker]}
            
            Meeting Transcripts: {transcripts}""",
        )

        speaker_transcripts = ""
        try:
            speaker_transcripts = response.text
        except Exception:
            speaker_transcripts = json.dumps(response, default=str)
        
        if len(speaker_transcripts) < 20:
            st.error(f"Speaker transcripts for {speaker} looks empty or too short.")
            continue
        
        st.write("Designing the follow-up booklet for the speaker...")

        follow_up_prompt_template = """You are given a predefined output template, detailed speaker information, and a full transcript from a single speaker at a private founder dinner event. The event is an intimate Innovators Table gathering where 7–10 founders openly discuss their businesses and challenges. Your role is to transform this one speaker’s raw, messy spoken transcript into a clean, professional follow-up document that exactly matches the provided output format. You must stay strictly grounded in the information from the speaker details and transcript, without inventing or assuming anything. The purpose is to create a ready-to-send recap that clearly captures the speaker’s context, challenges, insights, and next steps in a structured, polished way.

            Your goal is to generate a clear, actionable follow-up document based on:
            1. A predefined OUTPUT FORMAT template.
            2. Detailed SPEAKER DETAILS.
            3. Raw SPEAKER TRANSCRIPTS from a meeting.

            Task: Carefully read all three sections below, then produce a polished follow-up document that strictly follows the OUTPUT FORMAT structure and uses only information grounded in the speaker details and transcripts.

            Document Generation rules:
            - No emojis
            - No long dashes (indicating AI-generated document)
            - No tables, use bulleted list instead

            You will receive input in this structure:

            OUTPUT FORMAT:

            [Month Year] | Confidential Strategic Document
            [Company Name] - Innovators Table Strategic Brief

            What Happened at Your Table
            On [IT_Date], you sat with [Number_of_people] entrepreneurs at the Innovators Table. Over 3 hours, we explored real challenges, shared hard-won insights, and created actionable pathways forward. This brief captures what matters most for YOUR business—the insights, connections, and immediate actions that can create momentum in the next 14 days.

            Why This Matters Now:
            [1-2 sentences about urgency/timing for their specific situation]

            YOUR 5-MINUTE WIN (Do This Right Now):
            [One tiny action they can complete immediately - e.g., "Text [Name] right now: 'Great meeting you at the table. Coffee this week?'" or "Block 30 minutes on your calendar for Action #1"]

            Why this matters: Momentum starts with the first step, no matter how small.

            Your Situation: What We Heard
            Company: [Company Name]
            Industry: [Industry]
            Current Revenue: [Revenue range]
            Team Size: [Number]
            Time in Business: [Duration]
            Your Primary Challenge:
            [One paragraph summary of their main problem stated at table]
            Quote from You:
            "[Direct quote from transcript that captures their situation]"

            What We Observed:
            [Observation 1 about their business/situation]
            [Observation 2 about their business/situation]
            [Observation 3 about their business/situation]

            Key Insights from the Table
            These are the most valuable insights specifically for your situation:
            Insight #1: [Main Insight]
            [2-3 sentences explaining the insight and why it matters for them]
            Insight #2: [Second Insight]
            [2-3 sentences explaining the insight and why it matters for them]
            Insight #3: [Third Insight]
            [2-3 sentences explaining the insight and why it matters for them]

            Resources Mentioned:
            [Book/Tool/Contact mentioned at table]
            [Book/Tool/Contact mentioned at table]
            [Book/Tool/Contact mentioned at table]

            Your 7-Day Action Plan
            These three actions will create the most momentum for your business this week:
            Action #1: [Specific Action]
            Why: [Why this matters]
            How: [Specific steps to take]
            Deadline: [Day/Date]
            Action #2: [Specific Action]
            Why: [Why this matters]
            How: [Specific steps to take]
            Deadline: [Day/Date]
            Action #3: [Specific Action]
            Why: [Why this matters]
            How: [Specific steps to take]
            Deadline: [Day/Date]

            Success Tracker (Check Off as You Complete):
            ☐ Action #1 completed by [Date]
            ☐ Action #2 completed by [Date]
            ☐ Action #3 completed by [Date]
            ☐ Connected with [Name 1]
            ☐ Connected with [Name 2]
            ☐ Progress email sent to request full Strategic Mirror Document

            IF YOU ONLY DO ONE THING THIS WEEK:
            [The single highest-impact action from your 3 actions above]
            Do this, and everything else becomes easier.

            Success Metrics (How to Know You're Winning):
            Week 1: [Specific metric - e.g., "You've scheduled 2 key conversations"]
            Week 2: [Specific metric - e.g., "You have clarity on your decision and next steps"]
            30 Days: [Specific outcome - e.g., "Deal in progress OR revenue increased 15%"]

            Connections to Make
            People from the table who can help you:
            [Name] - [Company]
            Why connect: [Specific reason relevant to their business]
            Suggested approach: [How to reach out]
            [Name] - [Company]
            Why connect: [Specific reason relevant to their business]
            Suggested approach: [How to reach out]

            What Others Are Saying
            Previous Innovators Table attendees who implemented their action plans:

            "It was a great experience! I feel lucky to be able to get to know so many amazing individuals. I’ve never had a discussion like that where business builders were just so open with each other and really listen and give advice that saved us a lot of time and money going down the wrong path."
            Charlie Gomez, Founder and CEO at CG Trades

            "This was single-handedly the most beneficial and rewarding professional meeting I’ve had in years. And it didn’t even end up just being about work, it centered on how I can be a better person. I loved the experience! The other people in the room had incredibly insightful feedback for me."
            Chase Huntzinger, CEO at Piton Ventures & CFO at Second Chair AI

            "The dinner meeting offered a great opportunity to exchange ideas, gain perspective from others in the field, and explore potential collaborations. It was both productive and enjoyable."
            Jeremy L Christensen, Chairman/CEO at Euldora Financial


            What's Next: Your Full Strategic Mirror Document
            This brief gives you immediate actions for the next 14 days. But there's more.
            Your Full Strategic Mirror Document includes:
            Complete 30/60/90 day transformation roadmap
            Detailed implementation frameworks and templates
            Financial projections and models specific to your situation
            Step-by-step playbooks for your biggest challenges
            Complete resource guide with all connections and tools
            Strategic analysis of your competitive position
            The full document is typically 15-20 pages of customized strategy.

            To receive your complete Strategic Mirror Document:
            Implement the 7-day action plan above
            Email your progress update to: dalton@theinnovatorstable.com
            The full document is reserved for those who take action. Complete your 7-day plan, and we'll send you the complete strategic roadmap.

            Stuck or Have Questions? Reach out:
            Email: dalton@theinnovatorstable.com
            Text: +1 (801) 555-0123 (yes, really)
            We want you to succeed. If you hit a wall, ask for help.

            We would love to hear about:
            What you implemented from this brief
            Results you achieved
            Your next biggest challenge

            The table is watching. Make us proud.

            Document prepared for: [Name]
            Innovators Table | [Month Year]


            SPEAKER DETAILS:
            <<speaker_details>>

            OTHER ATTENDEES ON THE TABLE:
            <<other_attendees>>

            SPEAKER TRANSCRIPTS:
            <<speaker_transcripts>>"""

        follow_up_prompt = follow_up_prompt_template.replace("<<speaker_details>>", json.dumps(speaker_rsvp_details[speaker], indent=2, ensure_ascii=False))
        follow_up_prompt = follow_up_prompt.replace("<<speaker_transcripts>>", speaker_transcripts)
        follow_up_prompt = follow_up_prompt.replace("<<other_attendees>>", json.dumps({k:v for k, v in speaker_rsvp_details.items() if k!=speaker}, indent=2, ensure_ascii=False))
        follow_up_prompt = follow_up_prompt.replace("[IT_Date]", f"{it_date}_2025")
        follow_up_prompt = follow_up_prompt.replace("[Number_of_people]", str(len(speaker_rsvp_details)))
        follow_up_prompt = follow_up_prompt.replace("[Month Year]", "November 2025")

        response = client.models.generate_content(
            model="gemini-3-pro-preview",
            contents=follow_up_prompt,
        )

        follow_up_booklet = ""
        try:
            follow_up_booklet = response.text
        except Exception:
            follow_up_booklet = json.dumps(response, default=str)
        
        if len(follow_up_booklet) < 20:
            st.error(f"Follow Up Booklet for {speaker} looks empty or too short.")
            continue
        
        all_booklets.append(follow_up_booklet)
        all_booklets.append("\n" + "="*100 + "\n")
        
        # Update progress
        progress_bar.progress((idx + 1) / total_speakers)
    
    status_text.text("Processing complete!")
    
    return "\n".join(all_booklets)

def main():
    st.set_page_config(page_title="Innovators Table Follow-up Generator", layout="wide")

    # Initialize session state for result
    if 'generated_result' not in st.session_state:
        st.session_state.generated_result = None
    if 'result_filename' not in st.session_state:
        st.session_state.result_filename = None
    
    st.title("🚀 Innovators Table Follow-up Booklet Generator")
    st.markdown("Fetch participants from GoHighLevel or upload CSV, then generate personalized follow-up booklets.")
    
    # Sidebar for configuration
    with st.sidebar:
        st.header("⚙️ Configuration")
        
        # Gemini API Key
        api_key_input = st.text_input(
            "Gemini API Key", 
            value=st.session_state.api_key,
            type="password",
            help="Enter your Google Gemini API key"
        )
        if api_key_input:
            st.session_state.api_key = api_key_input
        
        st.markdown("---")
        
        # GoHighLevel Credentials
        st.subheader("🔗 GoHighLevel API")
        ghl_api_key = st.text_input(
            "GHL API Key",
            value=st.session_state.ghl_api_key,
            type="password",
            help="Your GoHighLevel API key"
        )
        if ghl_api_key:
            st.session_state.ghl_api_key = ghl_api_key
        
        ghl_location_id = st.text_input(
            "GHL Location ID",
            value=st.session_state.ghl_location_id,
            help="Your GoHighLevel Location ID"
        )
        if ghl_location_id:
            st.session_state.ghl_location_id = ghl_location_id
        
        # Test GHL connection
        if st.button("🔍 Test GHL Connection"):
            if st.session_state.ghl_api_key and st.session_state.ghl_location_id:
                with st.spinner("Testing connection..."):
                    if test_ghl_connection(st.session_state.ghl_api_key, st.session_state.ghl_location_id):
                        st.success("✅ GHL Connected!")
                    else:
                        st.error("❌ Connection Failed")
            else:
                st.warning("Please enter both API Key and Location ID")
        
        st.markdown("---")
        
        # Event settings
        it_date = st.text_input("Event Date (format: MM_DD)", value="11_19")
        host_speaker = st.text_input("Host Speaker ID", value="Speaker 2")
        
        st.markdown("---")
        st.markdown("### About")
        st.markdown("This app processes Innovators Table meeting transcripts and generates personalized follow-up booklets.")
    
    # Main content - tabs for different input methods
    tab1, tab2 = st.tabs(["📊 Upload CSV", "🔗 Fetch from GoHighLevel"])
    
    df = None
    
    with tab1:
        st.header("📊 Upload RSVP CSV")
        uploaded_file = st.file_uploader(
            "Upload the RSVP CSV file", 
            type=['csv'],
            help="CSV should contain required columns for participant information"
        )
        
        if uploaded_file is not None:
            try:
                df = pd.read_csv(uploaded_file)
                st.success(f"✅ CSV uploaded successfully! Found {len(df)} attendees.")
                
                with st.expander("Preview CSV Data"):
                    st.dataframe(df.head())
                    
                required_columns = [
                    "First name", "Last name", "Company Name", "Industry", 
                    "Role", "What their company solves.",
                    "What is the biggest challenge you are currently facing in your business?",
                    "What is your superpower—the one thing you do exceptionally well that could help others?"
                ]
                missing_columns = [col for col in required_columns if col not in df.columns]
                
                if missing_columns:
                    st.error(f"❌ Missing required columns: {', '.join(missing_columns)}")
                    st.info("Available columns: " + ", ".join(df.columns.tolist()))
                    df = None
                    
            except Exception as e:
                st.error(f"❌ Error reading CSV: {str(e)}")
                df = None
    
    with tab2:
        st.header("🔗 Fetch from GoHighLevel")
        
        if not st.session_state.ghl_api_key or not st.session_state.ghl_location_id:
            st.warning("⚠️ Please configure GoHighLevel credentials in the sidebar first.")
        else:
            st.info("Enter participant identifiers (one per line)")
            
            col1, col2 = st.columns([2, 1])
            
            with col1:
                identifiers_text = st.text_area(
                    "Participant Identifiers",
                    height=200,
                    placeholder="john@example.com\njane@example.com\n+1234567890\nJohn Smith",
                    help="Enter emails, phone numbers, or names (one per line)"
                )
            
            with col2:
                search_type = st.selectbox(
                    "Search Type",
                    ["auto", "email", "phone", "name"],
                    help="auto: Automatically detect type\nemail: Search by email only\nphone: Search by phone only\nname: Search by name only"
                )
                
                st.markdown("**Note:**")
                st.markdown("- GHL custom fields must match expected names")
                st.markdown("- API rate limits apply")
            
            if st.button("📥 Fetch Participants from GHL", type="primary"):
                if identifiers_text:
                    identifiers = [line.strip() for line in identifiers_text.split("\n") if line.strip()]
                    
                    # Create placeholder for progress
                    progress_bar = st.progress(0)
                    status_text = st.empty()
                    log_container = st.expander("📋 Fetch Log", expanded=True)
                    
                    try:
                        # Progress callback
                        def update_progress(value):
                            progress_bar.progress(value)
                        
                        status_text.text(f"Fetching {len(identifiers)} participants from GoHighLevel...")
                        
                        df, messages = fetch_participants_from_ghl(
                            st.session_state.ghl_api_key,
                            st.session_state.ghl_location_id,
                            identifiers,
                            progress_callback=update_progress
                        )
                        
                        # Display log messages
                        with log_container:
                            for msg in messages:
                                st.text(msg)
                        
                        # Clear progress indicators
                        progress_bar.empty()
                        status_text.empty()
                        
                        if len(df) > 0:
                            st.success(f"✅ Fetched {len(df)} participants!")
                            
                            # Store in session state
                            st.session_state['fetched_df'] = df
                            
                            with st.expander("Preview Fetched Data", expanded=True):
                                st.dataframe(df)
                        else:
                            st.warning("⚠️ No participants found. Check your identifiers.")
                            df = None
                            
                    except Exception as e:
                        st.error(f"❌ Error fetching from GHL: {str(e)}")
                        df = None
                else:
                    st.warning("Please enter at least one identifier")
    
    # Transcripts section (common to both tabs)
    st.markdown("---")
    st.header("📝 Meeting Transcripts")
    transcripts = st.text_area(
        "Paste the meeting transcripts here",
        height=300,
        help="Paste the full transcript of the Innovators Table meeting"
    )
    
    if transcripts:
        word_count = len(transcripts.split())
        st.info(f"📊 Transcript length: {len(transcripts)} characters, ~{word_count} words")
        
        if len(transcripts) < 20:
            st.warning("⚠️ Transcript seems too short. Please ensure you've pasted the complete transcript.")
    
    # Process button
    st.markdown("---")
    
    if st.button("🎯 Generate Follow-up Booklets", type="primary", use_container_width=True):
        # Validation
        if not st.session_state.api_key:
            st.error("❌ Please provide a Gemini API key in the sidebar.")
        else:
            # Check for fetched data in session state
            if 'fetched_df' in st.session_state and st.session_state['fetched_df'] is not None:
                df = st.session_state['fetched_df']
            elif df is None or (isinstance(df, pd.DataFrame) and len(df) == 0):
                st.error("❌ Please upload a CSV or fetch participants from GoHighLevel.")
                df = None
            
            if df is not None and (not transcripts or len(transcripts) < 20):
                st.error("❌ Please paste the meeting transcripts.")
            elif df is not None:
                # Process
                try:
                    with st.spinner("🔄 Processing... This may take several minutes."):
                        result = process_innovators_table(transcripts, df, it_date, host_speaker)
                    
                    # Store result in session state
                    st.session_state.generated_result = result
                    st.session_state.result_filename = f"{it_date}_follow_up_booklets"
                    
                    st.success("✅ Follow-up booklets generated successfully!")
                    
                except Exception as e:
                    st.error(f"❌ Error during processing: {str(e)}")
                    st.exception(e)

    # Display results if available (outside the button click)
    if st.session_state.generated_result:
        # Display result
        with st.expander("📄 View Generated Booklets", expanded=True):
            st.text_area(
                "Generated Content", 
                value=st.session_state.generated_result, 
                height=400,
                key="result_display"
            )
        
        # Create two columns for buttons
        col1, col2 = st.columns(2)
        
        # Download button
        with col1:
            st.download_button(
                label="💾 Download Follow-up Booklets",
                data=st.session_state.generated_result,
                file_name=f"{st.session_state.result_filename}.txt",
                mime="text/plain",
                use_container_width=True
            )
        
        # Google Docs button
        with col2:
            if st.button("📝 Send to Google Docs", use_container_width=True, key="gdocs_button"):
                with st.spinner("Creating Google Doc..."):
                    doc_title = f"{st.session_state.result_filename}"
                    response = create_google_doc(doc_title, st.session_state.generated_result)
                    
                    if response['success']:
                        st.success(response['message'])
                        st.markdown(f"[📄 Open Document in Google Docs]({response['document_url']})")
                    else:
                        st.error(response['message'])

if __name__ == "__main__":
    main()

