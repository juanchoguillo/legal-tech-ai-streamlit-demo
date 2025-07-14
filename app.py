"""
Streamlit Web Interface for Legal AI Assistant
Run with: streamlit run app.py
"""

import streamlit as st
import os
import sqlite3
import pandas as pd
from crewai import Agent, Task, Crew, Process
from typing import Dict, Any
import csv
from pathlib import Path
from dotenv import load_dotenv
import warnings

# Load environment variables
load_dotenv()

# Suppress warnings for cleaner output
warnings.filterwarnings("ignore")

# Set page config
st.set_page_config(
    page_title="Legal AI Assistant",
    page_icon="⚖️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Embedded LegalAIAssistant class (to avoid import issues)
class LegalAIAssistant:
    def __init__(self, csv_file: str = "litify_matters.csv", db_path: str = "legal_matters.db"):
        self.csv_file = csv_file
        self.db_path = db_path
        self.setup_database_from_csv()
        
    def setup_database_from_csv(self):
        """Initialize SQLite database from CSV file with exact Litify structure"""
        # Create CSV file if it doesn't exist
        if not Path(self.csv_file).exists():
            self.create_sample_csv()
        
        # Read CSV and create database
        try:
            df = pd.read_csv(self.csv_file)
            
            # Create database connection
            conn = sqlite3.connect(self.db_path)
            
            # Create table with simplified names for easier querying
            create_table_query = """
            CREATE TABLE IF NOT EXISTS matters (
                Id TEXT PRIMARY KEY,
                Display_Name TEXT,
                Client_Name TEXT,
                Client_Full_Name TEXT,
                Record_Type TEXT,
                Record_Type_Name TEXT,
                Case_Type TEXT,
                Status TEXT,
                Case_Stage TEXT,
                Case_Sub_Stage TEXT,
                Open_Date TEXT,
                Closed_Date TEXT,
                Primary_Legal_Assistant TEXT,
                Attorney_Name TEXT,
                Assistant_Name TEXT
            )
            """
            
            conn.execute(create_table_query)
            
            # Insert data with simplified column mapping
            for _, row in df.iterrows():
                conn.execute("""
                    INSERT OR REPLACE INTO matters VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    row['Id'],
                    row['litify_pm__Display_Name__c'],
                    row['litify_pm__Client__r'],
                    row['litify_pm__Client__r.bis_Full_Formatted_Name__c'],
                    row['RecordType'],
                    row['RecordType.Name'],
                    row['bis_Case_Type__c'],
                    row['litify_pm__Status__c'],
                    row['Case_Stage__c'],
                    row['Case_Sub_Stage__c'],
                    row['litify_pm__Open_Date__c'],
                    row['litify_pm__Closed_Date__c'],
                    row['Primary_Legal_Assistant__r'],
                    row['bis_Attorney_Name__c'],
                    row['Primary_Legal_Assistant__r.Name']
                ))
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            st.error(f"Error setting up database: {e}")
            raise
    
    def create_sample_csv(self):
        """Create the sample CSV file with your exact data structure"""
        csv_content = """Id,litify_pm__Display_Name__c,litify_pm__Client__r,litify_pm__Client__r.bis_Full_Formatted_Name__c,RecordType,RecordType.Name,bis_Case_Type__c,litify_pm__Status__c,Case_Stage__c,Case_Sub_Stage__c,litify_pm__Open_Date__c,litify_pm__Closed_Date__c,Primary_Legal_Assistant__r,bis_Attorney_Name__c,Primary_Legal_Assistant__r.Name
2ed7148386a56d1db9,Morgan Brown,[Account],Morgan Taylor,[RecordType],Billable Matter,WC WC-IN-HOUSE,Closed,Active,,7/21/23,8/31/23,,Taylor Miller,Riley Lee
77934fca56ba4bd509,Avery Taylor,[Account],Jordan Johnson,[RecordType],Personal Injury,PI AUTO-IN-HOUSE MINOR,Closed,Closed,,7/21/23,9/22/23,,Riley Wilson,Morgan Brown
34a706be1613efd297,Avery Wilson,[Account],Avery Wilson,[RecordType],Personal Injury,PI AUTO-IN-HOUSE,Closed,Pre-Lit Settlement,,7/25/23,3/6/24,,Morgan Taylor,Riley Brown
366b94b5409a51fb68,Morgan Davis,[Account],Jordan Johnson,[RecordType],Personal Injury,PI AUTO-IN-HOUSE,Closed,Closed,,7/22/23,9/8/23,,Taylor Davis,Morgan Miller
e804667b98067fa9ea,Morgan Smith,[Account],Alex Lee,[RecordType],Personal Injury,PI AUTO-IN-HOUSE,Closed,Closed,,7/22/23,8/31/23,,Jordan Davis,Avery Smith
ef911165c148f2a077,Riley Davis,[Account],Casey Miller,[RecordType],Personal Injury,PI AUTO-IN-HOUSE,Closed,Closed,,7/24/23,12/7/23,,Jamie Smith,Taylor Taylor
1183a7eb188081cec9,Taylor Wilson,[Account],Taylor Miller,[RecordType],Personal Injury,PI AUTO-IN-HOUSE,Closed,Closed,,7/22/23,9/8/23,,Riley Miller,Alex Davis
5751485a59c7062197,Alex Davis,[Account],Taylor Lee,[RecordType],Personal Injury,PI AUTO-IN-HOUSE,Closed,Pre-Lit Settlement,,7/22/23,1/22/24,,Riley Lee,Alex Taylor
e94b89a4e1ce6e8626,Morgan Smith,[Account],Morgan Davis,[RecordType],Personal Injury,PI AUTO-IN-HOUSE,Closed,Closed,,7/23/23,4/3/24,,Riley Wilson,Taylor Johnson
0ab59367dd16c0a1e9,Alex Lee,[Account],Riley Miller,[RecordType],Personal Injury,PI AUTO-IN-HOUSE,Closed,Pre-Lit Settlement,,7/24/23,6/7/24,,Casey Johnson,Jamie Smith"""
        
        with open(self.csv_file, 'w', newline='', encoding='utf-8') as f:
            f.write(csv_content)
    
    def execute_query(self, query: str):
        """Execute SQL query and return results"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute(query)
            results = cursor.fetchall()
            columns = [description[0] for description in cursor.description]
            
            # Format results as list of dictionaries
            formatted_results = []
            for row in results:
                record = {}
                for i, col in enumerate(columns):
                    record[col] = row[i] if row[i] is not None else ""
                formatted_results.append(record)
            
            conn.close()
            return formatted_results
            
        except Exception as e:
            conn.close()
            return []
    
    def create_agents(self):
        """Create two focused agents for the legal AI system"""
        
        # Agent 1: SQL Query Generator
        sql_agent = Agent(
            role='SQL Query Generator',
            goal='Convert natural language questions into accurate SQL queries for legal matter database',
            backstory="""You are an expert SQL developer who specializes in legal databases. You understand legal terminology and can translate business questions into precise SQL queries.
            
            The database has a table called 'matters' with these columns:
            - Id (unique identifier)
            - Display_Name (matter name)
            - Client_Name, Client_Full_Name (client information)
            - Record_Type_Name (Personal Injury, Billable Matter, Workers Compensation, etc.)
            - Case_Type (PI AUTO-IN-HOUSE, WC WC-IN-HOUSE, etc.)
            - Status (Active, Closed, Open, etc.)
            - Case_Stage (Active, Closed, Pre-Lit Settlement, etc.)
            - Open_Date, Closed_Date (dates in MM/DD/YY format)
            - Attorney_Name (assigned attorney)
            - Assistant_Name (legal assistant)
            
            Always respond with ONLY the SQL query, no explanations or markdown.""",
            verbose=False,
            allow_delegation=False
        )
        
        # Agent 2: Data Analyst
        data_analyst = Agent(
            role='Legal Data Analyst',
            goal='Analyze legal database results and provide clear, concise business insights',
            backstory="""You are a legal data analyst who provides SHORT, DIRECT answers about legal database results.
            
            Your response style:
            - ALWAYS keep answers SHORT and DIRECT (2-4 sentences max)
            - Start with the direct answer to the question
            - Provide key insights briefly
            - Use conversational but professional tone
            - Give exact numbers and facts from the database
            
            Stay concise and factual.""",
            verbose=False,
            allow_delegation=False
        )
        
        return {
            'sql_generator': sql_agent,
            'data_analyst': data_analyst
        }
    
    def create_chat_agent(self):
        """Create a conversational agent for chat mode with database access"""
        chat_agent = Agent(
            role='Legal Database Chat Assistant',
            goal='Answer questions about legal matters database in a conversational, short and direct way',
            backstory="""You are a legal database assistant that provides quick, direct answers about the firm's legal matters.
            
            Your response style:
            - ALWAYS keep answers SHORT and DIRECT (1-3 sentences max)
            - Answer the specific question asked
            - Use conversational tone but stay focused
            - Provide exact numbers and facts from the database
            
            Stay concise and factual.""",
            verbose=False,
            allow_delegation=False
        )
        
        return chat_agent
    
    def process_query(self, user_query: str) -> str:
        """Process user query through the 2-agent system"""
        
        # Create agents
        agents = self.create_agents()
        
        # Step 1: Generate SQL Query
        sql_task = Task(
            description=f"""
            Convert this natural language question to a SQL query for the legal matters database:
            
            Question: "{user_query}"
            
            Database Information:
            - Table name: matters
            - Available columns: Id, Display_Name, Client_Name, Client_Full_Name, Record_Type_Name, Case_Type, Status, Case_Stage, Open_Date, Closed_Date, Attorney_Name, Assistant_Name
            
            Return ONLY the SQL query, no explanations.
            """,
            expected_output="A single SQL query without any explanations or formatting",
            agent=agents['sql_generator']
        )
        
        # Execute SQL generation
        sql_crew = Crew(
            agents=[agents['sql_generator']],
            tasks=[sql_task],
            process=Process.sequential,
            verbose=False
        )
        
        sql_result = sql_crew.kickoff()
        
        # Clean up the SQL query
        sql_query = str(sql_result).strip()
        sql_query = sql_query.replace('```sql', '').replace('```', '').strip()
        if sql_query.startswith('SQL:'):
            sql_query = sql_query[4:].strip()
        
        # Step 2: Execute the query
        query_results = self.execute_query(sql_query)
        
        if not query_results:
            fallback_query = "SELECT COUNT(*) as total FROM matters"
            query_results = self.execute_query(fallback_query)
            sql_query = fallback_query
        
        # Step 3: Analyze results
        analysis_task = Task(
            description=f"""
            Analyze these legal database results and provide a SHORT, DIRECT answer:
            
            Original Question: "{user_query}"
            Database Results: {query_results}
            
            IMPORTANT: Keep response SHORT (2-4 sentences maximum)
            Start with a DIRECT answer to the user's question.
            """,
            expected_output="Short, direct analysis of the legal data (2-4 sentences max)",
            agent=agents['data_analyst']
        )
        
        # Execute analysis
        analysis_crew = Crew(
            agents=[agents['data_analyst']],
            tasks=[analysis_task],
            process=Process.sequential,
            verbose=False
        )
        
        final_response = analysis_crew.kickoff()
        return str(final_response)
    
    def process_chat(self, user_message: str, conversation_history: list = None) -> str:
        """Process chat message with database access for short, direct answers"""
        
        if conversation_history is None:
            conversation_history = []
        
        # First, try to identify if this is a data question and get database results
        database_context = ""
        sql_query_used = ""
        
        try:
            # Create agents for potential database query
            agents = self.create_agents()
            
            # Generate SQL query with better instructions
            sql_task = Task(
                description=f"""
                Analyze this user message and determine if it needs database information:
                
                User Message: "{user_message}"
                
                Database table 'matters' has columns: Id, Display_Name, Client_Name, Client_Full_Name, Record_Type_Name, Case_Type, Status, Case_Stage, Open_Date, Closed_Date, Attorney_Name, Assistant_Name
                
                Sample data context:
                - Record_Type_Name values: 'Personal Injury', 'Billable Matter'  
                - Status values: 'Closed', 'Active'
                - Case_Stage values: 'Closed', 'Pre-Lit Settlement', 'Active'
                - Attorney names like: 'Taylor Miller', 'Riley Wilson', 'Morgan Taylor'
                
                Rules:
                1. If asking about counts, data, cases, attorneys, clients, matters - generate SQL
                2. If greeting, thanks, or general chat - return: NO_QUERY_NEEDED
                3. Always use exact column names from the schema above
                4. For counting: SELECT COUNT(*) as count FROM matters WHERE...
                5. For attorney questions: SELECT Attorney_Name, COUNT(*) as count FROM matters WHERE Attorney_Name != '' GROUP BY Attorney_Name ORDER BY COUNT(*) DESC
                
                Return ONLY:
                - A valid SQL query (if database question)
                - NO_QUERY_NEEDED (if general chat)
                """,
                expected_output="Either a SQL query or NO_QUERY_NEEDED",
                agent=agents['sql_generator']
            )
            
            sql_crew = Crew(
                agents=[agents['sql_generator']],
                tasks=[sql_task],
                process=Process.sequential,
                verbose=False
            )
            
            sql_result = str(sql_crew.kickoff()).strip()
            
            # Clean up SQL and check if it's a real query
            sql_query = sql_result.replace('```sql', '').replace('```', '').strip()
            sql_query = sql_query.replace('SQL:', '').replace('Query:', '').strip()
            
            # If we have a real SQL query, execute it
            if sql_query != "NO_QUERY_NEEDED" and not sql_query.upper().startswith("NO_QUERY") and len(sql_query) > 10:
                query_results = self.execute_query(sql_query)
                if query_results:
                    database_context = f"\nDatabase Query: {sql_query}\nDatabase Results: {query_results}"
                    sql_query_used = sql_query
                else:
                    # If query failed, try a simple count
                    fallback_query = "SELECT COUNT(*) as count FROM matters"
                    fallback_results = self.execute_query(fallback_query)
                    if fallback_results:
                        database_context = f"\nDatabase Query: {fallback_query}\nDatabase Results: {fallback_results}"
                        sql_query_used = fallback_query
        
        except Exception as e:
            # If there's an error with database query, continue with chat-only mode
            print(f"Database query error: {e}")
            pass
        
        # Create chat agent
        chat_agent = self.create_chat_agent()
        
        # Build conversation context
        context = ""
        if conversation_history:
            context = "Recent conversation:\n"
            for msg in conversation_history[-2:]:  # Last 2 messages for context
                context += f"User: {msg['user']}\nAssistant: {msg['assistant']}\n\n"
        
        # Enhanced chat task with better instructions
        chat_task = Task(
            description=f"""
            Respond to this user message in a SHORT, DIRECT, conversational way:
            
            {context}
            Current User Message: "{user_message}"
            {database_context}
            
            Context about the legal firm database:
            - Contains legal matters/cases with attorneys, clients, case types
            - Personal Injury cases, Workers Compensation, Billable Matters
            - Case stages: Active, Closed, Pre-Lit Settlement
            - Real attorneys: Taylor Miller, Riley Wilson, Morgan Taylor, etc.
            
            CRITICAL INSTRUCTIONS:
            1. Keep answers SHORT (1-3 sentences maximum)
            2. If database results are provided above, USE THEM to answer - don't make up numbers
            3. If no database results, respond conversationally and offer to help with data questions
            4. Be direct and factual - no made-up statistics or case details
            5. For greetings/general chat, be friendly and ask how you can help with legal data
            
            Example good responses:
            - With data: "Based on our database, we have X personal injury cases."
            - Without data: "Hi! I can help you with questions about your legal matters. What would you like to know?"
            - For unclear questions: "I'd be happy to help! Could you clarify what specific information you need about your cases?"
            
            NEVER make up specific numbers, names, or case details that aren't in the database results!
            """,
            expected_output="A short, direct, factual response (1-3 sentences max)",
            agent=chat_agent
        )
        
        # Execute chat response
        chat_crew = Crew(
            agents=[chat_agent],
            tasks=[chat_task],
            process=Process.sequential,
            verbose=False
        )
        
        response = chat_crew.kickoff()
        response_text = str(response)
        
        # Add debug info in development (you can remove this later)
        if sql_query_used:
            print(f"DEBUG - SQL used: {sql_query_used}")
            print(f"DEBUG - Response: {response_text}")
        
        return response_text

# Custom CSS for better styling with improved chat visibility
st.markdown("""
<style>
.main {
    padding-top: 1rem;
}

.stButton > button {
    width: 100%;
    border-radius: 10px;
    border: 1px solid #e0e0e0;
    padding: 0.5rem 1rem;
    margin: 0.25rem 0;
}

.stButton > button:hover {
    border-color: #1f77b4;
    background-color: #f0f8ff;
}

.chat-message {
    padding: 1.2rem;
    border-radius: 12px;
    margin: 0.8rem 0;
    border: 2px solid #ddd;
    font-size: 16px;
    line-height: 1.5;
}

.user-message {
    background-color: #0084ff;
    color: white;
    border-left: 4px solid #0066cc;
    margin-left: 20%;
}

.user-message strong {
    color: #ffffff;
    font-weight: bold;
}

.assistant-message {
    background-color: #f8f9fa;
    color: #2c3e50;
    border-left: 4px solid #28a745;
    margin-right: 20%;
}

.assistant-message strong {
    color: #28a745;
    font-weight: bold;
}

.metric-container {
    background-color: #f8f9fa;
    padding: 1rem;
    border-radius: 10px;
    border: 1px solid #e9ecef;
    margin: 0.5rem 0;
}

/* Fix for Streamlit's default text color in dark mode */
.chat-message p {
    color: inherit !important;
    margin: 0 !important;
}

/* Ensure text is visible in both light and dark modes */
.user-message * {
    color: white !important;
}

.assistant-message * {
    color: #2c3e50 !important;
}
</style>
""", unsafe_allow_html=True)

# Initialize session state
def initialize_app():
    """Initialize the application and session state"""
    if 'assistant' not in st.session_state:
        try:
            with st.spinner("🔄 Initializing Legal AI Assistant..."):
                st.session_state.assistant = LegalAIAssistant()
                st.session_state.initialized = True
                st.success("✅ Legal AI Assistant initialized successfully!")
        except Exception as e:
            st.session_state.initialized = False
            st.error(f"❌ Failed to initialize Legal AI Assistant: {e}")
            st.info("💡 Make sure your OpenAI API key is set in the .env file")
            return False

    if 'chat_history' not in st.session_state:
        st.session_state.chat_history = []

    if 'mode' not in st.session_state:
        st.session_state.mode = "Chat Mode"
    
    return st.session_state.get('initialized', False)

def display_chat_message(message, is_user=True):
    """Display a chat message with proper styling"""
    if is_user:
        st.markdown(f"""
        <div class="chat-message user-message">
            <strong>👤 You:</strong><br>
            {message}
        </div>
        """, unsafe_allow_html=True)
    else:
        st.markdown(f"""
        <div class="chat-message assistant-message">
            <strong>🤖 Assistant:</strong><br>
            {message}
        </div>
        """, unsafe_allow_html=True)

def chat_mode():
    """Chat Mode Interface"""
    st.markdown("### 💬 Chat with your Legal Database")
    st.markdown("💡 **Ask quick questions about your legal data in a conversational way!**")
    
    # Examples
    with st.expander("💡 Example Questions"):
        st.markdown("""
        - "How many cases do we have?"
        - "Who's the busiest attorney?"
        - "Any personal injury cases?"
        - "Show me closed cases"
        - "Which clients have multiple matters?"
        """)
    
    # Chat container
    chat_container = st.container()
    
    # Display chat history
    with chat_container:
        if st.session_state.chat_history:
            for msg in st.session_state.chat_history:
                display_chat_message(msg['user'], is_user=True)
                display_chat_message(msg['assistant'], is_user=False)
        else:
            st.info("👋 Start a conversation by asking a question about your legal matters!")
    
    # Chat input
    with st.form("chat_form", clear_on_submit=True):
        col1, col2 = st.columns([6, 1])
        with col1:
            user_input = st.text_input("Ask a question:", placeholder="e.g., How many PI cases do we have?")
        with col2:
            send_button = st.form_submit_button("Send", use_container_width=True)
        
        if send_button and user_input:
            # Add user message to history immediately
            display_chat_message(user_input, is_user=True)
            
            # Generate response
            with st.spinner("🤖 Thinking..."):
                try:
                    response = st.session_state.assistant.process_chat(user_input, st.session_state.chat_history)
                    
                    # Display assistant response
                    display_chat_message(response, is_user=False)
                    
                    # Add to chat history
                    st.session_state.chat_history.append({
                        'user': user_input,
                        'assistant': response
                    })
                    
                    # Rerun to update the display
                    st.rerun()
                    
                except Exception as e:
                    st.error(f"❌ Error: {e}")
        elif send_button:
            st.warning("Please enter a question.")

def predefined_questions_mode():
    """Predefined Questions Interface"""
    st.markdown("### 📋 Quick Demo Questions")
    st.markdown("💡 **Click any question to get instant insights from your legal database**")
    
    demo_queries = [
        "How many personal injury cases do we have in the system?",
        "Which attorney is handling the most matters?",
        "What's the breakdown of case stages in our matters?",
        "Show me all matters that were settled pre-litigation",
        "Which clients have the most matters with us?",
        "How many matters were closed this year?",
        "What are the different record types we handle?",
        "Show me the average case duration for closed matters"
    ]
    
    # Display questions in a clean, visible format
    for i, query in enumerate(demo_queries):
        # Create a container for each question
        with st.container():
            col1, col2 = st.columns([4, 1])
            
            with col1:
                # Display the question prominently
                st.markdown(f"**{i+1}.** {query}")
            
            with col2:
                # Compact "Ask" button
                if st.button("🔍 Ask", key=f"demo_{i}", use_container_width=True):
                    # Show loading and process query
                    with st.spinner("🔄 Processing..."):
                        try:
                            response = st.session_state.assistant.process_query(query)
                            
                            # Display results in an appealing format
                            st.success("✅ Query completed!")
                            
                            # Create an info box with the results
                            st.info(f"**Answer:** {response}")
                            
                            # Add some spacing
                            st.markdown("---")
                            
                        except Exception as e:
                            st.error(f"❌ Error: {e}")
                            st.info("💡 Please check your OpenAI API configuration")
            
            # Add subtle divider between questions
            if i < len(demo_queries) - 1:
                st.markdown("<hr style='margin: 0.5rem 0; border: 0; height: 1px; background: #eee;'>", unsafe_allow_html=True)

def custom_query_mode():
    """Custom Query Interface"""
    st.markdown("### 🔍 Custom Data Query")
    st.markdown("💡 **Ask any question about your legal data in natural language!**")
    
    # Examples
    with st.expander("💡 Example Custom Questions"):
        st.markdown("""
        - "How many cases does Taylor Miller handle?"
        - "Show me all open matters"
        - "Which cases were opened in July 2023?"
        - "List all Workers Compensation cases"
        - "What's the status distribution of our cases?"
        """)
    
    # Query input form
    with st.form("custom_query_form"):
        query = st.text_area(
            "Enter your question:",
            placeholder="e.g., How many cases does Taylor Miller have?",
            height=120,
            help="Ask any question about your legal database in plain English"
        )
        
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            submitted = st.form_submit_button("🔍 Ask Question", use_container_width=True)
        
        if submitted and query:
            st.markdown("---")
            st.markdown(f"**Your Question:** {query}")
            
            with st.spinner("🤖 Analyzing your question and querying the database..."):
                try:
                    response = st.session_state.assistant.process_query(query)
                    st.success("✅ Query completed successfully!")
                    
                    # Display results in a nice format
                    st.markdown("**Answer:**")
                    st.info(response)
                    
                except Exception as e:
                    st.error(f"❌ Error processing query: {e}")
                    st.info("💡 Try rephrasing your question or check if your OpenAI API key is configured correctly.")
                    
        elif submitted:
            st.warning("⚠️ Please enter a question before submitting.")

def sidebar_content():
    """Sidebar content and navigation"""
    st.sidebar.title("⚖️ Legal AI Assistant")
    st.sidebar.markdown("---")
    
    # Mode selection
    st.sidebar.markdown("### 🎯 Select Mode")
    mode = st.sidebar.radio(
        "Choose how you want to interact:",
        ["📋 Predefined Questions", "🔍 Custom Query", "💬 Chat Mode"],
        index=0
    )
    
    # Extract mode name
    st.session_state.mode = mode.split(" ", 1)[1]
    
    st.sidebar.markdown("---")
    
    # Quick stats
    if st.session_state.get('initialized', False):
        st.sidebar.markdown("### 📊 Database Stats")
        try:
            # Get quick statistics
            total_matters = st.session_state.assistant.execute_query("SELECT COUNT(*) as count FROM matters")
            pi_cases = st.session_state.assistant.execute_query("SELECT COUNT(*) as count FROM matters WHERE Record_Type_Name = 'Personal Injury'")
            closed_cases = st.session_state.assistant.execute_query("SELECT COUNT(*) as count FROM matters WHERE Status = 'Closed'")
            
            if total_matters:
                st.sidebar.metric("📁 Total Matters", total_matters[0]['count'])
            if pi_cases:
                st.sidebar.metric("🚗 PI Cases", pi_cases[0]['count'])
            if closed_cases:
                st.sidebar.metric("✅ Closed Cases", closed_cases[0]['count'])
                
        except Exception as e:
            st.sidebar.warning("⚠️ Could not load stats")
    
    st.sidebar.markdown("---")
    
    # Clear chat history button (only show in chat mode)
    if st.session_state.mode == "Chat Mode" and st.session_state.chat_history:
        if st.sidebar.button("🗑️ Clear Chat History"):
            st.session_state.chat_history = []
            st.rerun()
    
    # Info section
    st.sidebar.markdown("### ℹ️ About")
    st.sidebar.info("""
    This AI assistant analyzes your legal matters database using:
    - **2-Agent System**: SQL Generator + Data Analyst
    - **Natural Language Processing**
    - **Real-time Database Queries**
    """)
    
    st.sidebar.markdown("### 🚀 Production Ready")
    st.sidebar.success("Ready to connect to your live Salesforce/Litify instance!")
    
    return mode

def main():
    """Main application function"""
    # Initialize the app
    if not initialize_app():
        st.stop()
    
    # Sidebar
    mode = sidebar_content()
    
    # Main content area
    st.title("⚖️ Legal AI Assistant")
    st.markdown("**Intelligent Legal Database Analysis with Multi-Agent AI**")
    st.markdown("---")
    
    # Route to appropriate mode
    if st.session_state.mode == "Predefined Questions":
        predefined_questions_mode()
    elif st.session_state.mode == "Custom Query":
        custom_query_mode()
    elif st.session_state.mode == "Chat Mode":
        chat_mode()

if __name__ == "__main__":
    main()