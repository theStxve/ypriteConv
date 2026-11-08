import os
import sys
from modules.ai_helper import AIHelper

class SmartCoder:
    def __init__(self):
        self.ai = AIHelper()
        self.project_root = os.getcwd()
        print(f"🧠 SmartCoder Agent verified. Model: {self.ai.model}")
        print("Capabilities: Project Scan, Auto-Planning, file creation/editing.")
        print("Type your request naturally (e.g. 'Add a reset button to the main window').")
        
    def start(self):
        while True:
            try:
                user_input = input("\n🤖 Agent> ").strip()
                if not user_input:
                    continue
                
                if user_input.lower() in ['exit', 'quit']:
                    print("Goodbye!")
                    break
                
                # Check for explicit commands, otherwise treat as agent task
                if user_input.startswith("custom:"):
                    # Fallback to old manual mode if needed
                    self.handle_legacy_command(user_input)
                else:
                    self.run_agent_task(user_input)

            except KeyboardInterrupt:
                break
            except Exception as e:
                print(f"❌ Error: {e}")

    def get_file_structure(self):
        """Scans the directory to give the AI context of the project."""
        file_list = []
        ignore_dirs = {'.git', '__pycache__', 'venv', 'dist', 'build', '.agent', '.gemini', '.idea', '.vscode'}
        ignore_exts = {'.pyc', '.exe', '.dll', '.so', '.bin', '.png', '.jpg', '.ico'}

        for root, dirs, files in os.walk(self.project_root):
            # Verify ignore lists
            dirs[:] = [d for d in dirs if d not in ignore_dirs]
            
            for file in files:
                ext = os.path.splitext(file)[1]
                if ext not in ignore_exts:
                    rel_path = os.path.relpath(os.path.join(root, file), self.project_root)
                    file_list.append(rel_path)
        return "\n".join(file_list)

    def run_agent_task(self, instruction):
        print("👀 Scanning project structure...")
        files_context = self.get_file_structure()
        
        # Step 1: Planning / File Selection
        print("🤔 Thinking & Planning... (Output streaming enabled)")
        planning_prompt = f"""
        You are an intelligent coding agent. 
        User Request: "{instruction}"
        
        Project Files:
        {files_context}
        
        Which file(s) do you need to modify or create to fulfill this request?
        Return ONLY the filenames, one per line. If a new file is needed, list it.
        Example:
        main.py
        utils/helper.py
        """
        
        # Stream the planning response
        response_stream = self.ai.chat(planning_prompt, system_message="Output ONLY a list of filenames.", stream=True)
        
        full_response = ""
        print("\n💭 AI Thought Process:")
        for chunk in response_stream:
            if chunk.choices[0].delta.content:
                content = chunk.choices[0].delta.content
                print(content, end="", flush=True)
                full_response += content
        print("\n")

        target_files = [f.strip() for f in full_response.split('\n') if f.strip() and not f.startswith('```')]
        
        valid_files = []
        for tf in target_files:
            if "." in tf and len(tf) > 2: 
                valid_files.append(tf)

        if not valid_files:
            print("💡 AI could not identify target files. Response was:", full_response)
            return

        print(f"🎯 Targeted files: {', '.join(valid_files)}")
        
        # Step 2: Execution
        for file_path in valid_files:
            self.process_file(file_path, instruction)

    def process_file(self, file_path, instruction):
        full_path = os.path.join(self.project_root, file_path)
        exists = os.path.exists(full_path)
        
        content = ""
        if exists:
            print(f"📖 Reading {file_path}...")
            try:
                with open(full_path, 'r', encoding='utf-8') as f:
                    content = f.read()
            except UnicodeDecodeError:
                print(f"⚠️ Cannot read binary file {file_path}. Skipping.")
                return
        else:
            print(f"✨ Creating new file {file_path}...")

        # Step 3: Coding
        print(f"✍️  Writing code for {file_path}...")
        
        system_prompt = "You are an expert Python/PyQt developer. Output ONLY the code for the file. No markdown, no explanations."
        user_prompt = f"""
        Request: {instruction}
        Target File: {file_path}
        
        Current Content:
        {content if content else "(New File)"}
        
        Output the full, valid code for this file to implement the request.
        """
        
        # Stream code generation
        response_stream = self.ai.chat(user_prompt, system_message=system_prompt, stream=True)
        
        new_content = ""
        print("\n💻 Generating Code:")
        for chunk in response_stream:
            if chunk.choices[0].delta.content:
                content = chunk.choices[0].delta.content
                print(content, end="", flush=True)
                new_content += content
        print("\n")
        
        # Clean up markdown code blocks
        new_content = self.clean_response(new_content)

        os.makedirs(os.path.dirname(full_path), exist_ok=True)
        
        with open(full_path, 'w', encoding='utf-8') as f:
            f.write(new_content)
        
        print(f"✅ Saved {file_path}")

    def clean_response(self, text):
        lines = text.split('\n')
        # Remove markdown fences like ```python or ```
        if lines and lines[0].strip().startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip().startswith("```"):
            lines = lines[:-1]
        return "\n".join(lines)

if __name__ == "__main__":
    bot = SmartCoder()
    bot.start()
