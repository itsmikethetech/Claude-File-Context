# app.py
from flask import Flask, render_template, request, jsonify, session, Response, stream_with_context
import os
import json
import anthropic
import time
import mimetypes
import tempfile
import shutil
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.secret_key = os.urandom(24)  # For session management
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max upload size
app.config['UPLOAD_FOLDER'] = tempfile.mkdtemp()
app.config['MAX_TEXT_SIZE'] = 4 * 1024 * 1024  # ~4MB limit for text content

# Create templates folder if it doesn't exist
os.makedirs(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'templates'), exist_ok=True)

# Create and write the template file
template_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'templates', 'index.html')
with open(template_path, 'w', encoding='utf-8') as f:
    f.write("""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Claude File Context Tool</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0-alpha1/dist/css/bootstrap.min.css" rel="stylesheet">
    <style>
        .file-list {
            max-height: 200px;
            overflow-y: auto;
            border: 1px solid #dee2e6;
            padding: 10px;
            border-radius: 4px;
            margin-bottom: 15px;
        }
        .response-area {
            min-height: 200px;
            max-height: 400px;
            overflow-y: auto;
            border: 1px solid #dee2e6;
            padding: 15px;
            border-radius: 4px;
            background-color: #f8f9fa;
            white-space: pre-wrap;
        }
        .loading {
            display: flex;
            justify-content: center;
            padding: 20px;
        }
        .hidden {
            display: none;
        }
    </style>
</head>
<body>
    <div class="container mt-4">
        <h1 class="mb-4">Claude File Context Tool</h1>
        
        <!-- API Configuration -->
        <div class="card mb-4">
            <div class="card-header">
                <h5>API Configuration</h5>
            </div>
            <div class="card-body">
                <div class="mb-3">
                    <label for="apiKey" class="form-label">API Key:</label>
                    <div class="input-group">
                        <input type="password" class="form-control" id="apiKey" placeholder="Enter your Claude API key">
                        <button class="btn btn-primary" id="connectBtn">Connect</button>
                    </div>
                </div>
                <div class="mb-3 row">
                    <div class="col-md-6">
                        <label for="modelSelect" class="form-label">Model:</label>
                        <select class="form-select" id="modelSelect">
                            <option value="claude-3-7-sonnet-20250219" selected>claude-3-7-sonnet-20250219</option>
                            <option value="claude-3-5-sonnet-20240620">claude-3-5-sonnet-20240620</option>
                            <option value="claude-3-opus-20240229">claude-3-opus-20240229</option>
                            <option value="claude-3-5-haiku-20240307">claude-3-5-haiku-20240307</option>
                        </select>
                    </div>
                    <div class="col-md-6">
                        <label for="maxTokens" class="form-label">Max Tokens:</label>
                        <input type="number" class="form-control" id="maxTokens" value="100000">
                    </div>
                </div>
                <div id="apiStatus" class="alert alert-secondary">Not connected</div>
            </div>
        </div>
        
        <!-- File Upload -->
        <div class="card mb-4">
            <div class="card-header">
                <h5>Upload Files</h5>
            </div>
            <div class="card-body">
                <div class="mb-3">
                    <label for="fileUpload" class="form-label">Select files to analyze:</label>
                    <input class="form-control" type="file" id="fileUpload" multiple>
                </div>
                <button class="btn btn-primary" id="uploadBtn">Upload Files</button>
                <div id="uploadStatus" class="alert alert-secondary mt-3">No files uploaded</div>
                
                <div id="fileListContainer" class="file-list hidden mt-3">
                    <h6>Uploaded Files:</h6>
                    <ul id="fileList" class="list-group list-group-flush"></ul>
                </div>
            </div>
        </div>
        
        <!-- Ask Claude -->
        <div class="card mb-4">
            <div class="card-header">
                <h5>Ask Claude</h5>
            </div>
            <div class="card-body">
                <div class="mb-3">
                    <label for="question" class="form-label">Your Question:</label>
                    <textarea class="form-control" id="question" rows="3" placeholder="Ask a question about your files..."></textarea>
                </div>
                <button class="btn btn-primary" id="askBtn">Send to Claude</button>
                
                <div class="mt-4">
                    <h6>Claude's Answer:</h6>
                    <div id="loadingResponse" class="loading hidden">
                        <div class="spinner-border text-primary" role="status">
                            <span class="visually-hidden">Loading...</span>
                        </div>
                    </div>
                    <div id="response" class="response-area">
                        Ask a question to see Claude's response here.
                    </div>
                </div>
            </div>
        </div>
    </div>

    <script>
        document.addEventListener('DOMContentLoaded', function() {
            const connectBtn = document.getElementById('connectBtn');
            const uploadBtn = document.getElementById('uploadBtn');
            const askBtn = document.getElementById('askBtn');
            const apiStatus = document.getElementById('apiStatus');
            const uploadStatus = document.getElementById('uploadStatus');
            const fileListContainer = document.getElementById('fileListContainer');
            const fileList = document.getElementById('fileList');
            const response = document.getElementById('response');
            const loadingResponse = document.getElementById('loadingResponse');
            
            // Connect to API
            connectBtn.addEventListener('click', async function() {
                const apiKey = document.getElementById('apiKey').value;
                
                if (!apiKey) {
                    apiStatus.className = 'alert alert-danger';
                    apiStatus.textContent = 'Error: API key is required';
                    return;
                }
                
                apiStatus.className = 'alert alert-info';
                apiStatus.textContent = 'Connecting...';
                
                try {
                    const res = await fetch('/api/connect', {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json'
                        },
                        body: JSON.stringify({ api_key: apiKey })
                    });
                    
                    const data = await res.json();
                    
                    if (data.success) {
                        apiStatus.className = 'alert alert-success';
                        apiStatus.textContent = data.message;
                    } else {
                        apiStatus.className = 'alert alert-danger';
                        apiStatus.textContent = data.message;
                    }
                } catch (err) {
                    apiStatus.className = 'alert alert-danger';
                    apiStatus.textContent = 'Error connecting to server: ' + err.message;
                }
            });
            
            // Upload files
            uploadBtn.addEventListener('click', async function() {
                const fileInput = document.getElementById('fileUpload');
                
                if (fileInput.files.length === 0) {
                    uploadStatus.className = 'alert alert-danger mt-3';
                    uploadStatus.textContent = 'Error: Please select files to upload';
                    return;
                }
                
                uploadStatus.className = 'alert alert-info mt-3';
                uploadStatus.textContent = 'Uploading files...';
                
                // Create form data with files
                const formData = new FormData();
                for (let i = 0; i < fileInput.files.length; i++) {
                    formData.append('files[]', fileInput.files[i]);
                }
                
                try {
                    const res = await fetch('/api/upload', {
                        method: 'POST',
                        body: formData
                    });
                    
                    const data = await res.json();
                    
                    if (data.success) {
                        uploadStatus.className = 'alert alert-success mt-3';
                        uploadStatus.textContent = data.message;
                        
                        // Display file list
                        fileList.innerHTML = '';
                        if (data.files.length > 0) {
                            fileListContainer.classList.remove('hidden');
                            data.files.forEach(file => {
                                const li = document.createElement('li');
                                li.className = 'list-group-item';
                                li.textContent = file;
                                fileList.appendChild(li);
                            });
                        } else {
                            fileListContainer.classList.add('hidden');
                        }
                        
                        if (data.truncated) {
                            const warning = document.createElement('div');
                            warning.className = 'alert alert-warning mt-2';
                            warning.textContent = 'Some content was truncated due to size limits.';
                            fileListContainer.appendChild(warning);
                        }
                    } else {
                        uploadStatus.className = 'alert alert-danger mt-3';
                        uploadStatus.textContent = data.message;
                    }
                } catch (err) {
                    uploadStatus.className = 'alert alert-danger mt-3';
                    uploadStatus.textContent = 'Error uploading files: ' + err.message;
                }
            });
            
            // Ask Claude with streaming response
            askBtn.addEventListener('click', async function() {
                const question = document.getElementById('question').value.trim();
                const model = document.getElementById('modelSelect').value;
                const maxTokens = document.getElementById('maxTokens').value;
                
                if (!question) {
                    response.textContent = 'Error: Please enter a question';
                    return;
                }
                
                // Show loading indicator and clear previous response
                loadingResponse.classList.remove('hidden');
                response.textContent = '';
                
                // Disable the ask button during processing
                askBtn.disabled = true;
                
                try {
                    // Start the streaming request
                    const eventSource = new EventSource(`/api/ask-stream?question=${encodeURIComponent(question)}&model=${encodeURIComponent(model)}&max_tokens=${encodeURIComponent(maxTokens)}`);
                    
                    // Process incoming stream events
                    eventSource.onmessage = function(event) {
                        // Hide loading indicator once we start receiving data
                        loadingResponse.classList.add('hidden');
                        
                        const data = JSON.parse(event.data);
                        
                        if (data.done) {
                            // Stream completed
                            eventSource.close();
                            askBtn.disabled = false;
                        } else if (data.error) {
                            // Handle error
                            response.textContent = data.error;
                            eventSource.close();
                            askBtn.disabled = false;
                        } else {
                            // Append the chunk of text
                            response.textContent += data.chunk;
                            
                            // Auto-scroll to bottom
                            response.scrollTop = response.scrollHeight;
                        }
                    };
                    
                    // Handle errors
                    eventSource.onerror = function(err) {
                        loadingResponse.classList.add('hidden');
                        response.textContent += "\\n\\nError: Connection to server lost. Please try again.";
                        eventSource.close();
                        askBtn.disabled = false;
                    };
                    
                } catch (err) {
                    loadingResponse.classList.add('hidden');
                    response.textContent = 'Error: ' + err.message;
                    askBtn.disabled = false;
                }
            });
        });
    </script>
</body>
</html>""")

# Set up mime types
mimetypes.init()

def is_text_file(file_path):
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

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/connect', methods=['POST'])
def connect_api():
    api_key = request.json.get('api_key')
    
    if not api_key:
        return jsonify({"success": False, "message": "API key is required"})
    
    try:
        # Test connection by creating a client
        client = anthropic.Anthropic(api_key=api_key)
        
        # Store API key in session
        session['api_key'] = api_key
        
        return jsonify({"success": True, "message": "Connected to Claude API"})
    except Exception as e:
        return jsonify({"success": False, "message": f"Error connecting: {str(e)}"})

@app.route('/api/upload', methods=['POST'])
def upload_files():
    if 'files[]' not in request.files:
        return jsonify({"success": False, "message": "No files provided"})
    
    # Get uploaded files
    files = request.files.getlist('files[]')
    
    # Clear previous uploads if any
    if 'upload_dir' in session:
        try:
            shutil.rmtree(session['upload_dir'])
        except:
            pass
    
    # Create a new temporary directory for this session
    upload_dir = os.path.join(app.config['UPLOAD_FOLDER'], str(time.time()))
    os.makedirs(upload_dir, exist_ok=True)
    session['upload_dir'] = upload_dir
    
    # Process files
    processed_files = []
    total_size = 0
    max_content_size = app.config['MAX_TEXT_SIZE']
    truncated = False
    file_contents = ""
    
    for file in files:
        if file.filename == '':
            continue
        
        # Save file to temporary directory with secure filename
        filename = secure_filename(file.filename)
        file_path = os.path.join(upload_dir, filename)
        file.save(file_path)
        
        # Check if it's a text file and not too large
        if is_text_file(file_path) and os.path.getsize(file_path) <= 1024 * 1024:  # 1MB max per file
            try:
                with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()
                    processed_files.append(filename)
                    
                    # Add file content with header to the combined content
                    file_header = f"\n\n==== FILE: {filename} ====\n\n"
                    
                    # Check if adding this file would exceed our limit
                    content_to_add = file_header + content
                    if total_size + len(content_to_add) > max_content_size:
                        truncated = True
                        # Only add if we have room for at least the header and some content
                        if total_size + len(file_header) + 100 < max_content_size:
                            truncated_content = content[:max_content_size - total_size - len(file_header) - 50]
                            file_contents += file_header + truncated_content + "\n[Content truncated due to size]"
                            total_size = max_content_size
                    else:
                        file_contents += content_to_add
                        total_size += len(content_to_add)
            except Exception as e:
                print(f"Error reading {file_path}: {str(e)}")
    
    # Add a note about truncation if needed
    if truncated:
        file_contents += "\n\n==== NOTE: Content was truncated due to size limitations ====\n"
    
    # Store the file contents in the session
    session['file_contents'] = file_contents
    
    return jsonify({
        "success": True, 
        "message": f"Loaded {len(processed_files)} files",
        "files": processed_files,
        "truncated": truncated
    })

# Streaming endpoint using Server-Sent Events (SSE)
@app.route('/api/ask-stream')
def ask_claude_stream():
    if 'api_key' not in session:
        return jsonify({"error": "Not connected to Claude API"})
    
    if 'file_contents' not in session or not session['file_contents']:
        return jsonify({"error": "No files loaded"})
    
    question = request.args.get('question', '').strip()
    model = request.args.get('model', 'claude-3-7-sonnet-20250219')
    max_tokens = int(request.args.get('max_tokens', 100000))
    
    if not question:
        return jsonify({"error": "Please enter a question"})
    
    def generate():
        try:
            # Create a client with the stored API key
            client = anthropic.Anthropic(api_key=session['api_key'])
            
            # Prepare the system prompt
            system_prompt = (
                "You are an assistant that analyzes and answers questions about the provided files. "
                "The user will provide file contents and ask questions about them. "
                "Be concise but thorough in your responses."
            )
            
            # Create the prompt for Claude with context
            prompt = f"Here are the files to analyze:\n\n{session['file_contents']}\n\nBased on these files, please answer the following question:\n{question}"
            
            # Use streaming API for long requests
            with client.messages.stream(
                model=model,
                system=system_prompt,
                max_tokens=max_tokens,
                messages=[
                    {"role": "user", "content": prompt}
                ]
            ) as stream:
                # Process the text stream
                for text in stream.text_stream:
                    # Yield each chunk as a Server-Sent Event (SSE)
                    yield f"data: {json.dumps({'chunk': text})}\n\n"
                    
                # Signal completion
                yield f"data: {json.dumps({'done': True})}\n\n"
                
        except Exception as e:
            # Send error information
            yield f"data: {json.dumps({'error': f'Error: {str(e)}'})}\n\n"
    
    # Return a streaming response
    return Response(stream_with_context(generate()), mimetype='text/event-stream')

if __name__ == '__main__':
    try:
        # Clean up temp files when the server starts
        if os.path.exists(app.config['UPLOAD_FOLDER']):
            shutil.rmtree(app.config['UPLOAD_FOLDER'])
        os.makedirs(app.config['UPLOAD_FOLDER'])
        
        app.run(debug=True)
    finally:
        # Clean up temp files when the server shuts down
        if os.path.exists(app.config['UPLOAD_FOLDER']):
            shutil.rmtree(app.config['UPLOAD_FOLDER'])