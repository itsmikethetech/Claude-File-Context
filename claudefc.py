import os
import sys
import tkinter as tk
from tkinter import filedialog, ttk, scrolledtext
import threading
import mimetypes
import anthropic
import time

class ClaudeAPIApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Claude API File Context Tool")
        self.root.geometry("800x700")
        self.root.configure(padx=10, pady=10)
        
        self.client = None
        self.context_files = []
        self.file_contents = ""
        
        # Set up mime types
        mimetypes.init()
        
        # Create the UI
        self.create_widgets()
        
    def create_widgets(self):
        # API Configuration Frame
        api_frame = ttk.LabelFrame(self.root, text="API Configuration")
        api_frame.pack(fill=tk.X, padx=5, pady=5)
        
        # API Key
        ttk.Label(api_frame, text="API Key:").grid(row=0, column=0, sticky=tk.W, padx=5, pady=5)
        self.api_key_var = tk.StringVar()
        self.api_key_entry = ttk.Entry(api_frame, textvariable=self.api_key_var, width=50, show="*")
        self.api_key_entry.grid(row=0, column=1, sticky=tk.W, padx=5, pady=5)
        
        # Token Limit
        ttk.Label(api_frame, text="Max Tokens:").grid(row=1, column=0, sticky=tk.W, padx=5, pady=5)
        self.token_limit_var = tk.IntVar(value=100000)
        token_limit_entry = ttk.Entry(api_frame, textvariable=self.token_limit_var, width=10)
        token_limit_entry.grid(row=1, column=1, sticky=tk.W, padx=5, pady=5)
        
        # Model Selection
        ttk.Label(api_frame, text="Model:").grid(row=2, column=0, sticky=tk.W, padx=5, pady=5)
        self.model_var = tk.StringVar(value="claude-3-7-sonnet-20250219")
        model_combo = ttk.Combobox(api_frame, textvariable=self.model_var, width=30)
        model_combo['values'] = (
            "claude-3-7-sonnet-20250219",
            "claude-3-5-sonnet-20240620", 
            "claude-3-opus-20240229",
            "claude-3-5-haiku-20240307"
        )
        model_combo.grid(row=2, column=1, sticky=tk.W, padx=5, pady=5)
        
        # Connect Button
        self.connect_btn = ttk.Button(api_frame, text="Connect to API", command=self.connect_to_api)
        self.connect_btn.grid(row=2, column=2, padx=5, pady=5)
        
        # Status display
        self.status_var = tk.StringVar(value="Not connected")
        ttk.Label(api_frame, textvariable=self.status_var).grid(row=3, column=0, columnspan=3, sticky=tk.W, padx=5, pady=5)
        
        # Content Frame
        content_frame = ttk.LabelFrame(self.root, text="Content")
        content_frame.pack(fill=tk.X, padx=5, pady=5)
        
        # Folder Selection
        ttk.Label(content_frame, text="Content Folder:").grid(row=0, column=0, sticky=tk.W, padx=5, pady=5)
        self.content_path_var = tk.StringVar()
        content_path_entry = ttk.Entry(content_frame, textvariable=self.content_path_var, width=50)
        content_path_entry.grid(row=0, column=1, sticky=tk.W, padx=5, pady=5)
        
        folder_btn = ttk.Button(content_frame, text="Browse...", command=self.select_folder)
        folder_btn.grid(row=0, column=2, padx=5, pady=5)
        
        load_btn = ttk.Button(content_frame, text="Load Files", command=self.load_files)
        load_btn.grid(row=1, column=1, sticky=tk.W, padx=5, pady=5)
        
        # Files display
        self.files_display = scrolledtext.ScrolledText(content_frame, height=5, width=70, wrap=tk.WORD)
        self.files_display.grid(row=2, column=0, columnspan=3, padx=5, pady=5, sticky=tk.W+tk.E)
        self.files_display.config(state=tk.DISABLED)
        
        # Question Frame
        question_frame = ttk.LabelFrame(self.root, text="Ask Claude")
        question_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Question Entry
        ttk.Label(question_frame, text="Your Question:").pack(anchor=tk.W, padx=5, pady=5)
        self.question_entry = scrolledtext.ScrolledText(question_frame, height=3, width=70, wrap=tk.WORD)
        self.question_entry.pack(fill=tk.X, padx=5, pady=5)
        
        # Send Button
        self.send_btn = ttk.Button(question_frame, text="Send to Claude", command=self.send_question)
        self.send_btn.pack(anchor=tk.W, padx=5, pady=5)
        
        # Answer Display
        ttk.Label(question_frame, text="Claude's Answer:").pack(anchor=tk.W, padx=5, pady=5)
        self.answer_display = scrolledtext.ScrolledText(question_frame, height=12, width=70, wrap=tk.WORD)
        self.answer_display.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        self.answer_display.config(state=tk.DISABLED)
        
        # Progress bar
        self.progress = ttk.Progressbar(self.root, orient=tk.HORIZONTAL, length=100, mode='indeterminate')
        self.progress.pack(fill=tk.X, padx=5, pady=5)
    
    def connect_to_api(self):
        api_key = self.api_key_var.get()
        
        if not api_key:
            self.status_var.set("Error: API key is required")
            return
        
        try:
            self.client = anthropic.Anthropic(api_key=api_key)
            self.status_var.set("Connected to Claude API")
            self.connect_btn.config(state=tk.DISABLED)
        except Exception as e:
            self.status_var.set(f"Error connecting: {str(e)}")
    
    def select_folder(self):
        folder_path = filedialog.askdirectory()
        if folder_path:
            self.content_path_var.set(folder_path)
    
    def is_text_file(self, file_path):
        """Determine if a file is a text file that can be read."""
        try:
            # Check for common binary file extensions to exclude
            binary_extensions = {
                # Images
                '.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff', '.webp', '.ico', '.svg',
                # Audio
                '.mp3', '.wav', '.ogg', '.flac', '.aac', '.wma', '.m4a',
                # Video
                '.mp4', '.avi', '.mkv', '.mov', '.wmv', '.flv', '.webm',
                # Archives
                '.zip', '.rar', '.7z', '.tar', '.gz', '.bz2',
                # Executables
                '.exe', '.dll', '.so', '.dylib', '.bin',
                # Other binary
                '.pdf', '.doc', '.docx', '.xls', '.xlsx', '.ppt', '.pptx', 
                '.db', '.sqlite', '.mdb', '.class', '.pyc', '.o'
            }
            
            # Get file extension
            _, ext = os.path.splitext(file_path.lower())
            
            # Check if it's a binary file by extension
            if ext in binary_extensions:
                return False
            
            # Known text file extensions
            text_extensions = {
                '.txt', '.md', '.py', '.js', '.html', '.css', '.java', '.c', '.cpp', '.h',
                '.cs', '.php', '.rb', '.go', '.rs', '.ts', '.swift', '.kt', '.scala', '.pl',
                '.sql', '.json', '.xml', '.yaml', '.yml', '.toml', '.ini', '.conf', '.sh',
                '.bat', '.ps1', '.log', '.csv', '.rst', '.r', '.dart', '.lua'
            }
            
            # If it's a known text extension, return True
            if ext in text_extensions:
                return True
            
            # For files we're not sure about, try to read them
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                sample = f.read(1024)  # Read first 1KB
                
                # Simple heuristic: if the sample contains mostly printable ASCII, 
                # it's probably text
                if sample:
                    # Count printable characters
                    printable_count = sum(1 for c in sample if 32 <= ord(c) <= 126 or c in '\n\r\t')
                    ratio = printable_count / len(sample)
                    
                    # If more than 90% characters are printable, consider it text
                    return ratio > 0.9
                
                return True  # Empty file is considered text
                
        except UnicodeDecodeError:
            return False
        except Exception:
            return False
    
    def load_files(self):
        folder_path = self.content_path_var.get()
        if not folder_path:
            self.files_display.config(state=tk.NORMAL)
            self.files_display.delete(1.0, tk.END)
            self.files_display.insert(tk.END, "Error: Please select a folder first")
            self.files_display.config(state=tk.DISABLED)
            return
        
        # Clear previous data
        self.context_files = []
        self.file_contents = ""
        
        self.files_display.config(state=tk.NORMAL)
        self.files_display.delete(1.0, tk.END)
        self.files_display.insert(tk.END, "Loading files...\n")
        self.files_display.config(state=tk.DISABLED)
        
        # Enable the progress bar
        self.progress.start()
        
        # Start background thread to load files
        thread = threading.Thread(target=self._load_files_thread, args=(folder_path,))
        thread.daemon = True
        thread.start()
    
    def _load_files_thread(self, folder_path):
        total_size = 0  # Track total content size
        max_content_size = 4 * 1024 * 1024  # ~4MB limit (rough estimate)
        truncated = False
        
        try:
            # Walk through all files recursively
            for root, _, files in os.walk(folder_path):
                for file in files:
                    file_path = os.path.join(root, file)
                    
                    # Check if we can read this as text
                    if self.is_text_file(file_path):
                        try:
                            # Check file size before reading
                            file_size = os.path.getsize(file_path)
                            
                            # Skip overly large files
                            if file_size > 1024 * 1024:  # Skip files larger than 1MB
                                continue
                                
                            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                                content = f.read()
                                relative_path = os.path.relpath(file_path, folder_path)
                                self.context_files.append(relative_path)
                                
                                # Add file content with header to the combined content
                                file_header = f"\n\n==== FILE: {relative_path} ====\n\n"
                                
                                # Check if adding this file would exceed our limit
                                content_to_add = file_header + content
                                if total_size + len(content_to_add) > max_content_size:
                                    truncated = True
                                    # Only add if we have room for at least the header and some content
                                    if total_size + len(file_header) + 100 < max_content_size:
                                        truncated_content = content[:max_content_size - total_size - len(file_header) - 50]
                                        self.file_contents += file_header + truncated_content + "\n[Content truncated due to size]"
                                        total_size = max_content_size
                                    break
                                
                                self.file_contents += content_to_add
                                total_size += len(content_to_add)
                            
                            # Update display every few files
                            if len(self.context_files) % 10 == 0:
                                self.root.after(0, lambda cnt=len(self.context_files): self._update_files_display_loading(cnt))
                                
                        except Exception as e:
                            print(f"Error reading {file_path}: {str(e)}")
                            
                    # Break the outer loop if we've hit our content size limit
                    if truncated:
                        break
                        
                if truncated:
                    break
            
            # Add a note about truncation if needed
            if truncated:
                self.file_contents += "\n\n==== NOTE: Content was truncated due to size limitations ====\n"
            
            # Final update to display
            self.root.after(0, lambda cnt=len(self.context_files), trunc=truncated: 
                           self._update_files_display_complete(cnt, trunc))
            
        except Exception as e:
            error_msg = f"Error loading files: {str(e)}"
            self.root.after(0, lambda msg=error_msg: self._show_error(msg))
        finally:
            self.root.after(0, self.progress.stop)
    
    def _update_files_display_loading(self, count):
        self.files_display.config(state=tk.NORMAL)
        self.files_display.delete(1.0, tk.END)
        self.files_display.insert(tk.END, f"Loading files... Found {count} so far")
        self.files_display.config(state=tk.DISABLED)
    
    def _update_files_display_complete(self, count, truncated=False):
        self.files_display.config(state=tk.NORMAL)
        self.files_display.delete(1.0, tk.END)
        
        if not self.context_files:
            self.files_display.insert(tk.END, "No readable text files found in the selected folder.")
        else:
            message = f"Loaded {count} files"
            if truncated:
                message += " (content truncated due to size limits)"
            message += ".\n\n"
            
            self.files_display.insert(tk.END, message)
            if count <= 20:
                for file in self.context_files:
                    self.files_display.insert(tk.END, f"- {file}\n")
            else:
                for file in self.context_files[:10]:
                    self.files_display.insert(tk.END, f"- {file}\n")
                self.files_display.insert(tk.END, f"... and {count - 10} more files.\n")
        
        self.files_display.config(state=tk.DISABLED)
    
    def _show_error(self, message):
        self.files_display.config(state=tk.NORMAL)
        self.files_display.delete(1.0, tk.END)
        self.files_display.insert(tk.END, message)
        self.files_display.config(state=tk.DISABLED)
    
    def send_question(self):
        if not self.client:
            self.answer_display.config(state=tk.NORMAL)
            self.answer_display.delete(1.0, tk.END)
            self.answer_display.insert(tk.END, "Error: Not connected to Claude API")
            self.answer_display.config(state=tk.DISABLED)
            return
        
        if not self.file_contents:
            self.answer_display.config(state=tk.NORMAL)
            self.answer_display.delete(1.0, tk.END)
            self.answer_display.insert(tk.END, "Error: No files loaded")
            self.answer_display.config(state=tk.DISABLED)
            return
        
        question = self.question_entry.get(1.0, tk.END).strip()
        if not question:
            self.answer_display.config(state=tk.NORMAL)
            self.answer_display.delete(1.0, tk.END)
            self.answer_display.insert(tk.END, "Error: Please enter a question")
            self.answer_display.config(state=tk.DISABLED)
            return
        
        # Disable UI elements during processing
        self.send_btn.config(state=tk.DISABLED)
        self.question_entry.config(state=tk.DISABLED)
        
        self.answer_display.config(state=tk.NORMAL)
        self.answer_display.delete(1.0, tk.END)
        self.answer_display.insert(tk.END, "Sending request to Claude, please wait...")
        self.answer_display.config(state=tk.DISABLED)
        
        self.progress.start()
        
        # Start background thread to send request
        thread = threading.Thread(target=self._send_question_thread, args=(question,))
        thread.daemon = True
        thread.start()
    
    def _send_question_thread(self, question):
        try:
            # Prepare the system prompt
            system_prompt = (
                "You are an assistant that analyzes and answers questions about the provided files. "
                "The user will provide file contents and ask questions about them. "
                "Be concise but thorough in your responses."
            )
            
            # Create the prompt for Claude with context
            prompt = f"Here are the files to analyze:\n\n{self.file_contents}\n\nBased on these files, please answer the following question:\n{question}"
            
            # Get token limit
            max_tokens = self.token_limit_var.get()
            
            # Update display to show we're processing
            self.root.after(0, lambda: self._update_answer_display("Sending request to Claude, please wait..."))
            
            try:
                # First update to show we're sending the request
                self.root.after(0, lambda: self._update_answer_display("Request sent to Claude API, waiting for response..."))
                
                # Use streaming API for long requests
                with self.client.messages.stream(
                    model=self.model_var.get(),
                    system=system_prompt,
                    max_tokens=max_tokens,
                    messages=[
                        {"role": "user", "content": prompt}
                    ]
                ) as stream:
                    # Initialize the full answer
                    full_answer = ""
                    
                    # Process the incoming stream
                    for text in stream.text_stream:
                        full_answer += text
                        # Update the display with what we have so far
                        self.root.after(0, lambda answer=full_answer: self._update_answer_display(
                            f"{answer}\n\n[Response streaming...]"))
                        # Small sleep to avoid too frequent updates
                        time.sleep(0.1)
                    
                    # Final update with complete answer
                    self.root.after(0, lambda a=full_answer: self._update_answer_display(a))
                
            except TimeoutError:
                self.root.after(0, lambda: self._update_answer_display(
                    "Request timed out. The context might be too large or the Claude API might be experiencing issues. "
                    "Try with fewer files or a smaller subset of content."))
                
        except Exception as error:
            error_message = f"Error: {str(error)}"
            self.root.after(0, lambda msg=error_message: self._update_answer_display(msg))
        finally:
            self.root.after(0, self._reset_ui)
    
    def _update_answer_display(self, text):
        self.answer_display.config(state=tk.NORMAL)
        self.answer_display.delete(1.0, tk.END)
        self.answer_display.insert(tk.END, text)
        self.answer_display.config(state=tk.DISABLED)
    
    def _reset_ui(self):
        self.progress.stop()
        self.send_btn.config(state=tk.NORMAL)
        self.question_entry.config(state=tk.NORMAL)


if __name__ == "__main__":
    root = tk.Tk()
    app = ClaudeAPIApp(root)
    root.mainloop()
