# Claude File Context Tool (ClaudeFC)

A desktop application that allows you to easily use the Claude API with local files as context.

![image](https://github.com/user-attachments/assets/047cae5e-184c-4df4-bba1-865a38c015c4)

## Features

- Connect to the Claude API using your API key
- Load text files from a local directory (recursively)
- Automatically filters out binary and large files
- Send questions to Claude about your files
- Streaming responses for better user experience
- Support for different Claude models

## Requirements

- Python 3.6+
- Anthropic Python SDK
- Tkinter (usually comes with Python)

## Installation

1. Clone or download this repository
2. Install the required dependencies:

```
pip install anthropic
```

## Usage

1. Run the application:

```
python claudefc.py
```

2. Enter your Claude API key and connect to the API
3. Select a folder containing the files you want to analyze
4. Click "Load Files" to scan and load the content
5. Type your question about the files
6. Click "Send to Claude" to get an answer

## Configuration Options

- **API Key**: Your Anthropic API key
- **Max Tokens**: Maximum number of tokens in Claude's response (default: 100,000)
- **Model**: Select the Claude model to use:
  - claude-3-7-sonnet-20250219 (default)
  - claude-3-5-sonnet-20240620
  - claude-3-opus-20240229
  - claude-3-5-haiku-20240307

## Notes

- The tool automatically handles:
  - Recursive directory scanning
  - Text file detection and binary file filtering
  - Content truncation for large datasets
  - Formatting file paths for context

- File content is loaded with headers to identify each file in the context
- Total content size is limited to approximately 4MB to avoid token limits
- Large individual files (>1MB) are skipped

## Troubleshooting

- If no files appear, check that your selected folder contains text files
- For large directories, the loading process may take some time
- If Claude's response seems incomplete, try reducing the number of files or focusing on a specific subdirectory
- Make sure your API key is correct and has sufficient permissions

## License

[Insert your preferred license here]

## Author

[Your name/organization]
