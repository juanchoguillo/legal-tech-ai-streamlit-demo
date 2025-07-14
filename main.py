import os
import sqlite3
import pandas as pd
from crewai import Agent, Task, Crew, Process
from typing import Dict, Any
import csv
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

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
            
            print(f"✅ Database created successfully from {self.csv_file}")
            print(f"📊 Loaded {len(df)} records")
            
        except Exception as e:
            print(f"❌ Error setting up database: {e}")
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
        
        print(f"✅ Sample CSV created: {self.csv_file}")
    
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
            print(f"❌ Error executing query: {e}")
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
            
            Common query patterns:
            - For counting: SELECT COUNT(*) FROM matters WHERE...
            - For listing: SELECT column_name FROM matters WHERE...
            - For grouping: SELECT column_name, COUNT(*) FROM matters GROUP BY column_name
            - For top/most: ORDER BY COUNT(*) DESC LIMIT N
            - For dates: Use LIKE '23' for 2023, LIKE '%/23' for year 2023
            
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
            - Don't provide lengthy explanations unless specifically requested
            
            You understand legal terminology:
            - Personal Injury (PI) cases
            - Workers Compensation (WC) cases  
            - Pre-Lit Settlement means settled before litigation
            - Case stages show progression through legal process
            
            Example response format:
            "We have X personal injury cases. Taylor Miller handles the most with Y cases. This shows good case distribution across the team."
            
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
            
            You have access to a legal matters database with information about:
            - Personal Injury cases, Workers Compensation cases, and other legal matters
            - Attorneys and their caseloads
            - Case stages (Active, Closed, Pre-Lit Settlement)
            - Client information and matter details
            - Case dates and durations
            
            Your response style:
            - ALWAYS keep answers SHORT and DIRECT (1-3 sentences max)
            - Answer the specific question asked
            - Use conversational tone but stay focused
            - Provide exact numbers and facts from the database
            - Don't provide lengthy explanations unless specifically asked
            
            You can answer questions like:
            - "How many PI cases do we have?" → "We have X personal injury cases."
            - "Who's our busiest attorney?" → "Taylor Miller handles X cases."
            - "Any cases settled pre-lit?" → "Yes, X cases were settled pre-litigation."
            
            Stay concise and factual.""",
            verbose=False,
            allow_delegation=False
        )
        
        return chat_agent
    
    def process_query(self, user_query: str) -> str:
        """Process user query through the 2-agent system"""
        
        print(f"🔍 Processing: {user_query}")
        
        # Create agents
        agents = self.create_agents()
        
        # Step 1: Generate SQL Query
        print("🤖 Agent 1: Converting natural language to SQL...")
        
        sql_task = Task(
            description=f"""
            Convert this natural language question to a SQL query for the legal matters database:
            
            Question: "{user_query}"
            
            Database Information:
            - Table name: matters
            - Available columns: Id, Display_Name, Client_Name, Client_Full_Name, Record_Type_Name, Case_Type, Status, Case_Stage, Open_Date, Closed_Date, Attorney_Name, Assistant_Name
            
            Common values in the database:
            - Record_Type_Name: 'Personal Injury', 'Billable Matter', 'Workers Compensation'
            - Case_Type: 'PI AUTO-IN-HOUSE', 'WC WC-IN-HOUSE', 'PI AUTO-IN-HOUSE MINOR'
            - Status: 'Closed', 'Active', 'Open'
            - Case_Stage: 'Active', 'Closed', 'Pre-Lit Settlement'
            - Dates are in MM/DD/YY format (like '7/21/23')
            
            Query Guidelines:
            - Use COUNT(*) for counting questions
            - Use GROUP BY for breakdown/distribution questions
            - Use ORDER BY ... DESC LIMIT N for "top" or "most" questions
            - Use LIKE '%23' for year 2023 queries
            - Use WHERE column_name != '' to exclude empty values
            - For personal injury: WHERE Record_Type_Name = 'Personal Injury'
            - For attorneys: WHERE Attorney_Name != ''
            - For clients: WHERE Client_Full_Name != ''
            
            Examples:
            - "How many personal injury cases?" → SELECT COUNT(*) FROM matters WHERE Record_Type_Name = 'Personal Injury'
            - "Top attorneys by cases?" → SELECT Attorney_Name, COUNT(*) FROM matters WHERE Attorney_Name != '' GROUP BY Attorney_Name ORDER BY COUNT(*) DESC LIMIT 5
            - "Case breakdown by stage?" → SELECT Case_Stage, COUNT(*) FROM matters WHERE Case_Stage != '' GROUP BY Case_Stage
            
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
        
        # Clean up the SQL query (remove any extra formatting)
        sql_query = str(sql_result).strip()
        
        # Remove common formatting issues
        sql_query = sql_query.replace('```sql', '').replace('```', '').strip()
        if sql_query.startswith('SQL:'):
            sql_query = sql_query[4:].strip()
        if sql_query.startswith('Query:'):
            sql_query = sql_query[6:].strip()
        
        print(f"📝 Generated SQL: {sql_query}")
        
        # Step 2: Execute the query
        print("🔄 Executing query against database...")
        query_results = self.execute_query(sql_query)
        
        if not query_results:
            print("⚠️ No results found, trying alternative query...")
            # Try a fallback query if the first one fails
            fallback_query = "SELECT COUNT(*) as total FROM matters"
            query_results = self.execute_query(fallback_query)
            sql_query = fallback_query
        
        print(f"📊 Retrieved {len(query_results)} result(s)")
        
        # Step 3: Analyze results
        print("🤖 Agent 2: Analyzing results and generating insights...")
        
        analysis_task = Task(
            description=f"""
            Analyze these legal database results and provide a SHORT, DIRECT answer:
            
            Original Question: "{user_query}"
            SQL Query Used: {sql_query}
            Database Results: {query_results}
            
            Context: This is a legal practice management system with data about:
            - Personal Injury cases (PI)
            - Workers Compensation cases (WC)
            - Case stages (Active, Closed, Pre-Lit Settlement)
            - Attorney assignments and workload
            - Client relationships
            
            IMPORTANT RESPONSE GUIDELINES:
            1. Keep response SHORT (2-4 sentences maximum)
            2. Start with a DIRECT answer to the user's question
            3. Provide 1-2 key insights briefly
            4. Be professional but conversational
            5. Use exact numbers from the database results
            6. Don't provide lengthy analysis or multiple bullet points
            
            Example good responses:
            - "We have 8 personal injury cases in the system. Most are already closed, showing good case resolution."
            - "Taylor Miller handles the most cases with 3 matters. The workload is well distributed across attorneys."
            - "3 cases were settled pre-litigation. This represents efficient early resolution."
            
            Stay concise and direct!
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
        
        # Return concise response without production note for brevity
        return str(final_response)
    
    def process_chat(self, user_message: str, conversation_history: list = None) -> str:
        """Process chat message with database access for short, direct answers"""
        
        if conversation_history is None:
            conversation_history = []
        
        # First, try to identify if this is a data question and get database results
        database_context = ""
        try:
            # Create agents for potential database query
            agents = self.create_agents()
            
            # Generate SQL query (but don't print verbose output)
            sql_task = Task(
                description=f"""
                Determine if this is a question about the legal database and generate a SQL query if needed:
                
                User Message: "{user_message}"
                
                Database Information:
                - Table: matters
                - Columns: Id, Display_Name, Client_Name, Client_Full_Name, Record_Type_Name, Case_Type, Status, Case_Stage, Open_Date, Closed_Date, Attorney_Name, Assistant_Name
                
                If this is a database question, return ONLY a SQL query.
                If this is NOT a database question (like greetings, general advice, etc.), return: NO_QUERY_NEEDED
                
                Examples:
                - "How many cases?" → SELECT COUNT(*) FROM matters
                - "Who handles most cases?" → SELECT Attorney_Name, COUNT(*) FROM matters WHERE Attorney_Name != '' GROUP BY Attorney_Name ORDER BY COUNT(*) DESC LIMIT 1
                - "Hello" → NO_QUERY_NEEDED
                - "What's a good practice tip?" → NO_QUERY_NEEDED
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
            
            if sql_query != "NO_QUERY_NEEDED" and not sql_query.startswith("NO_QUERY"):
                # Execute the database query
                query_results = self.execute_query(sql_query)
                if query_results:
                    database_context = f"\nDatabase Results: {query_results}\nSQL Used: {sql_query}"
        
        except Exception as e:
            # If there's an error with database query, continue with chat-only mode
            pass
        
        # Create chat agent
        chat_agent = self.create_chat_agent()
        
        # Build conversation context
        context = ""
        if conversation_history:
            context = "Recent conversation:\n"
            for msg in conversation_history[-3:]:  # Last 3 messages for context
                context += f"User: {msg['user']}\nAssistant: {msg['assistant']}\n\n"
        
        chat_task = Task(
            description=f"""
            Respond to this user message in a SHORT, DIRECT, conversational way:
            
            {context}
            Current User Message: "{user_message}"
            {database_context}
            
            Context about the legal firm:
            - Law firm with Personal Injury, Workers Compensation, and other legal matters
            - Has attorneys, legal assistants, and tracks cases through various stages
            
            IMPORTANT RESPONSE GUIDELINES:
            1. Keep answers SHORT (1-3 sentences maximum)
            2. Be DIRECT and answer exactly what was asked
            3. Use conversational tone but stay focused
            4. If database results are provided, use them to give exact answers
            5. Don't provide long explanations unless specifically requested
            6. For greetings or general questions, respond briefly and ask how you can help with their legal data
            
            Examples of good responses:
            - "We have 9 personal injury cases in the system."
            - "Taylor Miller handles the most cases with 3 matters."
            - "Yes, 3 cases were settled pre-litigation."
            - "Hi! I can help you with questions about your legal matters. What would you like to know?"
            
            Stay concise and helpful!
            """,
            expected_output="A short, direct response (1-3 sentences max)",
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
        return str(response)

def show_main_menu():
    """Display the main menu options"""
    print("\n" + "="*60)
    print("🏛️  LEGAL AI ASSISTANT - MAIN MENU")
    print("="*60)
    print("1. 📋 Predefined Questions - Quick insights from demo queries")
    print("2. 🔍 Custom Query - Ask your own data questions")
    print("3. 💬 Chat Mode - Conversational legal practice advice")
    print("4. 🚪 Exit")
    print("="*60)

def run_predefined_queries(assistant):
    """Run the predefined queries mode"""
    print("\n🎯 PREDEFINED QUESTIONS MODE")
    print("="*40)
    
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
    
    while True:
        print("\n📊 Available Demo Queries:")
        for i, query in enumerate(demo_queries, 1):
            print(f"{i}. {query}")
        
        choice = input("\nEnter query number (1-8) or 'back' to return to main menu: ").strip()
        
        if choice.lower() == 'back':
            break
        elif choice.isdigit() and 1 <= int(choice) <= len(demo_queries):
            query = demo_queries[int(choice) - 1]
            
            print("\n" + "-"*60)
            print(f"🔍 Processing: {query}")
            print("-"*60)
            
            try:
                response = assistant.process_query(query)
                print(f"\n🤖 {response}")
                
            except Exception as e:
                print(f"❌ Error processing query: {e}")
                print("💡 Make sure your OpenAI API key is properly configured")
        else:
            print("❌ Invalid choice. Please enter a number 1-8 or 'back'.")

def run_custom_queries(assistant):
    """Run the custom queries mode"""
    print("\n🔍 CUSTOM QUERY MODE")
    print("="*40)
    print("💡 Ask any question about your legal data in natural language!")
    print("💡 Examples: 'How many cases does Taylor Miller have?', 'Show me all open cases'")
    
    while True:
        query = input("\n🔍 Enter your question (or 'back' to return to main menu): ").strip()
        
        if query.lower() == 'back':
            break
        elif not query:
            print("❌ Please enter a question.")
            continue
        
        print("\n" + "-"*60)
        print(f"🔍 Processing: {query}")
        print("-"*60)
        
        try:
            response = assistant.process_query(query)
            print(f"\n🤖 {response}")
            
        except Exception as e:
            print(f"❌ Error processing query: {e}")
            print("💡 Make sure your OpenAI API key is properly configured")

def run_chat_mode(assistant):
    """Run the conversational chat mode with database access"""
    print("\n💬 CHAT MODE")
    print("="*40)
    print("💡 Ask quick questions about your legal data in a conversational way!")
    print("💡 Examples: 'How many cases?', 'Who's the busiest attorney?', 'Any closed cases?'")
    print("💡 Type 'back' to return to main menu.")
    
    conversation_history = []
    
    while True:
        user_message = input("\n💬 You: ").strip()
        
        if user_message.lower() == 'back':
            break
        elif not user_message:
            print("❌ Please enter a message.")
            continue
        
        try:
            print("🤖 Assistant: ", end="")
            response = assistant.process_chat(user_message, conversation_history)
            print(response)
            
            # Add to conversation history
            conversation_history.append({
                'user': user_message,
                'assistant': response
            })
            
        except Exception as e:
            print(f"❌ Error in chat: {e}")
            print("💡 Make sure your OpenAI API key is properly configured")

def run_demo():
    """Main application with menu system"""
    print("🏛️ Legal AI Assistant - Multi-Mode System")
    print("🤖 2-Agent System: SQL Generator + Data Analyst + Chat Agent")
    print("="*60)
    
    # Initialize assistant
    try:
        assistant = LegalAIAssistant(csv_file="litify_matters.csv")
        print("✅ AI Assistant initialized with agent system")
    except Exception as e:
        print(f"❌ Error initializing assistant: {e}")
        return
    
    # Main application loop
    while True:
        show_main_menu()
        choice = input("\nSelect an option (1-4): ").strip()
        
        if choice == '1':
            run_predefined_queries(assistant)
        elif choice == '2':
            run_custom_queries(assistant)
        elif choice == '3':
            run_chat_mode(assistant)
        elif choice == '4':
            print("\n✅ Thank you for using Legal AI Assistant!")
            print("🚀 Remember: In production, this connects to your live Salesforce/Litify data!")
            break
        else:
            print("❌ Invalid choice. Please select 1, 2, 3, or 4.")

if __name__ == "__main__":
    run_demo()